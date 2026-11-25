"""QAQS execution-cost model: predict billed QPU time (resource units) before running.

IBM bills QPU time in resource units (RUs); 1 RU = 1 minute of QPU time for standard
workloads. Each job's usage report gives the RUs, the billed time rounded up to whole
seconds, and the time spent executing the circuit. This module predicts billed
seconds (``g.cost_rus * 60``) from pre-runtime information only: the compiled circuit,
its scheduled duration, the runtime options, and the number of shots.

One structure for every chip, with one chip-specific constant. The usage reports follow an
accounting identity: billed time minus IBM's circuit-execution time takes one value per
runtime configuration, and circuit time is shots x (a per-shot constant + scheduled
duration). That per-shot constant differs between chips by several microseconds, which is
several milliseconds per 1,024-shot job and enough to move a job across a whole-second
billing boundary. The chip is known before submission, so it is an input of the physical
model. A chip with no training jobs gets the job-weighted average of the training chips'
constants and is flagged: its offset is unknown until that chip has usage reports.

Why the model has a physical part. Every job in this dataset ran the same number of shots
of one circuit, and billed time is dominated by a fixed per-job overhead. An ML model
trained at one shot count cannot learn how cost scales with shots. So the model is

    billed_seconds = overhead + shots x (per_shot[chip] + slope x duration) + residual(circuit)

The physical terms are fitted on the training data; a tree model learns the residual
from circuit features (twirling, dynamic circuits, depth). The residual is learned at the
training shot counts and has no shot input, so it is applied only at those shot counts.
Predictions at other shot counts use the physical terms alone; that extrapolation is
reported as an assumption, not a validated result.

Usage reports in resource units exist only for some providers. Jobs without one are
counted per provider and reported as WAITING FOR DATA; they never raise.

Evaluations (same names as the quality models):

* unseen-circuit validation -- repeated grouped K-fold by circuit configuration on the
  training campaigns;
* new-run validation -- the validation-v1 jobs on Fez, Kingston and Marrakesh. Cost was
  not pre-registered for those runs, so this is an out-of-sample test, not a
  pre-registration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

from experiments.ml_dataset import is_validation_campaign, load_ml_dataset

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLES = ROOT / "experiments" / "dataset_out"
DEFAULT_REPORT = ROOT / "report" / "ml_estimation" / "cost"
DEFAULT_DASHBOARD = ROOT / "dashboard" / "experiments" / "cost" / "cost-v1.json"
SCHEMA_VERSION = 1
SECONDS_PER_RU = 60.0
# IBM's published rough estimate: ~2 s per sub-job + 0.00035 s per circuit execution.
IBM_OVERHEAD_S = 2.0
IBM_PER_EXECUTION_S = 0.00035

TARGET = "billed_seconds"
CIRCUIT_FEATURES = (
    "b.depth",
    "b.two_qubit_gates",
    "b.two_qubit_depth",
    "b.size",
    "b.QiskitMetrics.basic_metrics.num_qubits",
    "b.count_ops.measure",
)
FLAG_FEATURES = ("twirling", "dynamic", "dynamical_decoupling")
CHIP = "backend"  # known before submission; read by the physical model, not by the trees
PRIMARY = "QAQS cost (physical + residual)"
WAITING = "WAITING FOR DATA"
# A job this close to a whole-second billing boundary can flip with a few ms of error.
NEAR_BOUNDARY_SECONDS = 0.02


def _flag(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "1.0"}).astype(float)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    """A numeric column, or all-missing when the export does not have it."""
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _text(frame: pd.DataFrame, column: str, default: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=object)
    return frame[column].astype(str)


def cost_coverage(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    """Per provider: how many jobs carry a resource-unit usage report."""
    provider = _text(frame, "meta.provider", "unknown")
    has_ru = _numeric(frame, "g.cost_rus").notna()
    rows = []
    for name in sorted(provider.unique()):
        mask = provider == name
        with_ru = int(has_ru[mask].sum())
        rows.append(
            {
                "provider": name,
                "jobs": int(mask.sum()),
                "withRu": with_ru,
                "chips": sorted(_text(frame, "meta.backend_name", "unknown")[mask].unique().tolist()),
                "status": "modelled" if with_ru else WAITING,
            }
        )
    return rows


def cost_frame(tables: Path = DEFAULT_TABLES, frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """Jobs with a resource-unit usage report, with cost targets and pre-runtime inputs.

    Empty, never an error, when no job has a usage report.
    """
    if frame is None:
        frame = load_ml_dataset(tables, include_validation=True).frame
    ru = _numeric(frame, "g.cost_rus")
    frame = frame[ru.notna()].copy()
    out = pd.DataFrame(index=frame.index)
    out["job_id"] = frame["meta.job_id"]
    out["config_id"] = frame["meta.config_id"].astype(str)
    out["algorithm"] = frame["meta.algorithm"].astype(str)
    out["backend"] = frame["meta.backend_name"].astype(str)
    out["provider"] = _text(frame, "meta.provider", "unknown")
    out["campaign"] = frame["meta.campaign_id"].astype(str)
    out["validation"] = frame["meta.campaign_id"].map(is_validation_campaign)
    out["cost_rus"] = _numeric(frame, "g.cost_rus")
    out[TARGET] = out["cost_rus"] * SECONDS_PER_RU
    out["billed_whole_seconds"] = _numeric(frame, "g.billed_seconds")
    out["circuit_seconds"] = _numeric(frame, "g.circuit_execution_seconds")
    out["shots"] = _numeric(frame, "meta.shots")
    # Scheduled duration of one shot; dynamic circuits are not scheduled (NaN -> imputed).
    out["duration_s"] = _numeric(frame, "c.duration_s")
    for name, column in (
        ("twirling", "g.twirling_gates"),
        ("dynamic", "g.dynamic_circuit"),
        ("dynamical_decoupling", "g.dynamical_decoupling"),
    ):
        out[name] = _flag(_text(frame, column, "false"))
    for col in CIRCUIT_FEATURES:
        out[col] = _numeric(frame, col)
    return out.reset_index(drop=True)


FEATURES: tuple[str, ...] = ("shots", "duration_s") + FLAG_FEATURES + CIRCUIT_FEATURES


class PhysicalCostModel(BaseEstimator, RegressorMixin):
    """billed = overhead + shots * per_shot(duration, twirling), following IBM's usage formula.

    Every job in the data ran the same number of shots, so overhead and per-shot cost are
    not separable from billed time alone (they are collinear). They are separated with
    IBM's measured circuit-execution time, which is training-label information only and
    is never an input at prediction time:

    1. per-shot time = circuit_seconds / shots, regressed on scheduled duration and
       twirling (``a[chip] + b*duration + c*duration*twirling + d*twirling``), with one
       constant per chip when the ``backend`` column is present;
    2. overhead = billed - shots * per-shot, averaged (separately for twirled jobs).

    ``shot_coef_[0]`` is the job-weighted average of the chip constants. It is the fallback
    for a chip without training jobs, whose true constant is unknown; ``unseen_chip`` flags
    those rows. Missing durations (dynamic circuits are not scheduled) use the training median.
    """

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        y = np.asarray(y, dtype=float)
        self.duration_fill_ = float(np.nanmedian(X["duration_s"])) if X["duration_s"].notna().any() else 0.0
        shots = X["shots"].to_numpy(dtype=float)
        per_shot = X["circuit_seconds"].to_numpy(dtype=float) / shots
        slopes = self._shot_design(X)[:, 1:]
        chips = X[CHIP].astype(str).to_numpy() if CHIP in X else np.full(len(X), "")
        names = sorted(set(chips))
        dummies = np.column_stack([(chips == name).astype(float) for name in names])
        coef, *_ = np.linalg.lstsq(np.c_[dummies, slopes], per_shot, rcond=None)
        constants = coef[: len(names)]
        fallback = float(dummies.mean(axis=0) @ constants)
        self.shot_coef_ = np.r_[fallback, coef[len(names) :]]
        self.chip_per_shot_ = dict(zip(names, map(float, constants))) if CHIP in X else {}
        rest = y - self.predict_circuit_seconds(X)
        tw = X["twirling"].to_numpy(dtype=float)
        self.overhead_ = float(rest[tw == 0].mean()) if (tw == 0).any() else float(rest.mean())
        self.overhead_twirling_ = float(rest[tw == 1].mean() - self.overhead_) if (tw == 1).any() else 0.0
        return self

    def _shot_design(self, X: pd.DataFrame) -> np.ndarray:
        dur = X["duration_s"].fillna(self.duration_fill_).to_numpy(dtype=float)
        tw = X["twirling"].to_numpy(dtype=float)
        return np.c_[np.ones(len(X)), dur, dur * tw, tw]

    def _chip_offset(self, X: pd.DataFrame) -> np.ndarray:
        """Chip constant minus the fallback; zero for an unseen chip or a model without chips."""
        constants = getattr(self, "chip_per_shot_", {})
        if not constants or CHIP not in X:
            return np.zeros(len(X))
        return (
            X[CHIP].astype(str).map(constants).fillna(self.shot_coef_[0]).to_numpy(dtype=float)
            - self.shot_coef_[0]
        )

    def unseen_chip(self, X: pd.DataFrame) -> np.ndarray:
        """Rows predicted with the fallback constant because their chip had no training jobs."""
        constants = getattr(self, "chip_per_shot_", {})
        if not constants:
            return np.zeros(len(X), dtype=bool)
        if CHIP not in X:
            return np.ones(len(X), dtype=bool)
        return ~X[CHIP].astype(str).isin(constants).to_numpy()

    def predict_circuit_seconds(self, X: pd.DataFrame) -> np.ndarray:
        per_shot = self._shot_design(X) @ self.shot_coef_ + self._chip_offset(X)
        return X["shots"].to_numpy(dtype=float) * per_shot

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        tw = X["twirling"].to_numpy(dtype=float)
        return self.overhead_ + self.overhead_twirling_ * tw + self.predict_circuit_seconds(X)

    def terms(self) -> Dict[str, Any]:
        a, b, c, d = self.shot_coef_
        chips = getattr(self, "chip_per_shot_", {})
        spread = max(chips.values()) - min(chips.values()) if chips else 0.0
        return {
            # Additive: perShotSeconds stays the single constant older readers expect. It is
            # the fallback for a chip that is not listed in perShotSecondsByChip.
            "perShotSecondsByChip": dict(chips),
            "perShotSecondsFallback": float(a),
            "perShotChipSpreadSeconds": float(spread),
            "overheadSeconds": self.overhead_,
            "twirlingOverheadSeconds": self.overhead_twirling_,
            "perShotSeconds": float(a),
            "durationSlope": float(b),
            "twirlingDurationSlope": float(c),
            "twirlingPerShotSeconds": float(d),
        }


class HybridCostModel(BaseEstimator, RegressorMixin):
    """Physical model + gradient-boosted residual on circuit features."""

    def __init__(self, random_state: int = 11):
        self.random_state = random_state

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        y = np.asarray(y, dtype=float)
        self.physical_ = PhysicalCostModel().fit(X, y)
        self.shots_seen_ = np.unique(X["shots"].to_numpy(dtype=float))
        resid = y - self.physical_.predict(X)
        self.imputer_ = SimpleImputer(strategy="median", keep_empty_features=True)
        Z = self.imputer_.fit_transform(X[list(FEATURES)])
        self.residual_ = GradientBoostingRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=self.random_state
        ).fit(Z, resid)
        return self

    def residual_applied(self, X: pd.DataFrame) -> np.ndarray:
        """The residual has no shot input, so it is used only at shot counts it was fitted on."""
        seen = getattr(self, "shots_seen_", None)
        if seen is None:  # models frozen before this rule
            return np.ones(len(X), dtype=bool)
        return np.isin(X["shots"].to_numpy(dtype=float), seen)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        residual = self.residual_.predict(self.imputer_.transform(X[list(FEATURES)]))
        return self.physical_.predict(X) + np.where(self.residual_applied(X), residual, 0.0)


class IBMRuleOfThumb(BaseEstimator, RegressorMixin):
    """IBM's published estimate: ~2 s per job + 0.00035 s per circuit execution (no fitting)."""

    def fit(self, X, y):
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return IBM_OVERHEAD_S + IBM_PER_EXECUTION_S * X["shots"].to_numpy(dtype=float)


