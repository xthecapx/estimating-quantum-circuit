"""Repeated grouped K-fold evaluation for QAQS (thesis Phase 7-8 headline numbers).

Every circuit configuration is tested exactly once per repeat by a model that never
saw it. Everything learned from data happens inside the training folds:

* footprint selection (VIF screen -> SHAP/permutation rank -> top-k, one-SE rule),
* calibration-feature selection,
* hyperparameter tuning (small grid, inner grouped 3-fold CV),
* model choice (best inner-CV R^2).

The score of this whole *procedure* is the honest H1 estimate. Per-model scores are
reported too, but picking the best of them after the fact is optimistic.

Fold assignment is by ``meta.config_id`` and is shared across chips, so the pooled
scope never trains on a circuit that is being tested on another chip.

What is scored (see ``headline_mask``): the composite anchor (Shor) sits at its chance
level, so separating it from the rest earns R^2 without predicting anything. Raw
targets are therefore scored without it; the chance-corrected success target scores
every job. Every headline number comes with a noise ceiling, a config-mean R^2, a
per-algorithm breakdown and a plain size baseline (``_diagnostics``).

Nothing here names a chip or a provider: scopes, splits and calibration columns are
derived from the dataset. Analyses that need more than one provider return
``WAITING_FOR_DATA`` until that data is exported.

Naming used in the thesis (see ``VALIDATION_NAMES``):

* **Unseen-circuit validation** -- this module's repeated grouped K-fold.
* **Calibration-cycle validation** -- the forward temporal holdout, kept per chip
  (``_temporal_drift``); the only internal evidence on a later calibration cycle.
* **Prospective validation** -- frozen models scored on a new run.
"""

from __future__ import annotations

import math
import warnings
from collections import Counter
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import clone
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline

from experiments.footprint_analysis import select_best_footprint
from experiments.ml_dataset import (
    ALL_TARGETS,
    CHANCE_CORRECTED_TARGETS,
    COMPOSITE_ANCHOR,
    CORE_ALGORITHMS,
    FAMILIES,
    RANDOM_ALGORITHM,
    DatasetBundle,
    add_chip_indicators,
    baseline_predictions,
    chip_indicator_columns,
    headline_mask,
    infer_provider,
    split_temporal_and_cv,
    temporal_ordering,
)
from experiments.qaqs_models import (
    H1_R2_THRESHOLD,
    MODEL_LABELS,
    REGIME_LABELS,
    SCHEMA_VERSION,
    SIZE_BASELINE_FEATURES,
    _aggregate_scatter_points,
    _clean_json,
    _fit_predict,
    _group_cv_predictions,
    _run_h3_hardware_boundary,
    _save_regime_model,
    _select_device_predictors,
    _select_hardware_predictors,
    _usable_columns,
    build_hurdle,
    build_models,
    cluster_bootstrap_r2_diff,
    evaluate_predictions,
    h1_verdict,
)

WAITING_FOR_DATA = "WAITING FOR DATA"

# Thesis names for the three QAQS validation tests. Keep in sync with VALIDATION in
# dashboard/src/views/estimation/model.ts and with the manuscript.
VALIDATION_NAMES: dict[str, dict[str, str]] = {
    "unseen_circuit": {
        "name": "Unseen-circuit validation",
        "method": "repeated grouped K-fold by circuit configuration",
        "question": "Does QAQS predict circuits it has never seen?",
    },
    "calibration_cycle": {
        "name": "Calibration-cycle validation",
        "method": "forward temporal holdout: earlier windows -> latest window",
        "question": "Does QAQS predict a later calibration cycle?",
    },
    "prospective": {
        "name": "Prospective validation",
        "method": "frozen models, new IBM run, predictions committed before results",
        "question": "Does QAQS predict a run that did not exist at training time?",
    },
}

PARAM_GRIDS: dict[str, list[dict[str, Any]]] = {
    "LR": [{"model__alpha": a} for a in (0.1, 1.0, 10.0)],
    "DTR": [{"model__max_depth": d} for d in (4, 6, 10)],
    "RF": [{"model__min_samples_leaf": m} for m in (1, 2, 5)],
    "KNN": [{"model__n_neighbors": k} for k in (5, 9, 15)],
    "SVR": [{"model__C": c} for c in (0.5, 2.0, 8.0)],
    "XGBoost": [
        {"model__max_depth": d, "model__learning_rate": lr}
        for d, lr in ((3, 0.1), (5, 0.07), (7, 0.05))
    ],
    "LightGBM": [{"model__num_leaves": n} for n in (15, 31, 63)],
    "Stacking (AutoML)": [{}],
}

FOOTPRINT_KWARGS = dict(
    max_vif=10.0,
    max_candidates=16,
    min_features=5,
    max_selected=10,
    r2_tolerance=0.0015,
)

# A footprint feature is "stable" when it is selected in at least this share of folds.
STABLE_SELECTION_FREQUENCY = 0.80
# Targets with at least this share of jobs at the floor also get a two-stage model.
HURDLE_FLOOR = 0.02
HURDLE_MIN_SHARE = 0.05
WINDOW_CODE = "_window_code"

# Analytical M2 estimate expressed in each target's space (pre-runtime: it uses
# only the circuit and the calibration at submission). DSR has no counterpart.
M2_PRIOR = {
    "success": ("e.m2_error", lambda s: 1.0 - s),
    "tvd": ("e.m2_tvd", lambda s: s),
    "hellinger": ("e.m2_tvd", lambda s: 1.0 - s),
}

MIN_TRAIN_ROWS = 20


# --------------------------------------------------------------------------- folds


def assign_config_folds(
    frame: pd.DataFrame,
    n_splits: int = 5,
    n_repeats: int = 3,
    seed: int = 11,
) -> pd.DataFrame:
    """Return a table ``config_id -> fold`` for each repeat (columns ``r0``, ``r1``, ...).

    Stratified by algorithm and size: each algorithm's configurations are sorted by
    median two-qubit gate count and dealt out in blocks of ``n_splits``, with a fresh
    random fold order inside every block. Each fold therefore spans small and large
    circuits of every algorithm. Built from the whole dataset so every scope shares it.
    """
    size_col = "b.two_qubit_gates" if "b.two_qubit_gates" in frame.columns else "a.num_qubits"
    cfg = (
        frame.assign(_size=pd.to_numeric(frame[size_col], errors="coerce"))
        .groupby("meta.config_id")
        .agg(algorithm=("meta.algorithm", "first"), size=("_size", "median"))
        .reset_index()
    )
    rng = np.random.default_rng(seed)
    out = pd.DataFrame({"meta.config_id": cfg["meta.config_id"].astype(str)})
    for r in range(n_repeats):
        fold = pd.Series(-1, index=cfg.index, dtype=int)
        for _, grp in cfg.groupby("algorithm"):
            ordered = grp.sort_values(["size", "meta.config_id"]).index.to_numpy()
            for start in range(0, len(ordered), n_splits):
                block = ordered[start : start + n_splits]
                fold.loc[block] = rng.permutation(n_splits)[: len(block)]
        out[f"r{r}"] = fold.to_numpy()
    return out.set_index("meta.config_id")


