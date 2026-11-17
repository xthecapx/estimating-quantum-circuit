"""QAQS execution-cost model: predict billed QPU time (resource units) before running.

IBM bills QPU time in resource units (RUs); 1 RU = 1 minute of QPU time for standard
workloads. Each job's usage report gives the RUs, the billed time rounded up to whole
seconds, and the time spent executing the circuit. This module predicts billed
seconds (``g.cost_rus * 60``) from pre-runtime information only: the compiled circuit,
its scheduled duration, the runtime options, and the number of shots.

One model for every chip (no chip feature): cost is a property of the job, and the three
Heron chips bill at the same rate.

Why the model has a physical part. Every job in this dataset ran 1,024 shots of one
circuit, and billed time is dominated by a fixed per-job overhead (~1.70 s) plus about
1,024 x (scheduled duration + reset/readout time). An ML model trained only on 1,024-shot
jobs cannot learn how cost scales with shots. So the model is

    billed_seconds = overhead + shots x (per_shot + slope x duration) + residual(circuit)

The physical terms are fitted on the training data; a tree model learns the residual
from circuit features (twirling, dynamic circuits, depth). Predictions at other shot
counts reuse the fitted per-shot terms; that extrapolation is reported as an assumption,
not a validated result.

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


def _flag(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "1.0"}).astype(float)


def cost_frame(tables: Path = DEFAULT_TABLES) -> pd.DataFrame:
    """Jobs with a resource-unit usage report, with cost targets and pre-runtime inputs."""
    frame = load_ml_dataset(tables, include_validation=True).frame
    ru = pd.to_numeric(frame.get("g.cost_rus"), errors="coerce")
    frame = frame[ru.notna()].copy()
    out = pd.DataFrame(index=frame.index)
    out["job_id"] = frame["meta.job_id"]
    out["config_id"] = frame["meta.config_id"].astype(str)
    out["algorithm"] = frame["meta.algorithm"].astype(str)
    out["backend"] = frame["meta.backend_name"].astype(str)
    out["campaign"] = frame["meta.campaign_id"].astype(str)
    out["validation"] = frame["meta.campaign_id"].map(is_validation_campaign)
    out["cost_rus"] = pd.to_numeric(frame["g.cost_rus"])
    out[TARGET] = out["cost_rus"] * SECONDS_PER_RU
    out["billed_whole_seconds"] = pd.to_numeric(frame["g.billed_seconds"])
    out["circuit_seconds"] = pd.to_numeric(frame["g.circuit_execution_seconds"])
    out["shots"] = pd.to_numeric(frame["meta.shots"])
    # Scheduled duration of one shot; dynamic circuits are not scheduled (NaN -> imputed).
    out["duration_s"] = pd.to_numeric(frame.get("c.duration_s"), errors="coerce")
    out["twirling"] = _flag(frame["g.twirling_gates"])
    out["dynamic"] = _flag(frame["g.dynamic_circuit"])
    out["dynamical_decoupling"] = _flag(frame["g.dynamical_decoupling"])
    for col in CIRCUIT_FEATURES:
        out[col] = pd.to_numeric(frame.get(col), errors="coerce")
    return out.reset_index(drop=True)


FEATURES: tuple[str, ...] = ("shots", "duration_s") + FLAG_FEATURES + CIRCUIT_FEATURES


class PhysicalCostModel(BaseEstimator, RegressorMixin):
    """billed = overhead + shots * per_shot(duration, twirling), following IBM's usage formula.

    Every job in the data ran the same number of shots, so overhead and per-shot cost are
    not separable from billed time alone (they are collinear). They are separated with
    IBM's measured circuit-execution time, which is training-label information only and
    is never an input at prediction time:

    1. per-shot time = circuit_seconds / shots, regressed on scheduled duration and
       twirling (``a + b*duration + c*duration*twirling + d*twirling``);
    2. overhead = billed - shots * per-shot, averaged (separately for twirled jobs).

    Missing durations (dynamic circuits are not scheduled) use the training median.
    """

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        y = np.asarray(y, dtype=float)
        self.duration_fill_ = float(np.nanmedian(X["duration_s"])) if X["duration_s"].notna().any() else 0.0
        shots = X["shots"].to_numpy(dtype=float)
        per_shot = X["circuit_seconds"].to_numpy(dtype=float) / shots
        self.shot_coef_, *_ = np.linalg.lstsq(self._shot_design(X), per_shot, rcond=None)
        rest = y - shots * (self._shot_design(X) @ self.shot_coef_)
        tw = X["twirling"].to_numpy(dtype=float)
        self.overhead_ = float(rest[tw == 0].mean()) if (tw == 0).any() else float(rest.mean())
        self.overhead_twirling_ = float(rest[tw == 1].mean() - self.overhead_) if (tw == 1).any() else 0.0
        return self

    def _shot_design(self, X: pd.DataFrame) -> np.ndarray:
        dur = X["duration_s"].fillna(self.duration_fill_).to_numpy(dtype=float)
        tw = X["twirling"].to_numpy(dtype=float)
        return np.c_[np.ones(len(X)), dur, dur * tw, tw]

    def predict_circuit_seconds(self, X: pd.DataFrame) -> np.ndarray:
        return X["shots"].to_numpy(dtype=float) * (self._shot_design(X) @ self.shot_coef_)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        tw = X["twirling"].to_numpy(dtype=float)
        return self.overhead_ + self.overhead_twirling_ * tw + self.predict_circuit_seconds(X)

    def terms(self) -> Dict[str, float]:
        a, b, c, d = self.shot_coef_
        return {
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
        resid = y - self.physical_.predict(X)
        self.imputer_ = SimpleImputer(strategy="median", keep_empty_features=True)
        Z = self.imputer_.fit_transform(X[list(FEATURES)])
        self.residual_ = GradientBoostingRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=self.random_state
        ).fit(Z, resid)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.physical_.predict(X) + self.residual_.predict(self.imputer_.transform(X[list(FEATURES)]))


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


def evaluate(y: np.ndarray, pred: np.ndarray, whole: np.ndarray | None = None) -> Dict[str, Any]:
    y, pred = np.asarray(y, dtype=float), np.asarray(pred, dtype=float)
    out = {
        "n": int(len(y)),
        "r2": float(r2_score(y, pred)) if len(y) > 2 and np.std(y) > 1e-12 else None,
        "maeSeconds": float(mean_absolute_error(y, pred)),
        "maeMilliseconds": float(mean_absolute_error(y, pred) * 1e3),
        "mapePercent": float(np.mean(np.abs(pred - y) / y) * 100),
        "biasSeconds": float(np.mean(pred - y)),
        "maxErrorSeconds": float(np.max(np.abs(pred - y))),
    }
    if whole is not None:
        out["billedSecondsAccuracy"] = float(np.mean(np.ceil(pred - 1e-9) == np.asarray(whole)))
    return out


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
        for k in range(n_splits):
            te = (fold == k).to_numpy()
            for name, model in models.items():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    est = clone(model).fit(train.loc[~te], y[~te])
                preds[name][te] = est.predict(train.loc[te])
        for name in models:
            results[name].append(evaluate(y, preds[name], train["billed_whole_seconds"].to_numpy()))
            if r == 0:
                oof0[name] = preds[name]
    summary = {}
    for name, runs in results.items():
        keys = runs[0].keys()
        summary[name] = {k: float(np.mean([run[k] for run in runs])) if runs[0][k] is not None else None for k in keys}
        summary[name]["r2Sd"] = float(np.std([run["r2"] for run in runs]))
        summary[name]["n"] = runs[0]["n"]
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


def run(tables: Path = DEFAULT_TABLES, report_dir: Path = DEFAULT_REPORT, dashboard_out: Path = DEFAULT_DASHBOARD) -> Dict[str, Any]:
    data = cost_frame(tables)
    train = data[~data["validation"]].reset_index(drop=True)
    valid = data[data["validation"]].reset_index(drop=True)
    print(f"cost model: {len(train)} training jobs, {len(valid)} new-run jobs", flush=True)

    cv = unseen_circuit_validation(train)
    models = build_models()
    fitted = {}
    newrun: Dict[str, Any] = {}
    y_tr = train[TARGET].to_numpy()
    for name, model in models.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fitted[name] = clone(model).fit(train, y_tr)
        p = fitted[name].predict(valid)
        newrun[name] = {
            "all": evaluate(valid[TARGET], p, valid["billed_whole_seconds"]),
            **{
                b: evaluate(valid.loc[valid.backend == b, TARGET], p[(valid.backend == b).to_numpy()],
                            valid.loc[valid.backend == b, "billed_whole_seconds"])
                for b in sorted(valid["backend"].unique())
            },
        }
    primary = "QAQS cost (physical + residual)"
    p_valid = fitted[primary].predict(valid)

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
                "withoutRu": int(len(load_ml_dataset(tables, include_validation=True).frame) - len(data)),
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
    o, t = s["observed"], s["physicalTerms"]
    lines = [
        "# QAQS execution-cost model",
        "",
        f"Target: billed QPU seconds = resource units × {s['secondsPerRu']:.0f} (1 RU = 1 minute of QPU time). "
        f"{s['jobs']['total']} jobs with an RU report on {', '.join(s['jobs']['chips'])}; "
        f"{s['jobs']['withoutRu']} older jobs report whole seconds only and are excluded. "
        f"Every job ran {', '.join(map(str, s['jobs']['shots']))} shots.",
        "",
        f"Observed: median {o['medianSeconds']:.3f} s ({o['medianRus']:.5f} RU) per job; the circuit itself "
        f"runs {o['medianCircuitSeconds']:.3f} s, so {o['overheadShare'] * 100:.0f}% of the bill is per-job overhead. "
        f"{o['threeSecondShare'] * 100:.1f}% of jobs are billed 3 whole seconds instead of 2.",
        "",
        "## Physical terms (fitted on all jobs)",
        "",
        f"billed ≈ {t['overheadSeconds']:.3f} s per job + shots × ({t['perShotSeconds'] * 1e6:.1f} µs + "
        f"{t['durationSlope']:.3f} × scheduled duration). Twirled jobs add {t['twirlingOverheadSeconds']:.3f} s "
        f"per job and {t['twirlingPerShotSeconds'] * 1e6:.1f} µs + {t['twirlingDurationSlope']:.2f} × duration per shot.",
        "",
        f"For comparison, IBM's published rule is ~{s['ibmRule']['overheadSeconds']:.0f} s per job + "
        f"{s['ibmRule']['perExecutionSeconds'] * 1e6:.0f} µs per execution (250 µs default rep_delay + a typical circuit).",
        "",
        "## Unseen-circuit validation (training campaigns, grouped K-fold)",
        "",
        "| Model | R² | MAE (ms) | MAPE % | Billed-second accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, m in s["unseenCircuit"]["metrics"].items():
        lines.append(f"| {name} | {f(m['r2'])} | {f(m['maeMilliseconds'], 1)} | {f(m['mapePercent'], 2)} | {f(m.get('billedSecondsAccuracy'))} |")
    lines += ["", "## New-run validation (validation-v1 jobs; cost not pre-registered)", "",
              "| Model | Scope | R² | MAE (ms) | MAPE % | Billed-second accuracy |", "|---|---|---:|---:|---:|---:|"]
    for name, by in s["newRun"].items():
        for scope, m in by.items():
            lines.append(f"| {name} | {scope} | {f(m['r2'])} | {f(m['maeMilliseconds'], 1)} | {f(m['mapePercent'], 2)} | {f(m.get('billedSecondsAccuracy'))} |")
    lines += ["", "Predictions at other shot counts use the fitted per-shot terms; the data only contains "
              "1,024-shot jobs, so that scaling is an assumption (IBM's published structure), not validated."]
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
    p = s["newRun"][s["primaryModel"]]["all"]
    print(f"new-run MAE {p['maeMilliseconds']:.1f} ms, R² {p['r2']:.3f}; report: {args.report_out / 'report.md'}")


if __name__ == "__main__":
    main()