class TreeOnly(BaseEstimator, RegressorMixin):
    """Pure ML baseline: gradient boosting on the same inputs, no physical structure."""

    def __init__(self, random_state: int = 11):
        self.random_state = random_state

    def fit(self, X, y):
        self.imputer_ = SimpleImputer(strategy="median", keep_empty_features=True)
        self.model_ = GradientBoostingRegressor(
            n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=self.random_state
        ).fit(self.imputer_.fit_transform(X[list(FEATURES)]), np.asarray(y, dtype=float))
        return self

    def predict(self, X):
        return self.model_.predict(self.imputer_.transform(X[list(FEATURES)]))


def build_models(random_state: int = 11) -> Dict[str, BaseEstimator]:
    return {
        "QAQS cost (physical + residual)": HybridCostModel(random_state),
        "Physical model only": PhysicalCostModel(),
        "Gradient boosting only": TreeOnly(random_state),
        "IBM rule of thumb": IBMRuleOfThumb(),
    }


# ------------------------------------------------------------------- evaluation


def near_boundary(y: np.ndarray) -> np.ndarray:
    """Jobs whose billed time lies within NEAR_BOUNDARY_SECONDS of a whole second."""
    y = np.asarray(y, dtype=float)
    return np.abs(y - np.rint(y)) < NEAR_BOUNDARY_SECONDS