# ------------------------------------------------------------------- tuning/models


def tune_model(
    name: str,
    pipe: Pipeline,
    X: pd.DataFrame,
    y: np.ndarray,
    groups: pd.Series,
    inner_splits: int = 3,
) -> tuple[dict[str, Any], float | None]:
    """Pick the grid point with the best inner grouped-CV R^2. Failing points are skipped."""
    best_params: dict[str, Any] = {}
    best_r2: float | None = None
    for params in PARAM_GRIDS.get(name, [{}]):
        try:
            est = clone(pipe).set_params(**params)
            pred = _group_cv_predictions(est, X, y, groups, max_splits=inner_splits)
            r2 = evaluate_predictions(y, pred)["r2"]
        except Exception:  # noqa: BLE001 - e.g. KNN neighbours > rows in a tiny fold
            continue
        if r2 is not None and (best_r2 is None or r2 > best_r2):
            best_params, best_r2 = params, r2
    return best_params, best_r2


def _fit_regime(
    train: pd.DataFrame,
    test: pd.DataFrame | None,
    cols: list[str],
    target_col: str,
    tune: bool,
    random_state: int,
) -> dict[str, Any]:
    """Tune each model on ``train`` (inner CV), choose the best, predict ``test``."""
    models = build_models(random_state=random_state)
    y = train[target_col].to_numpy(dtype=float)
    groups = train["meta.config_id"]
    per_model: dict[str, Any] = {}
    names = list(models) if tune else ["LightGBM"]
    for name in names:
        params, inner_r2 = tune_model(name, models[name], train[cols], y, groups) if tune else ({}, None)
        entry: dict[str, Any] = {"params": params, "innerR2": inner_r2}
        if test is not None and len(test):
            try:
                est = clone(models[name]).set_params(**params)
                entry["pred"] = _fit_predict(est, train[cols], y, test[cols])
            except Exception:  # noqa: BLE001
                continue
        per_model[name] = entry
    ranked = sorted(
        per_model,
        key=lambda n: per_model[n]["innerR2"] if per_model[n]["innerR2"] is not None else -math.inf,
        reverse=True,
    )
    return {"perModel": per_model, "selected": ranked[0] if ranked else None}


def _fit_fixed(
    train: pd.DataFrame,
    test: pd.DataFrame,
    cols: list[str],
    target_col: str,
    name: str,
    pipe: Pipeline,
) -> dict[str, Any]:
    """One untuned model: used for the comparison regimes, where tuning is not the point."""
    y = train[target_col].to_numpy(dtype=float)
    try:
        pred = _fit_predict(pipe, train[cols], y, test[cols])
    except Exception:  # noqa: BLE001
        return {"perModel": {}, "selected": None, "nFeatures": len(cols)}
    return {"perModel": {name: {"params": {}, "innerR2": None, "pred": pred}}, "selected": name, "nFeatures": len(cols)}


def _nested_fold(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
    circuit_pool: list[str],
    hw_pool: list[str],
    random_state: int,
    device_pool: Sequence[str] = (),
    hurdle: bool = False,
    chip_cols: Sequence[str] = (),
) -> dict[str, Any]:
    """One outer fold: all selection on ``train``; predictions for ``test`` only.

    ``circuit_only``, ``mixed_submit`` and, in a multi-chip scope, ``circuit_chip``
    (footprint + one-hot chip id) are the deployed procedures: tuned, model chosen by
    inner CV. The other regimes are fixed-LightGBM comparisons.
    """
    warnings.simplefilter("ignore")
    models = build_models(random_state=random_state)
    fp_cols, _, _ = select_best_footprint(
        train,
        train.iloc[0:0],
        circuit_pool,
        target_col,
        contrib_model=models["XGBoost"],
        ablation_model=models["LightGBM"],
        groups=train["meta.config_id"],
        random_state=random_state,
        **FOOTPRINT_KWARGS,
    )
    hw_cols = _select_hardware_predictors(train, hw_pool, target_col)
    dev_cols = _select_device_predictors(train, device_pool)
    size_cols = [c for c in SIZE_BASELINE_FEATURES if c in train.columns and train[c].notna().any()]
    regimes: dict[str, Any] = {}
    if fp_cols:
        regimes["circuit_only"] = _fit_regime(train, test, fp_cols, target_col, True, random_state)
        regimes["circuit_only"]["nFeatures"] = len(fp_cols)
        if hw_cols:
            regimes["mixed_submit"] = _fit_regime(train, test, fp_cols + hw_cols, target_col, True, random_state)
            regimes["mixed_submit"]["nFeatures"] = len(fp_cols + hw_cols)
    fixed: list[tuple[str, list[str]]] = [
        ("size_baseline", size_cols),
        ("hardware_only", dev_cols),
        ("layout_only", hw_cols),
    ]
    if fp_cols:
        fixed.append(("mixed_device", fp_cols + dev_cols if dev_cols else []))
        if WINDOW_CODE in train.columns and train[WINDOW_CODE].nunique() > 1:
            fixed.append(("circuit_window", fp_cols + [WINDOW_CODE]))
        if chip_cols:
            cols = fp_cols + list(chip_cols)
            regimes["circuit_chip"] = _fit_regime(train, test, cols, target_col, True, random_state)
            regimes["circuit_chip"]["nFeatures"] = len(cols)
    for regime, cols in fixed:
        if cols:
            regimes[regime] = _fit_fixed(train, test, cols, target_col, "LightGBM", models["LightGBM"])
    if hurdle and fp_cols:
        regimes["hurdle"] = _fit_fixed(train, test, fp_cols, target_col, "Hurdle", build_hurdle(random_state))
    return {
        "testIndex": test.index.to_numpy(),
        "footprint": fp_cols,
        "hardware": hw_cols,
        "device": dev_cols,
        "regimes": regimes,
    }


# ------------------------------------------------------------------ aggregation


def summarize_repeats(
    y: pd.Series,
    groups: pd.Series,
    preds_by_repeat: Sequence[pd.Series],
) -> dict[str, Any]:
    """Metrics per repeat on out-of-fold predictions, then mean (± sd for R^2)."""
    per: list[dict[str, Any]] = []
    for pred in preds_by_repeat:
        ok = pred.dropna().index
        if len(ok) < 3:
            continue
        per.append(
            evaluate_predictions(
                y.loc[ok].to_numpy(dtype=float),
                pred.loc[ok].to_numpy(dtype=float),
                groups.loc[ok].to_numpy(),
            )
        )
    if not per:
        return evaluate_predictions(np.array([]), np.array([]))

    def mean_of(key: str) -> float | None:
        vals = [m[key] for m in per if m.get(key) is not None]
        return float(np.mean(vals)) if vals else None

    r2_list = [m["r2"] for m in per if m["r2"] is not None]
    r2 = mean_of("r2")
    lo, hi = mean_of("r2CiLow"), mean_of("r2CiHigh")
    return {
        "n": int(per[0]["n"]),
        "r2": r2,
        "mae": mean_of("mae"),
        "rmse": mean_of("rmse"),
        "spearmanRho": mean_of("spearmanRho"),
        "r2Sd": float(np.std(r2_list)) if len(r2_list) > 1 else 0.0,
        "r2PerRepeat": r2_list,
        "nRepeats": len(per),
        "r2CiLow": lo,
        "r2CiHigh": hi,
        "meetsH1": bool(r2 is not None and r2 >= H1_R2_THRESHOLD),
        "h1Verdict": h1_verdict(r2, (lo, hi) if lo is not None and hi is not None else None),
    }


def _oof_series(
    index: pd.Index,
    folds: Sequence[dict[str, Any]],
    regime: str,
    which: str,
) -> pd.Series:
    """Out-of-fold predictions for one repeat: ``which`` = model name or "selected"."""
    out = pd.Series(np.nan, index=index, dtype=float)
    for fold in folds:
        reg = fold["regimes"].get(regime)
        if not reg:
            continue
        name = reg["selected"] if which == "selected" else which
        entry = reg["perModel"].get(name) if name else None
        if entry is not None and "pred" in entry:
            out.loc[fold["testIndex"]] = entry["pred"]
    return out


def _regime_leaderboard(
    valid: pd.DataFrame,
    target_col: str,
    folds_by_repeat: Mapping[int, list[dict[str, Any]]],
    regime: str,
    scored: pd.Series | None = None,
) -> tuple[list[dict[str, Any]], dict[int, pd.Series]]:
    """Scores on the ``scored`` jobs only; the returned predictions cover every job."""
    y = valid[target_col]
    groups = valid["meta.config_id"].astype(str)
    repeats = sorted(folds_by_repeat)
    procedure = {r: _oof_series(valid.index, folds_by_repeat[r], regime, "selected") for r in repeats}
    keep = scored if scored is not None else pd.Series(True, index=valid.index)

    def only(pred: pd.Series) -> pd.Series:
        return pred.where(keep)

    picks = Counter(
        fold["regimes"][regime]["selected"]
        for r in repeats
        for fold in folds_by_repeat[r]
        if regime in fold["regimes"] and fold["regimes"][regime]["selected"]
    )
    rows = [
        {
            "model": "QAQS (nested selection)",
            "label": "QAQS procedure: footprint, tuning and model chosen inside each fold",
            "kind": "procedure",
            "selectionCounts": dict(picks),
            "cv": summarize_repeats(y, groups, [only(procedure[r]) for r in repeats]),
            "holdout": None,
        }
    ]
    model_names = sorted(
        {
            name
            for r in repeats
            for fold in folds_by_repeat[r]
            for name in fold["regimes"].get(regime, {}).get("perModel", {})
        }
    )
    model_rows = []
    for name in model_names:
        preds = [only(_oof_series(valid.index, folds_by_repeat[r], regime, name)) for r in repeats]
        model_rows.append(
            {
                "model": name,
                "label": MODEL_LABELS.get(name, name),
                "kind": "ml_ensemble" if "Stacking" in name else "ml",
                "cv": summarize_repeats(y, groups, preds),
                "holdout": None,
            }
        )
    model_rows.sort(key=lambda row: row["cv"]["r2"] if row["cv"]["r2"] is not None else -999.0, reverse=True)
    return rows + model_rows, procedure


# ------------------------------------------------------------------ diagnostics


def noise_ceiling(frame: pd.DataFrame, target_col: str) -> dict[str, Any]:
    """How well repeats of one configuration on one chip predict each other.

    ``looReplicateR2``: R^2 of predicting each job by the mean of the *other* jobs of
    the same (chip, configuration). No pre-runtime model can beat it at job level,
    because the footprint is identical within a configuration.
    """
    d = frame[[target_col]].copy()
    d["_g"] = frame["meta.backend_name"].astype(str) + "|" + frame["meta.config_id"].astype(str)
    d = d[np.isfinite(d[target_col])]
    if len(d) < 6 or d[target_col].std() <= 1e-12:
        return {"looReplicateR2": None, "betweenConfigShare": None, "jobs": int(len(d))}
    grp = d.groupby("_g")[target_col]
    count, total = grp.transform("count"), grp.transform("sum")
    multi = count > 1
    y = d.loc[multi, target_col]
    loo = (total[multi] - y) / (count[multi] - 1)
    within = float(((d[target_col] - grp.transform("mean")) ** 2).sum())
    tot = float(((d[target_col] - d[target_col].mean()) ** 2).sum())
    return {
        "looReplicateR2": float(r2_score(y, loo)) if len(y) >= 6 and y.std() > 1e-12 else None,
        "betweenConfigShare": float(1.0 - within / tot) if tot > 0 else None,
        "jobs": int(len(d)),
        "replicatedJobs": int(multi.sum()),
        "medianRepeats": float(count.groupby(d["_g"]).first().median()),
    }


def _config_mean_r2(frame: pd.DataFrame, y: pd.Series, preds: Sequence[pd.Series]) -> dict[str, Any]:
    """R^2 after averaging observed and predicted over repeats of a (chip, configuration)."""
    key = frame["meta.backend_name"].astype(str) + "|" + frame["meta.config_id"].astype(str)
    out, cis = [], []
    for pred in preds:
        ok = pred.dropna().index
        if len(ok) < 6:
            continue
        g = pd.DataFrame({"y": y.loc[ok], "p": pred.loc[ok], "k": key.loc[ok], "c": frame.loc[ok, "meta.config_id"].astype(str)})
        m = g.groupby("k").agg(y=("y", "mean"), p=("p", "mean"), c=("c", "first"))
        res = evaluate_predictions(m["y"].to_numpy(), m["p"].to_numpy(), m["c"].to_numpy())
        if res["r2"] is not None:
            out.append(res["r2"])
            if res["r2CiLow"] is not None:
                cis.append((res["r2CiLow"], res["r2CiHigh"]))
    if not out:
        return {"r2": None, "r2CiLow": None, "r2CiHigh": None}
    return {
        "r2": float(np.mean(out)),
        "r2CiLow": float(np.mean([c[0] for c in cis])) if cis else None,
        "r2CiHigh": float(np.mean([c[1] for c in cis])) if cis else None,
    }