def evaluate(
    y: np.ndarray,
    pred: np.ndarray,
    whole: np.ndarray | None = None,
    majority: np.ndarray | float | None = None,
) -> Dict[str, Any]:
    """Error in billed time, led by MAE. R² is kept but is not the headline: billed time
    varies by milliseconds within a chip, so R² swings on tiny absolute errors.

    ``majority`` is the most common whole-second bill in the training jobs. It gives the
    accuracy of always predicting that bill, the base rate for billedSecondsAccuracy.
    """
    y, pred = np.asarray(y, dtype=float), np.asarray(pred, dtype=float)
    out = {
        "n": int(len(y)),
        "maeMilliseconds": float(mean_absolute_error(y, pred) * 1e3),
        "r2": float(r2_score(y, pred)) if len(y) > 2 and np.std(y) > 1e-12 else None,
        "maeSeconds": float(mean_absolute_error(y, pred)),
        "mapePercent": float(np.mean(np.abs(pred - y) / y) * 100),
        "biasSeconds": float(np.mean(pred - y)),
        "maxErrorSeconds": float(np.max(np.abs(pred - y))),
    }
    if whole is not None:
        whole = np.asarray(whole, dtype=float)
        hit = np.ceil(pred - 1e-9) == whole
        close = near_boundary(y)
        out["billedSecondsAccuracy"] = float(np.mean(hit))
        out["nearBoundaryJobs"] = int(close.sum())
        out["nearBoundaryAccuracy"] = float(hit[close].mean()) if close.any() else None
        if majority is not None:
            base = np.broadcast_to(np.asarray(majority, dtype=float), whole.shape) == whole
            out["majorityBaselineAccuracy"] = float(base.mean())
            out["nearBoundaryMajorityAccuracy"] = float(base[close].mean()) if close.any() else None
    return out