def _diagnostics(
    valid: pd.DataFrame,
    target_key: str,
    target_col: str,
    procedure: Mapping[int, pd.Series],
    size_baseline: Mapping[int, pd.Series] | None,
) -> dict[str, Any]:
    """Context for the headline: ceiling, config-mean R^2, subsets, per algorithm, size baseline."""
    y = valid[target_col]
    groups = valid["meta.config_id"].astype(str)
    repeats = sorted(procedure)
    algo = valid["meta.algorithm"]
    head = headline_mask(valid, target_key)
    subsets = {
        "headline": head,
        "core": algo.isin(CORE_ALGORITHMS),
        "randomControl": algo == RANDOM_ALGORITHM,
        "compositeAnchor": algo == COMPOSITE_ANCHOR,
        "allJobs": pd.Series(True, index=valid.index),
    }
    subset_scores = {}
    for name, mask in subsets.items():
        if int(mask.sum()) < 6:
            continue
        subset_scores[name] = {
            "jobs": int(mask.sum()),
            "configs": int(groups[mask].nunique()),
            **summarize_repeats(y, groups, [procedure[r].where(mask) for r in repeats]),
        }
    per_algorithm = []
    for name in sorted(algo.unique()):
        mask = algo == name
        if int(mask.sum()) < 6:
            continue
        sc = summarize_repeats(y, groups, [procedure[r].where(mask) for r in repeats])
        per_algorithm.append(
            {
                "algorithm": str(name),
                "jobs": int(mask.sum()),
                "configs": int(groups[mask].nunique()),
                "observedMean": float(y[mask].mean()),
                "observedSd": float(y[mask].std()),
                "r2": sc["r2"],
                "r2CiLow": sc["r2CiLow"],
                "r2CiHigh": sc["r2CiHigh"],
                "mae": sc["mae"],
                "ceiling": noise_ceiling(valid[mask], target_col)["looReplicateR2"],
            }
        )
    out: dict[str, Any] = {
        "headlineRule": (
            "all jobs (chance-corrected target)"
            if target_key in CHANCE_CORRECTED_TARGETS
            else f"all jobs except {COMPOSITE_ANCHOR} (at chance level on raw targets)"
        ),
        "noiseCeiling": noise_ceiling(valid[head], target_col),
        "configMean": _config_mean_r2(valid, y, [procedure[r].where(head) for r in repeats]),
        "subsets": subset_scores,
        "perAlgorithm": per_algorithm,
        "sizeBaseline": None,
        "footprintGainOverSize": None,
    }
    if size_baseline:
        out["sizeBaseline"] = {
            "features": [c for c in SIZE_BASELINE_FEATURES if c in valid.columns],
            **summarize_repeats(y, groups, [size_baseline[r].where(head) for r in repeats if r in size_baseline]),
        }
        r0 = repeats[0]
        if r0 in size_baseline:
            ok = head & procedure[r0].notna() & size_baseline[r0].notna()
            out["footprintGainOverSize"] = cluster_bootstrap_r2_diff(
                y[ok].to_numpy(dtype=float),
                procedure[r0][ok].to_numpy(dtype=float),
                size_baseline[r0][ok].to_numpy(dtype=float),
                groups[ok].to_numpy(),
            )
    return out


# -------------------------------------------------------------------------- H2


def _h2_protocols(valid: pd.DataFrame) -> list[dict[str, Any]]:
    """Same three H2 protocols as before; the train/test frames per protocol."""
    protocols: list[dict[str, Any]] = []
    for fam_key, fam_algos in FAMILIES.items():
        sub = valid[valid["meta.algorithm"].isin(fam_algos)]
        cfg_sizes = sub.groupby(["meta.algorithm", "meta.config_id"])["b.two_qubit_gates"].median().sort_values()
        if len(cfg_sizes) < 6:
            continue
        cutoff = max(int(math.floor(len(cfg_sizes) * 0.75)), 3)
        train_cfgs = set(cfg_sizes.index[:cutoff])
        keys = list(zip(sub["meta.algorithm"], sub["meta.config_id"]))
        in_train = np.array([k in train_cfgs for k in keys])
        edge = float(cfg_sizes.iloc[cutoff - 1])
        protocols.append(
            {
                "protocol": "scaling_extrapolation",
                "task": f"Scaling · {fam_key.title()} ({'/'.join(fam_algos)})",
                "family": fam_key,
                "trainScope": f"<= {edge:.0f} 2Q gates",
                "testTarget": f"> {edge:.0f} 2Q gates",
                "train": sub[in_train],
                "test": sub[~in_train],
                "minTrain": 10,
                "minTest": 5,
            }
        )
    core = valid[valid["meta.algorithm"].isin(CORE_ALGORITHMS)]
    for algo in CORE_ALGORITHMS:
        test = core[core["meta.algorithm"] == algo]
        protocols.append(
            {
                "protocol": "leave_algorithm_out",
                "task": f"Zero-shot · Core 5 -> {algo}",
                "family": str(test["meta.family"].iloc[0]) if len(test) else "",
                "trainScope": "Remaining 5 core algorithms",
                "testTarget": algo,
                "train": core[core["meta.algorithm"] != algo],
                "test": test,
                "minTrain": 20,
                "minTest": 5,
            }
        )
    shor = valid[valid["meta.algorithm"] == COMPOSITE_ANCHOR]
    protocols.append(
        {
            "protocol": "composite_anchor",
            "task": f"Zero-shot composite · Core 6 -> {COMPOSITE_ANCHOR}",
            "family": "composite",
            "trainScope": "All 6 core paradigm algorithms",
            "testTarget": COMPOSITE_ANCHOR,
            "train": core,
            "test": shor,
            "minTrain": 20,
            "minTest": 4,
        }
    )
    return [p for p in protocols if len(p["train"]) >= p["minTrain"] and len(p["test"]) >= p["minTest"]]


def _h2_one(
    proto: Mapping[str, Any],
    target_key: str,
    target_col: str,
    circuit_pool: list[str],
    random_state: int,
) -> list[dict[str, Any]]:
    """Footprint chosen on the protocol's own training set, then LightGBM.

    For scaling extrapolation, also a hardware-aware variant: the analytical M2
    estimate as a prior plus a footprint model of its residual. Tree models cannot
    predict below the quality range they were trained on; the prior carries the
    exponential decay into larger circuits.
    """
    warnings.simplefilter("ignore")
    train, test = proto["train"], proto["test"]
    models = build_models(random_state=random_state)
    fast = models["LightGBM"]
    fp_cols, _, _ = select_best_footprint(
        train,
        train.iloc[0:0],
        circuit_pool,
        target_col,
        contrib_model=models["XGBoost"],
        ablation_model=fast,
        groups=train["meta.config_id"],
        random_state=random_state,
        **FOOTPRINT_KWARGS,
    )
    if not fp_cols:
        return []
    meta = {k: proto[k] for k in ("protocol", "task", "family", "trainScope", "testTarget")}
    y_tr = train[target_col].to_numpy(dtype=float)
    y_te = test[target_col].to_numpy(dtype=float)
    groups = test["meta.config_id"].to_numpy()
    base_pred = _fit_predict(fast, train[fp_cols], y_tr, test[fp_cols])
    rows = [
        {
            **meta,
            "variant": "footprint",
            "usesCalibration": False,
            "featureSelection": "inside_train",
            "featureCount": len(fp_cols),
            "nTrain": int(len(train)),
            "nTest": int(len(test)),
            **evaluate_predictions(y_te, base_pred, groups),
        }
    ]
    if proto["protocol"] == "scaling_extrapolation" and target_key in M2_PRIOR:
        col, to_target = M2_PRIOR[target_key]
        if col in train.columns:
            prior_tr = to_target(pd.to_numeric(train[col], errors="coerce")).to_numpy(dtype=float)
            prior_te = to_target(pd.to_numeric(test[col], errors="coerce")).to_numpy(dtype=float)
            ok_tr, ok_te = np.isfinite(prior_tr), np.isfinite(prior_te)
            if ok_tr.sum() >= 10 and ok_te.sum() >= 3:
                # The prior on its own, on the rows it covers: shows how much of the
                # rescue is the analytical estimate and how much the footprint adds.
                rows.append(
                    {
                        **meta,
                        "task": meta["task"] + " · M2 prior alone",
                        "variant": "m2_only",
                        "usesCalibration": True,
                        "featureSelection": "none",
                        "priorCoverage": float(ok_te.mean()),
                        "featureCount": 0,
                        "nTrain": 0,
                        "nTest": int(ok_te.sum()),
                        **evaluate_predictions(y_te[ok_te], np.clip(prior_te[ok_te], 0.0, 1.0), groups[ok_te]),
                    }
                )
                est = clone(fast)
                est.fit(train[fp_cols].iloc[ok_tr], y_tr[ok_tr] - prior_tr[ok_tr])
                pred = base_pred.copy()  # rows without a prior (dynamic circuits) keep the footprint model
                pred[ok_te] = np.clip(prior_te[ok_te] + est.predict(test[fp_cols].iloc[ok_te]), 0.0, 1.0)
                rows.append(
                    {
                        **meta,
                        "task": meta["task"] + " · M2 prior + residual",
                        "variant": "m2_residual",
                        "usesCalibration": True,
                        "featureSelection": "inside_train",
                        "priorCoverage": float(ok_te.mean()),
                        "featureCount": len(fp_cols),
                        "nTrain": int(len(train)),
                        "nTest": int(len(test)),
                        "r2OnPriorRows": evaluate_predictions(y_te[ok_te], pred[ok_te])["r2"],
                        **evaluate_predictions(y_te, pred, groups),
                    }
                )
    return rows


# -------------------------------------------------------------------------- H4


H4_LABELS = {
    "random_only": "Random Volumetric Only (RV)",
    "paradigm_only": "Paradigm Algorithms Only (6 Core)",
    "combined": "Combined (RV + 6 Core)",
    "paradigm_matched": "Paradigm Only, size-matched to RV",
    "reverse_paradigm": "Reverse · paradigm-trained, tested on RV",
    "reverse_random_cv": "Reverse · RV-trained, tested on unseen RV",
}
# (a, b, question): paired bootstrap of R2(a) - R2(b) on the same test jobs.
H4_CONTRASTS = (
    ("paradigm_matched", "random_only", "Same training size: do paradigm circuits predict paradigm circuits better than RV circuits do?"),
    ("combined", "paradigm_only", "Do RV circuits add anything once paradigm circuits are in training?"),
    ("combined", "random_only", "Do paradigm circuits add anything once RV circuits are in training?"),
    ("reverse_random_cv", "reverse_paradigm", "Reverse: do RV circuits predict RV circuits better than paradigm circuits do?"),
)


def _h4_kfold(
    valid: pd.DataFrame,
    target_col: str,
    folds: Sequence[dict[str, Any]],
    fold_of: pd.Series,
    random_state: int,
    n_matched_draws: int = 5,
) -> dict[str, Any]:
    """H4 over the repeat-0 folds, in both directions, with paired contrasts.

    Forward: every paradigm configuration is tested once; training is RV only,
    paradigm only, both, or paradigm size-matched to RV. Reverse: every RV
    configuration is tested once; training is paradigm only, or the other RV
    configurations. Each fold uses the footprint selected on its own training data.
    A regime "wins" only if the paired interval of the difference excludes zero.
    """
    warnings.simplefilter("ignore")
    fast = build_models(random_state=random_state)["LightGBM"]
    rng = np.random.default_rng(random_state)
    is_para = valid["meta.algorithm"].isin(CORE_ALGORITHMS)
    is_rand = valid["meta.algorithm"] == RANDOM_ALGORITHM
    rand_all = valid[is_rand]
    forward = ("random_only", "paradigm_only", "combined")
    oof = {k: pd.Series(np.nan, index=valid.index, dtype=float) for k in (*forward, "reverse_paradigm", "reverse_random_cv")}
    matched = [pd.Series(np.nan, index=valid.index, dtype=float) for _ in range(n_matched_draws)]
    n_train: dict[str, list[int]] = {k: [] for k in H4_LABELS}
    y = lambda d: d[target_col].to_numpy(dtype=float)  # noqa: E731
    for k, fold in enumerate(folds):
        cols = fold["footprint"]
        if not cols:
            continue
        in_fold = fold_of == k
        test, para_tr = valid[is_para & in_fold], valid[is_para & ~in_fold]
        rand_te, rand_tr = valid[is_rand & in_fold], valid[is_rand & ~in_fold]
        if len(test) and len(para_tr) >= 10 and len(rand_all) >= 10:
            for key, tr in (
                ("random_only", rand_all),
                ("paradigm_only", para_tr),
                ("combined", pd.concat([para_tr, rand_all])),
            ):
                oof[key].loc[test.index] = _fit_predict(fast, tr[cols], y(tr), test[cols])
                n_train[key].append(len(tr))
            counts = para_tr.groupby("meta.config_id").size()
            for draw in matched:
                picked, total = [], 0
                for cfg in rng.permutation(counts.index.to_numpy()):
                    if total >= len(rand_all):
                        break
                    picked.append(cfg)
                    total += int(counts[cfg])
                sub = para_tr[para_tr["meta.config_id"].isin(picked)]
                draw.loc[test.index] = _fit_predict(fast, sub[cols], y(sub), test[cols])
            n_train["paradigm_matched"].append(len(rand_all))
        if len(rand_te) and len(para_tr) >= 10:
            oof["reverse_paradigm"].loc[rand_te.index] = _fit_predict(fast, para_tr[cols], y(para_tr), rand_te[cols])
            n_train["reverse_paradigm"].append(len(para_tr))
            if len(rand_tr) >= 10:
                oof["reverse_random_cv"].loc[rand_te.index] = _fit_predict(fast, rand_tr[cols], y(rand_tr), rand_te[cols])
                n_train["reverse_random_cv"].append(len(rand_tr))
    oof["paradigm_matched"] = matched[0]

    y_all = valid[target_col]
    groups = valid["meta.config_id"].astype(str)

    def score(pred: pd.Series, by_family: bool) -> dict[str, Any] | None:
        idx = pred.dropna().index
        if len(idx) < 3:
            return None
        res = evaluate_predictions(
            y_all.loc[idx].to_numpy(dtype=float), pred.loc[idx].to_numpy(dtype=float), groups.loc[idx].to_numpy()
        )
        fam: dict[str, Any] = {}
        if by_family:
            for fam_key, fam_algos in FAMILIES.items():
                sub = idx[valid.loc[idx, "meta.algorithm"].isin(fam_algos).to_numpy()]
                if len(sub) >= 3:
                    fam[fam_key] = evaluate_predictions(
                        y_all.loc[sub].to_numpy(dtype=float), pred.loc[sub].to_numpy(dtype=float)
                    )
        return {"nTest": int(len(idx)), **res, "byFamily": fam}

    rows = []
    for key, label in H4_LABELS.items():
        res = score(oof[key], by_family=not key.startswith("reverse"))
        if res is None:
            continue
        if key == "paradigm_matched":  # R2 is the mean over draws, not of an averaged prediction
            per_draw = [s["r2"] for s in (score(d, False) for d in matched) if s and s["r2"] is not None]
            res["r2PerDraw"] = per_draw
            if per_draw:
                res["r2"] = float(np.mean(per_draw))
        rows.append(
            {
                "regime": key,
                "label": label,
                "direction": "reverse" if key.startswith("reverse") else "forward",
                "nTrain": int(np.mean(n_train[key])) if n_train[key] else 0,
                **res,
            }
        )
    contrasts = []
    for a, b, question in H4_CONTRASTS:
        ok = oof[a].notna() & oof[b].notna()
        if int(ok.sum()) < 6:
            continue
        diff = cluster_bootstrap_r2_diff(
            y_all[ok].to_numpy(dtype=float),
            oof[a][ok].to_numpy(dtype=float),
            oof[b][ok].to_numpy(dtype=float),
            groups[ok].to_numpy(),
        )
        if diff:
            verdict = "a_better" if diff["ciLow"] > 0 else ("b_better" if diff["ciHigh"] < 0 else "no_difference_shown")
            contrasts.append({"a": a, "b": b, "question": question, "verdict": verdict, **diff})
    return {"rows": rows, "contrasts": contrasts}