def majority_bill(whole: pd.Series | np.ndarray) -> float:
    """Most common whole-second bill (smallest on ties)."""
    values, counts = np.unique(np.asarray(whole, dtype=float), return_counts=True)
    return float(values[np.argmax(counts)])


def assign_folds(frame: pd.DataFrame, n_splits: int, seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    cfgs = frame["config_id"].unique()
    order = rng.permutation(len(cfgs))
    return frame["config_id"].map({c: int(i % n_splits) for i, c in zip(order, cfgs)})


def unseen_circuit_validation(
    train: pd.DataFrame, n_splits: int = 5, n_repeats: int = 3, seed: int = 11
) -> Dict[str, Any]:
    """Repeated grouped K-fold by configuration; returns metrics and repeat-0 predictions."""
    models = build_models(seed)
    results: Dict[str, List[Dict[str, Any]]] = {name: [] for name in models}
    oof0: Dict[str, np.ndarray] = {}
    y = train[TARGET].to_numpy()
    for r in range(n_repeats):
        fold = assign_folds(train, n_splits, seed + r)
        preds = {name: np.full(len(train), np.nan) for name in models}
        majority = np.full(len(train), np.nan)
        for k in range(n_splits):
            te = (fold == k).to_numpy()
            majority[te] = majority_bill(train.loc[~te, "billed_whole_seconds"])
            for name, model in models.items():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    est = clone(model).fit(train.loc[~te], y[~te])
                preds[name][te] = est.predict(train.loc[te])
        for name in models:
            results[name].append(
                evaluate(y, preds[name], train["billed_whole_seconds"].to_numpy(), majority)
            )
            if r == 0:
                oof0[name] = preds[name]
    summary = {}
    for name, runs in results.items():
        keys = runs[0].keys()
        summary[name] = {k: float(np.mean([run[k] for run in runs])) if runs[0][k] is not None else None for k in keys}
        summary[name]["r2Sd"] = float(np.std([run["r2"] for run in runs]))
        for key in ("n", "nearBoundaryJobs"):
            summary[name][key] = runs[0][key]
    return {"metrics": summary, "oof": oof0, "nSplits": n_splits, "nRepeats": n_repeats}


def _clean(value):
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _write_waiting(report_dir: Path, coverage: List[Dict[str, Any]], reason: str) -> Dict[str, Any]:
    """No cost model can be fitted: say so in the report instead of raising."""
    report_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# QAQS execution-cost model", "", f"{WAITING}: {reason}", ""]
    lines += _coverage_lines(coverage)
    (report_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"cost model: {WAITING} ({reason})", flush=True)
    return {"status": WAITING, "reason": reason, "coverage": coverage}


def _coverage_lines(coverage: List[Dict[str, Any]]) -> List[str]:
    lines = ["## Usage-report coverage", "", "| Provider | Chips | Jobs | With RU report | Status |", "|---|---|---:|---:|---|"]
    for row in coverage:
        lines.append(f"| {row['provider']} | {', '.join(row['chips'])} | {row['jobs']} | {row['withRu']} | {row['status']} |")
    return lines + [""]


def run(tables: Path = DEFAULT_TABLES, report_dir: Path = DEFAULT_REPORT, dashboard_out: Path = DEFAULT_DASHBOARD) -> Dict[str, Any]:
    full = load_ml_dataset(tables, include_validation=True).frame
    coverage = cost_coverage(full)
    data = cost_frame(tables, full)
    train = data[~data["validation"]].reset_index(drop=True)
    valid = data[data["validation"]].reset_index(drop=True)
    if data.empty:
        return _write_waiting(report_dir, coverage, "no job in this export has a resource-unit usage report.")
    if train["config_id"].nunique() < 5:
        return _write_waiting(report_dir, coverage, "fewer than five training configurations have a usage report.")
    print(f"cost model: {len(train)} training jobs, {len(valid)} new-run jobs", flush=True)

    cv = unseen_circuit_validation(train)
    models = build_models()
    fitted = {}
    newrun: Dict[str, Any] = {}
    y_tr = train[TARGET].to_numpy()
    majority = majority_bill(train["billed_whole_seconds"])
    train_chips = set(train["backend"])
    for name, model in models.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fitted[name] = clone(model).fit(train, y_tr)
        if valid.empty:
            continue
        p = fitted[name].predict(valid)
        newrun[name] = {"all": evaluate(valid[TARGET], p, valid["billed_whole_seconds"], majority)}
        for b in sorted(valid["backend"].unique()):
            mask = (valid.backend == b).to_numpy()
            newrun[name][b] = {
                **evaluate(valid.loc[mask, TARGET], p[mask], valid.loc[mask, "billed_whole_seconds"], majority),
                # False: predicted with the fallback per-shot constant, so the offset is unknown.
                "chipSeenInTraining": b in train_chips,
            }
    primary = PRIMARY
    p_valid = fitted[primary].predict(valid) if len(valid) else np.array([])

    # Final deployed model: same procedure on every job with an RU report.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        final = clone(models[primary]).fit(data, data[TARGET].to_numpy())
    physical = final.physical_.terms()
    # The shot-count calculator needs the per-shot and overhead terms; record the fit quality
    # of the circuit-time decomposition so the dashboard can state it.
    circ_pred = final.physical_.predict_circuit_seconds(data)
    physical["circuitTimeMaeMilliseconds"] = float(np.mean(np.abs(circ_pred - data["circuit_seconds"])) * 1e3)
    report_dir.mkdir(parents=True, exist_ok=True)
    model_path = report_dir / "cost_model.joblib"
    joblib.dump(
        {
            "schema_version": SCHEMA_VERSION,
            "target": "billed QPU seconds (resource units x 60)",
            "features": list(FEATURES),
            "pipeline": final,
            "physical_terms": physical,
            "trained_jobs": int(len(data)),
            "shots_seen": sorted(int(s) for s in data["shots"].unique()),
        },
        model_path,
        compress=3,
    )

    # Points for the dashboard: training out-of-fold (repeat 0) + new-run predictions.
    def pts(frame: pd.DataFrame, pred: np.ndarray, split: str) -> List[Dict[str, Any]]:
        g = frame.assign(pred=pred).groupby(["backend", "config_id", "algorithm"], as_index=False).agg(
            observed=(TARGET, "mean"), predicted=("pred", "mean"), duration=("duration_s", "mean"),
            circuit=("circuit_seconds", "mean"), whole=("billed_whole_seconds", "max"), jobs=(TARGET, "size"),
            twirling=("twirling", "max"), dynamic=("dynamic", "max"), depth=("b.depth", "mean"),
        )
        g["split"] = split
        return g.to_dict(orient="records")

    points = pts(train, cv["oof"][primary], "unseen_circuit") + pts(valid, p_valid, "new_run")

    # Per-algorithm cost profile (typical job) from every job.
    profile = (
        data.groupby("algorithm")
        .agg(jobs=(TARGET, "size"), medianSeconds=(TARGET, "median"), maxSeconds=(TARGET, "max"),
             medianCircuitSeconds=("circuit_seconds", "median"), threeSecondShare=("billed_whole_seconds", lambda s: float((s >= 3).mean())))
        .reset_index()
        .sort_values("medianSeconds")
        .to_dict(orient="records")
    )

    manifest = tables / "dataset_manifest.json"
    parts = json.loads(manifest.read_text(encoding="utf-8"))["parts"]
    snapshot = _clean(
        {
            "schemaVersion": SCHEMA_VERSION,
            "backend": "cost-v1",
            "manifestHash": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "inputs": {p["file"]: hashlib.sha256((tables / p["file"]).read_bytes()).hexdigest() for p in parts},
            "secondsPerRu": SECONDS_PER_RU,
            "ibmRule": {"overheadSeconds": IBM_OVERHEAD_S, "perExecutionSeconds": IBM_PER_EXECUTION_S},
            "jobs": {
                "total": int(len(data)),
                "training": int(len(train)),
                "newRun": int(len(valid)),
                "withoutRu": int(len(full) - len(data)),
                "newRunChipsUnseenInTraining": sorted(set(valid["backend"]) - train_chips),
                "chips": sorted(data["backend"].unique().tolist()),
                "shots": sorted(int(s) for s in data["shots"].unique()),
            },
            "observed": {
                "medianSeconds": float(data[TARGET].median()),
                "medianRus": float(data["cost_rus"].median()),
                "medianCircuitSeconds": float(data["circuit_seconds"].median()),
                "overheadShare": float(1 - (data["circuit_seconds"] / data[TARGET]).median()),
                "threeSecondShare": float((data["billed_whole_seconds"] >= 3).mean()),
                "totalRus": float(data["cost_rus"].sum()),
            },
            "primaryModel": primary,
            "coverage": coverage,
            "waitingForData": [row["provider"] for row in coverage if row["status"] == WAITING],
            "majorityBilledSeconds": majority,
            "nearBoundarySeconds": NEAR_BOUNDARY_SECONDS,
            "physicalTerms": physical,
            "unseenCircuit": {"nSplits": cv["nSplits"], "nRepeats": cv["nRepeats"], "metrics": cv["metrics"]},
            "newRun": newrun,
            "profile": profile,
            "points": points,
        }
    )
    dashboard_out.parent.mkdir(parents=True, exist_ok=True)
    dashboard_out.write_text(json.dumps(snapshot, separators=(",", ":"), allow_nan=False, sort_keys=True), encoding="utf-8")
    _write_report(snapshot, report_dir)
    return snapshot


def _write_report(s: Dict[str, Any], report_dir: Path) -> None:
    f = lambda v, nd=3: "—" if v is None else f"{v:.{nd}f}"  # noqa: E731
    pct = lambda v: "—" if v is None else f"{100 * v:.1f}%"  # noqa: E731
    o, t = s["observed"], s["physicalTerms"]
    head = s["newRun"].get(s["primaryModel"], {}).get("all")
    lines = ["# QAQS execution-cost model", ""]
    if head:
        lines += [
            f"**New-run MAE {head['maeMilliseconds']:.1f} ms** on {head['n']} jobs. Whole-second bill "
            f"correct for {pct(head['billedSecondsAccuracy'])}; always predicting "
            f"{s['majorityBilledSeconds']:.0f} s is correct for {pct(head.get('majorityBaselineAccuracy'))}. "
            f"Among the {head['nearBoundaryJobs']} jobs within {s['nearBoundarySeconds'] * 1e3:.0f} ms of a "
            f"whole second: {pct(head['nearBoundaryAccuracy'])} against "
            f"{pct(head.get('nearBoundaryMajorityAccuracy'))} for that baseline.",
            "",
        ]
    else:
        lines += [f"New-run validation: {WAITING} (no validation job has a usage report).", ""]
    lines += [
        f"Target: billed QPU seconds = resource units × {s['secondsPerRu']:.0f} (1 RU = 1 minute of QPU time). "
        f"{s['jobs']['total']} jobs with an RU report on {', '.join(s['jobs']['chips'])}; "
        f"{s['jobs']['withoutRu']} jobs have no RU report and are excluded. "
        f"Every job ran {', '.join(map(str, s['jobs']['shots']))} shots.",
        "",
        f"Observed: median {o['medianSeconds']:.3f} s ({o['medianRus']:.5f} RU) per job; the circuit itself "
        f"runs {o['medianCircuitSeconds']:.3f} s, so {o['overheadShare'] * 100:.0f}% of the bill is per-job overhead. "
        f"{o['threeSecondShare'] * 100:.1f}% of jobs are billed 3 whole seconds instead of 2.",
        "",
        "## Physical terms (fitted on all jobs)",
        "",
        "The usage reports follow a billing formula, which these terms recover. Billed time minus IBM's "
        "circuit-execution time is one constant per runtime configuration, and circuit time is "
        "shots × (a chip constant + scheduled duration). Accuracy here is agreement with that formula.",
        "",
        f"billed ≈ {t['overheadSeconds']:.3f} s per job + shots × (chip constant + "
        f"{t['durationSlope']:.3f} × scheduled duration). Twirled jobs add {t['twirlingOverheadSeconds']:.3f} s "
        f"per job and {t['twirlingPerShotSeconds'] * 1e6:.1f} µs + {t['twirlingDurationSlope']:.2f} × duration per shot.",
        "",
        "| Chip | Per-shot constant (µs) |",
        "|---|---:|",
    ]
    for chip, value in sorted(t.get("perShotSecondsByChip", {}).items()):
        lines.append(f"| {chip} | {value * 1e6:.2f} |")
    lines += [
        f"| any other chip (fallback: job-weighted average) | {t['perShotSeconds'] * 1e6:.2f} |",
        "",
        f"The chip constants span {t.get('perShotChipSpreadSeconds', 0.0) * 1e6:.1f} µs per shot. A chip without "
        "usage reports is predicted with the fallback and carries an unknown offset of that order "
        "per shot until it has data.",
        "",
        f"For comparison, IBM's published rule is ~{s['ibmRule']['overheadSeconds']:.0f} s per job + "
        f"{s['ibmRule']['perExecutionSeconds'] * 1e6:.0f} µs per execution (250 µs default rep_delay + a typical circuit).",
        "",
        "## Unseen-circuit validation (training campaigns, grouped K-fold)",
        "",
        "Whole-second accuracy is shown beside two references: the accuracy of always predicting the "
        f"most common training bill, and both figures on jobs within {s['nearBoundarySeconds'] * 1e3:.0f} ms "
        "of a whole second, where the bill can flip. R² is last: billed time varies by milliseconds "
        "within a chip, so R² moves on errors that do not change the bill.",
        "",
        "| Model | MAE (ms) | MAPE % | Whole-second accuracy | Majority baseline | Near boundary: jobs | Near boundary: accuracy | Near boundary: majority | R² |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def row(label: str, m: Dict[str, Any]) -> str:
        return (
            f"| {label} | {f(m['maeMilliseconds'], 1)} | {f(m['mapePercent'], 2)} | {pct(m.get('billedSecondsAccuracy'))} | "
            f"{pct(m.get('majorityBaselineAccuracy'))} | {m.get('nearBoundaryJobs', '—')} | "
            f"{pct(m.get('nearBoundaryAccuracy'))} | {pct(m.get('nearBoundaryMajorityAccuracy'))} | {f(m['r2'])} |"
        )

    for name, m in s["unseenCircuit"]["metrics"].items():
        lines.append(row(name, m))
    lines += ["", "## New-run validation (validation jobs; cost not pre-registered)", ""]
    if not s["newRun"]:
        lines += [f"{WAITING}: no validation job has a usage report.", ""]
    else:
        unseen = s["jobs"].get("newRunChipsUnseenInTraining", [])
        if unseen:
            lines += [
                f"Chips with no training jobs, predicted with the fallback constant: {', '.join(unseen)}. "
                "Their rows measure the unknown-chip offset, not the model with a known chip constant.",
                "",
            ]
        lines += [
            "| Model · scope | MAE (ms) | MAPE % | Whole-second accuracy | Majority baseline | Near boundary: jobs | Near boundary: accuracy | Near boundary: majority | R² |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for name, by in s["newRun"].items():
            for scope, m in by.items():
                flag = " (chip unseen in training)" if m.get("chipSeenInTraining") is False else ""
                lines.append(row(f"{name} · {scope}{flag}", m))
        lines.append("")
    lines += _coverage_lines(s["coverage"])
    if s["waitingForData"]:
        lines += [f"{WAITING}: no usage report in resource units for {', '.join(s['waitingForData'])}.", ""]
    lines += [
        "Predictions at other shot counts use the physical terms only; the residual model has no shot "
        "input and is applied only at the shot counts it was fitted on. The data contains "
        f"{', '.join(map(str, s['jobs']['shots']))}-shot jobs only, so shot scaling is an assumption "
        "(IBM's published structure, with a per-job overhead that does not depend on shots), not validated.",
    ]
    (report_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    # Run through the importable module, not `__main__`: classes pickled while this file runs as a
    # script are recorded as `__main__.HybridCostModel` and cannot be loaded anywhere else.
    from experiments import qaqs_cost as canonical

    if canonical is not sys.modules[__name__]:
        return canonical.main()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--dashboard-out", type=Path, default=DEFAULT_DASHBOARD)
    args = parser.parse_args()
    s = run(args.tables, args.report_out, args.dashboard_out)
    p = s.get("newRun", {}).get(s.get("primaryModel"), {}).get("all")
    if p:
        print(
            f"new-run MAE {p['maeMilliseconds']:.1f} ms; whole-second accuracy {p['billedSecondsAccuracy']:.3f} "
            f"(majority baseline {p['majorityBaselineAccuracy']:.3f}); report: {args.report_out / 'report.md'}"
        )
    else:
        print(f"new-run validation: {WAITING}; report: {args.report_out / 'report.md'}")


if __name__ == "__main__":
    main()