# ---------------------------------------------------------------- temporal drift


def _temporal_drift(
    bundle: DatasetBundle,
    scope_frame: pd.DataFrame,
    target_key: str,
    target_col: str,
    circuit_pool: list[str],
    hw_pool: list[str],
    device_pool: Sequence[str],
    random_state: int,
) -> dict[str, Any] | None:
    """Train on earlier windows, test on the latest ones; all selection on the earlier ones.

    This is where calibration regimes are judged: the test windows are new calibration
    cycles, so a regime cannot score by recognising a window it was trained on.
    """
    is_holdout, periods = split_temporal_and_cv(scope_frame)
    finite = np.isfinite(scope_frame[target_col])
    train = scope_frame.loc[~is_holdout & finite]
    hold = scope_frame.loc[is_holdout & finite & headline_mask(scope_frame, target_key)]
    if len(train) < MIN_TRAIN_ROWS or len(hold) < 10:
        return None
    models = build_models(random_state=random_state)
    fp_cols, _, _ = select_best_footprint(
        train,
        train.iloc[0:0],
        circuit_pool,
        target_col,
        contrib_model=models["XGBoost"],
        ablation_model=models["LightGBM"],
        groups=train["meta.config_id"],
        random_state=random_state,
        **FOOTPRINT_KWARGS,
    )
    hw_cols = _select_hardware_predictors(train, hw_pool, target_col)
    dev_cols = _select_device_predictors(train, device_pool)
    size_cols = [c for c in SIZE_BASELINE_FEATURES if c in train.columns]
    block = _run_h3_hardware_boundary(
        train, hold, target_col, fp_cols, hw_cols, bundle.exec_to_submit_map, models["LightGBM"],
        device_cols=dev_cols,
        extra_sets={"size_baseline": (REGIME_LABELS["size_baseline"], size_cols)},
    )
    seen = set(train["meta.config_id"].astype(str))
    hold_cfgs = set(hold["meta.config_id"].astype(str))
    return {
        "holdoutPeriods": periods,
        "ordering": temporal_ordering(scope_frame, is_holdout),
        "trainJobs": int(len(train)),
        "holdoutJobs": int(len(hold)),
        "holdoutConfigsSeenInTrain": len(hold_cfgs & seen),
        "holdoutConfigs": len(hold_cfgs),
        "trainCalibrationSnapshots": int(train["meta.calibration_snapshot"].nunique()),
        "holdoutCalibrationSnapshots": int(hold["meta.calibration_snapshot"].nunique()),
        **block,
    }


# ------------------------------------------------------------- provider transfer


def provider_transfer(
    bundle: DatasetBundle,
    target_key: str,
    random_state: int = 11,
) -> dict[str, Any]:
    """Leave-one-provider-out (H3 proper): train on every other provider, test on one.

    Footprint selection happens on the training providers only. With a single
    provider in the export there is nothing to test: the result is marked
    ``WAITING FOR DATA`` and the pipeline carries on.
    """
    frame = bundle.frame
    providers = sorted(frame["meta.provider"].astype(str).unique())
    if len(providers) < 2:
        return {"status": WAITING_FOR_DATA, "providers": providers, "rows": []}
    target_col = ALL_TARGETS[target_key][0]
    if target_col not in frame.columns:
        return {"status": WAITING_FOR_DATA, "providers": providers, "rows": []}
    valid = frame[np.isfinite(frame[target_col])]
    models = build_models(random_state=random_state)
    rows = []
    for held in providers:
        train = valid[valid["meta.provider"] != held]
        test = valid[(valid["meta.provider"] == held) & headline_mask(valid, target_key)]
        if len(train) < MIN_TRAIN_ROWS or len(test) < 10:
            continue
        pool = _usable_columns(train, bundle.circuit_features, min_non_null=0.60)
        pool = [c for c in pool if test[c].notna().mean() >= 0.60]
        fp_cols, _, _ = select_best_footprint(
            train,
            train.iloc[0:0],
            pool,
            target_col,
            contrib_model=models["XGBoost"],
            ablation_model=models["LightGBM"],
            groups=train["meta.config_id"],
            random_state=random_state,
            **FOOTPRINT_KWARGS,
        )
        size_cols = [c for c in SIZE_BASELINE_FEATURES if c in train.columns and test[c].notna().any()]
        y_tr, y_te = train[target_col].to_numpy(dtype=float), test[target_col].to_numpy(dtype=float)
        groups = test["meta.config_id"].to_numpy()
        for regime, cols in (("circuit_only", fp_cols), ("size_baseline", size_cols)):
            if not cols:
                continue
            pred = _fit_predict(models["LightGBM"], train[cols], y_tr, test[cols])
            rows.append(
                {
                    "heldOutProvider": held,
                    "trainProviders": sorted(train["meta.provider"].unique().tolist()),
                    "regime": regime,
                    "label": REGIME_LABELS[regime],
                    "featureCount": len(cols),
                    "nTrain": int(len(train)),
                    "nTest": int(len(test)),
                    **evaluate_predictions(y_te, pred, groups),
                }
            )
    return {"status": "ok" if rows else WAITING_FOR_DATA, "providers": providers, "rows": rows}


# ------------------------------------------------------------------------ scope

ALL_REGIMES = (
    "circuit_only",
    "size_baseline",
    "hardware_only",
    "layout_only",
    "mixed_device",
    "mixed_submit",
    "circuit_window",
    "circuit_chip",
    "hurdle",
)


def analyze_scope_kfold(
    bundle: DatasetBundle,
    scope_name: str,
    scope_frame: pd.DataFrame,
    fold_table: pd.DataFrame,
    models_dir: Any = None,
    random_state: int = 11,
    n_jobs: int = -1,
    multi_chip: bool | None = None,
) -> dict[str, Any]:
    """Nested repeated grouped K-fold analysis for one scope (a chip, a provider, or pooled)."""
    repeat_cols = list(fold_table.columns)
    n_splits = int(fold_table.max().max()) + 1
    targets_payload: dict[str, Any] = {}
    skipped: dict[str, str] = {}
    if multi_chip is None:
        multi_chip = scope_frame["meta.backend_name"].nunique() > 1
    scope_frame = scope_frame.copy()
    scope_frame[WINDOW_CODE] = pd.factorize(
        scope_frame["meta.backend_name"].astype(str) + "|" + scope_frame["period"].astype(str)
    )[0].astype(float)
    chip_cols = chip_indicator_columns(scope_frame) if multi_chip else []
    add_chip_indicators(scope_frame, chip_cols)

    for target_key, (target_col, target_label, higher_better) in ALL_TARGETS.items():
        if target_col not in scope_frame.columns or not np.isfinite(scope_frame[target_col]).any():
            skipped[target_key] = f"{WAITING_FOR_DATA}: `{target_col}` is not exported for this scope"
            continue
        valid = scope_frame[np.isfinite(scope_frame[target_col])].copy()
        if len(valid) < MIN_TRAIN_ROWS:
            skipped[target_key] = f"{WAITING_FOR_DATA}: {len(valid)} jobs, need {MIN_TRAIN_ROWS}"
            continue
        print(f"  [{scope_name}] target={target_key} (jobs={len(valid)}, {n_splits}x{len(repeat_cols)} folds)", flush=True)
        circuit_pool = _usable_columns(valid, bundle.circuit_features, min_non_null=0.60)
        hw_pool = _usable_columns(valid, bundle.hardware_submit_features, min_non_null=0.60)
        device_pool = _usable_columns(valid, bundle.device_calibration_features, min_non_null=0.60)
        cfg = valid["meta.config_id"].astype(str)
        head = headline_mask(valid, target_key)
        floor_share = float((valid.loc[head, target_col] <= HURDLE_FLOOR).mean())
        use_hurdle = floor_share >= HURDLE_MIN_SHARE
        extra = [WINDOW_CODE] + chip_cols
        work_cols = sorted(set(circuit_pool + hw_pool + device_pool + extra + [target_col, "meta.config_id"]))
        work = valid[work_cols]

        tasks = []
        for r, rc in enumerate(repeat_cols):
            fold_of = cfg.map(fold_table[rc])
            for k in range(n_splits):
                te_mask = (fold_of == k).to_numpy()
                if te_mask.sum() < 3 or (~te_mask).sum() < MIN_TRAIN_ROWS:
                    continue
                tasks.append((r, k, work.loc[~te_mask], work.loc[te_mask]))
        results = Parallel(n_jobs=n_jobs)(
            delayed(_nested_fold)(tr, te, target_col, circuit_pool, hw_pool, random_state, device_pool, use_hurdle, chip_cols)
            for _, _, tr, te in tasks
        )
        folds_by_repeat: dict[int, list[dict[str, Any]]] = {}
        folds_r0: dict[int, dict[str, Any]] = {}
        for (r, k, _, _), res in zip(tasks, results):
            folds_by_repeat.setdefault(r, []).append(res)
            if r == 0:
                folds_r0[k] = res
        all_folds = [f for fs in folds_by_repeat.values() for f in fs]

        regimes_out: dict[str, Any] = {}
        procedure_preds: dict[str, dict[int, pd.Series]] = {}
        for regime in ALL_REGIMES:
            if any(regime in f["regimes"] for f in all_folds):
                board, proc = _regime_leaderboard(valid, target_col, folds_by_repeat, regime, scored=head)
                regimes_out[regime] = board
                procedure_preds[regime] = proc

        n_folds_total = len(all_folds)
        fp_freq = Counter(c for f in all_folds for c in f["footprint"])
        hw_freq = Counter(c for f in all_folds for c in f["hardware"])
        fp_sizes = [len(f["footprint"]) for f in all_folds]
        stable = sorted(
            (
                {"feature": c, "selectionFrequency": n / max(n_folds_total, 1)}
                for c, n in fp_freq.items()
                if n / max(n_folds_total, 1) >= STABLE_SELECTION_FREQUENCY
            ),
            key=lambda row: (-row["selectionFrequency"], row["feature"]),
        )

        # ---- final deployed models: same procedure on 100% of the scope
        models = build_models(random_state=random_state)
        fp_full, fp_items, ablation = select_best_footprint(
            valid,
            valid.iloc[0:0],
            circuit_pool,
            target_col,
            contrib_model=models["XGBoost"],
            ablation_model=models["LightGBM"],
            groups=valid["meta.config_id"],
            random_state=random_state,
            **FOOTPRINT_KWARGS,
        )
        hw_full = _select_hardware_predictors(valid, hw_pool, target_col)
        dev_full = _select_device_predictors(valid, device_pool)
        for item in fp_items:
            item["selectionFrequency"] = fp_freq.get(item["feature"], 0) / max(n_folds_total, 1)
            item["stable"] = bool(item["selectionFrequency"] >= STABLE_SELECTION_FREQUENCY)
        saved_models: dict[str, Any] = {}
        deployed_names: dict[str, str] = {}
        for regime, cols in (
            ("circuit_only", fp_full),
            ("mixed_submit", fp_full + hw_full),
            ("circuit_chip", fp_full + chip_cols if chip_cols else []),
        ):
            if not cols or regime not in regimes_out:
                continue
            fit = _fit_regime(valid, None, cols, target_col, True, random_state)
            name = fit["selected"]
            if name is None:
                continue
            deployed_names[regime] = name
            pipe = clone(models[name]).set_params(**fit["perModel"][name]["params"])
            score = next((row for row in regimes_out[regime] if row["model"] == "QAQS (nested selection)"), None)
            best_row = {
                "model": name,
                "label": MODEL_LABELS.get(name, name),
                "cv": score["cv"] if score else evaluate_predictions(np.array([]), np.array([])),
                "holdout": None,
            }
            if models_dir is not None:
                info = _save_regime_model(
                    models_dir, scope_name, target_key, target_col, regime, best_row, pipe, valid, cols,
                    train_rows=len(valid),
                )
                info["params"] = fit["perModel"][name]["params"]
                info["evaluation"] = "nested repeated grouped K-fold (procedure score)"
                saved_models[regime] = info

        # ---- analytical baselines (no training), same scored jobs as the headline
        baselines = []
        for b_name, series in baseline_predictions(valid, target_key).items():
            baselines.append(
                {
                    "model": b_name,
                    "label": b_name,
                    "kind": "analytical_baseline",
                    "cv": evaluate_predictions(
                        valid.loc[head, target_col].to_numpy(dtype=float),
                        series[head].to_numpy(dtype=float),
                        cfg[head].to_numpy(),
                    ),
                    "holdout": None,
                }
            )

        # ---- scatter: repeat-0 out-of-fold predictions of the circuit-only procedure
        points: list[dict[str, Any]] = []
        if "circuit_only" in procedure_preds and 0 in procedure_preds["circuit_only"]:
            p0 = procedure_preds["circuit_only"][0]
            ok = p0.notna().to_numpy()
            points = _aggregate_scatter_points(
                valid.loc[ok], valid.loc[ok, target_col].to_numpy(dtype=float), p0[ok].to_numpy(dtype=float), "cv"
            )

        diagnostics = (
            _diagnostics(valid, target_key, target_col, procedure_preds["circuit_only"], procedure_preds.get("size_baseline"))
            if "circuit_only" in procedure_preds
            else {}
        )
        diagnostics["floorShare"] = floor_share
        diagnostics["hurdleEvaluated"] = bool(use_hurdle)

        # ---- H2 (selection inside each protocol's training set)
        protocols = _h2_protocols(valid)
        h2_nested = Parallel(n_jobs=n_jobs)(
            delayed(_h2_one)(p, target_key, target_col, circuit_pool, random_state) for p in protocols
        )
        h2_rows = [row for rows in h2_nested for row in rows]

        # ---- H3 regimes from the K-fold + calibration-cycle block per chip
        h3_regimes = []
        for regime in ALL_REGIMES:
            board = regimes_out.get(regime)
            if board:
                h3_regimes.append(
                    {
                        "regime": regime,
                        "label": REGIME_LABELS[regime],
                        "featureCount": int(np.mean([f["regimes"][regime].get("nFeatures", 0) for f in all_folds if regime in f["regimes"]])),
                        "cv": board[0]["cv"],
                        "holdout": None,
                    }
                )
        temporal = None
        if not multi_chip:
            temporal = _temporal_drift(
                bundle, valid, target_key, target_col, circuit_pool, hw_pool, device_pool, random_state
            )

        # ---- H4 over repeat-0 folds
        fold_of_r0 = cfg.map(fold_table[repeat_cols[0]])
        h4 = _h4_kfold(
            valid, target_col, [folds_r0.get(k, {"footprint": []}) for k in range(n_splits)], fold_of_r0, random_state
        )

        leaderboard = regimes_out.get("circuit_only", [])
        targets_payload[target_key] = {
            "key": target_key,
            "column": target_col,
            "label": target_label,
            "higherBetter": higher_better,
            "r2Threshold": H1_R2_THRESHOLD,
            "chanceCorrected": target_key in CHANCE_CORRECTED_TARGETS,
            "scoredJobs": int(head.sum()),
            "bestModel": deployed_names.get("circuit_only", ""),
            # Role of each saved circuit-only model. Per-chip models are the best choice
            # on a chip with training data; the pooled model predicts a chip without
            # any; pooled + chip id is a candidate to re-evaluate when new data arrives.
            "modelRoles": (
                {"circuit_only": "unseen_chip_fallback", "circuit_chip": "candidate"}
                if multi_chip
                else {"circuit_only": "best"}
            ),
            "chipLeaderboard": regimes_out.get("circuit_chip", []),
            "footprintCount": len(fp_full),
            "candidateFootprintCount": len(fp_items),
            "hardwareFeatureCount": len(hw_full),
            "selectedFootprintFeatures": fp_full,
            "selectedHardwareFeatures": hw_full,
            "selectedDeviceFeatures": dev_full,
            "stableFootprintFeatures": stable,
            "footprintAblation": ablation,
            "footprintSizeAcrossFolds": {
                "min": int(min(fp_sizes)) if fp_sizes else 0,
                "median": float(np.median(fp_sizes)) if fp_sizes else 0.0,
                "max": int(max(fp_sizes)) if fp_sizes else 0,
            },
            "hardwareSelectionFrequency": {c: n / max(n_folds_total, 1) for c, n in hw_freq.most_common()},
            "foldCount": n_folds_total,
            "savedModels": saved_models,
            "leaderboard": leaderboard,
            "circuitLeaderboard": leaderboard,
            "mixedLeaderboard": regimes_out.get("mixed_submit", []),
            "baselines": baselines,
            "points": points,
            "footprint": fp_items,
            "diagnostics": diagnostics,
            "h2": h2_rows,
            "h3": {
                "regimes": h3_regimes,
                "drift": (temporal or {}).get("drift", {"available": False, "rows": []}),
                "temporal": temporal,
                "transferMatrix": [],
                "providerTransfer": {"status": WAITING_FOR_DATA, "rows": []},
            },
            "h4": h4["rows"],
            "h4Contrasts": h4["contrasts"],
        }

    providers = sorted(scope_frame["meta.provider"].unique().tolist())
    if multi_chip:
        prov, modality = (providers[0] if len(providers) == 1 else "multi"), (
            "mixed" if scope_frame["meta.modality"].nunique() > 1 else str(scope_frame["meta.modality"].iloc[0])
        )
    else:
        prov, modality = infer_provider(scope_name, providers[0] if providers else None)
    return _clean_json(
        {
            "schemaVersion": SCHEMA_VERSION,
            "backend": scope_name,
            "provider": prov,
            "modality": modality,
            "manifestHash": bundle.manifest_hash,
            "inputs": bundle.inputs,
            "jobs": int(len(scope_frame)),
            "trainJobs": int(len(scope_frame)),
            "holdoutJobs": 0,
            "holdoutPeriods": [],
            "split": {
                "mode": "kfold",
                "nSplits": n_splits,
                "nRepeats": len(repeat_cols),
                "totalConfigs": int(scope_frame["meta.config_id"].nunique()),
            },
            "temporalOrdering": {"available": False},
            "algorithms": sorted(scope_frame["meta.algorithm"].unique().tolist()),
            "backendsIncluded": sorted(scope_frame["meta.backend_name"].unique().tolist()),
            "providersIncluded": providers,
            "skippedTargets": skipped,
            "targets": targets_payload,
        }
    )
