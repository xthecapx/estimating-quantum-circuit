"""Phase 7 & 8 QAQS ML estimation pipeline, H1-H4 validation, and dashboard exporter."""

from __future__ import annotations

import argparse
import json
import math
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from scipy.stats import spearmanr
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor

from experiments.footprint_analysis import (
    curate_footprint_vif,
    select_best_footprint,
)
from experiments.ml_dataset import (
    COMPOSITE_ANCHOR,
    CORE_ALGORITHMS,
    FAMILIES,
    RANDOM_ALGORITHM,
    TARGETS,
    DatasetBundle,
    baseline_predictions,
    infer_provider,
    load_ml_dataset,
    make_exec_feature_frame,
    split_by_config,
    split_temporal_and_cv,
    temporal_ordering,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLES = ROOT / "experiments" / "dataset_out"
DEFAULT_REPORT_OUT = ROOT / "report" / "ml_estimation"
DEFAULT_DASHBOARD_OUT = ROOT / "dashboard" / "experiments" / "estimation"
SCHEMA_VERSION = 1
H1_R2_THRESHOLD = 0.80


def build_models(random_state: int = 11) -> dict[str, Pipeline]:
    """Return the 7 thesis regression models plus an AutoML stacking ensemble."""
    xgb = XGBRegressor(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.07,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=random_state,
        n_jobs=1,
        verbosity=0,
    )
    lgbm = LGBMRegressor(
        n_estimators=120,
        max_depth=6,
        num_leaves=31,
        learning_rate=0.07,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=random_state,
        n_jobs=1,
        verbose=-1,
    )
    rf = RandomForestRegressor(
        n_estimators=120,
        max_depth=12,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=1,
    )
    svr = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("svr", SVR(C=2.0, epsilon=0.03, kernel="rbf")),
        ]
    )
    stacker = StackingRegressor(
        estimators=[
            ("xgb", clone(xgb)),
            ("lgbm", clone(lgbm)),
            (
                "rf",
                RandomForestRegressor(
                    n_estimators=60,
                    max_depth=12,
                    min_samples_leaf=2,
                    random_state=random_state,
                    n_jobs=1,
                ),
            ),
            ("svr", clone(svr)),
        ],
        final_estimator=RidgeCV(),
        cv=3,
        n_jobs=1,
    )
    return {
        "LR": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0, random_state=random_state)),
            ]
        ),
        "DTR": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                (
                    "model",
                    DecisionTreeRegressor(
                        max_depth=6, min_samples_leaf=5, random_state=random_state
                    ),
                ),
            ]
        ),
        "RF": Pipeline(
            [("imputer", SimpleImputer(strategy="median", keep_empty_features=True)), ("model", rf)]
        ),
        "KNN": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scaler", StandardScaler()),
                ("model", KNeighborsRegressor(n_neighbors=7, weights="distance")),
            ]
        ),
        "SVR": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scaler", StandardScaler()),
                ("model", SVR(C=2.0, epsilon=0.03, kernel="rbf")),
            ]
        ),
        "XGBoost": Pipeline(
            [("imputer", SimpleImputer(strategy="median", keep_empty_features=True)), ("model", xgb)]
        ),
        "LightGBM": Pipeline(
            [("imputer", SimpleImputer(strategy="median", keep_empty_features=True)), ("model", lgbm)]
        ),
        "Stacking (AutoML)": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("model", stacker),
            ]
        ),
    }


MODEL_LABELS: dict[str, str] = {
    "LR": "Linear Regression (Ridge)",
    "DTR": "Decision Tree (DTR)",
    "RF": "Random Forest (RF)",
    "KNN": "K-Nearest Neighbors (KNN)",
    "SVR": "Support Vector Regression (SVR)",
    "XGBoost": "XGBoost",
    "LightGBM": "LightGBM",
    "Stacking (AutoML)": "Stacking Ensemble (AutoML)",
}


def _clean_json(value: Any) -> Any:
    """Recursively convert numpy scalars and replace non-finite floats with None."""
    if isinstance(value, dict):
        return {str(k): _clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json(v) for v in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        f = float(value)
        return f if math.isfinite(f) else None
    return value


def _fit_predict(model: Pipeline, X_train: pd.DataFrame, y_train: np.ndarray, X_test: pd.DataFrame) -> np.ndarray:
    """Fit pipeline on finite training labels and return [0, 1]-clipped predictions."""
    est = clone(model)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        est.fit(X_train, y_train)
        preds = est.predict(X_test)
    return np.clip(np.asarray(preds, dtype=float), 0.0, 1.0)


def _cluster_bootstrap_r2(
    y: np.ndarray,
    pred: np.ndarray,
    groups: Sequence[Any],
    n_boot: int = 300,
    seed: int = 11,
) -> tuple[float, float] | None:
    """95% percentile CI of R^2, resampling whole circuit configurations.

    Repetitions of one configuration are not independent samples, so jobs are
    resampled by ``meta.config_id`` cluster rather than individually.
    """
    codes, _ = pd.factorize(pd.Series(list(groups)))
    n_groups = int(codes.max()) + 1 if len(codes) else 0
    if n_groups < 5:
        return None
    members = [np.flatnonzero(codes == g) for g in range(n_groups)]
    rng = np.random.default_rng(seed)
    scores: list[float] = []
    for _ in range(n_boot):
        pick = rng.integers(0, n_groups, size=n_groups)
        idx = np.concatenate([members[g] for g in pick])
        yt = y[idx]
        if np.std(yt) <= 1e-12:
            continue
        scores.append(float(r2_score(yt, pred[idx])))
    if len(scores) < 20:
        return None
    lo, hi = np.percentile(scores, [2.5, 97.5])
    return float(lo), float(hi)


def h1_verdict(r2: float | None, ci: tuple[float, float] | None) -> str:
    """`pass` only if the whole CI clears the threshold; `fail` if it is entirely below."""
    if r2 is None:
        return "inconclusive"
    if ci is None:
        return "pass" if r2 >= H1_R2_THRESHOLD else "fail"
    if ci[0] >= H1_R2_THRESHOLD:
        return "pass"
    if ci[1] < H1_R2_THRESHOLD:
        return "fail"
    return "inconclusive"


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    groups: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Compute R^2, MAE, RMSE, Spearman rho, H1 flag and (with ``groups``) a cluster CI."""
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    n = int(mask.sum())
    if n < 3:
        return {
            "n": n,
            "r2": None,
            "mae": None,
            "rmse": None,
            "spearmanRho": None,
            "meetsH1": False,
            "r2CiLow": None,
            "r2CiHigh": None,
            "h1Verdict": "inconclusive",
        }
    yt, yp = y_true[mask], y_pred[mask]
    r2 = float(r2_score(yt, yp)) if np.std(yt) > 1e-12 else 0.0
    mae = float(mean_absolute_error(yt, yp))
    rmse = float(math.sqrt(mean_squared_error(yt, yp)))
    if np.std(yt) > 1e-12 and np.std(yp) > 1e-12:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            rho = float(spearmanr(yt, yp).statistic)
    else:
        rho = 0.0
    ci = None
    if groups is not None:
        ci = _cluster_bootstrap_r2(yt, yp, np.asarray(list(groups))[mask])
    r2_ok = r2 if math.isfinite(r2) else None
    return {
        "n": n,
        "r2": r2_ok,
        "mae": mae if math.isfinite(mae) else None,
        "rmse": rmse if math.isfinite(rmse) else None,
        "spearmanRho": rho if math.isfinite(rho) else None,
        "meetsH1": bool(math.isfinite(r2) and r2 >= H1_R2_THRESHOLD),
        "r2CiLow": ci[0] if ci else None,
        "r2CiHigh": ci[1] if ci else None,
        "h1Verdict": h1_verdict(r2_ok, ci),
    }


def _usable_columns(frame: pd.DataFrame, cols: Sequence[str], min_non_null: float = 0.5) -> list[str]:
    """Keep numeric columns with non-trivial variance and coverage on `frame`."""
    out: list[str] = []
    n = max(len(frame), 1)
    for col in cols:
        if col not in frame.columns:
            continue
        series = pd.to_numeric(frame[col], errors="coerce")
        if series.notna().sum() / n < min_non_null:
            continue
        if float(series.std(skipna=True) or 0.0) < 1e-12:
            continue
        out.append(col)
    return out


def _group_cv_predictions(
    model: Pipeline,
    X: pd.DataFrame,
    y: np.ndarray,
    groups: pd.Series,
    max_splits: int = 5,
) -> np.ndarray:
    """Out-of-fold predictions using GroupKFold grouped by circuit configuration."""
    n_groups = int(groups.nunique())
    n_splits = min(max_splits, n_groups)
    preds = np.full(len(X), np.nan, dtype=float)
    if n_splits < 2:
        return _fit_predict(model, X, y, X)
    splitter = GroupKFold(n_splits=n_splits)
    for train_idx, val_idx in splitter.split(X, y, groups=groups):
        preds[val_idx] = _fit_predict(
            model,
            X.iloc[train_idx],
            y[train_idx],
            X.iloc[val_idx],
        )
    return preds


def _aggregate_scatter_points(
    frame: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    split_name: str,
) -> list[dict[str, Any]]:
    """Aggregate observed vs predicted values by (backend, algorithm, config) for plotting."""
    tmp = pd.DataFrame(
        {
            "backend": frame["meta.backend_name"].astype(str).values,
            "provider": frame["meta.provider"].astype(str).values,
            "algorithm": frame["meta.algorithm"].astype(str).values,
            "config": frame["meta.config_id"].astype(str).values,
            "width": pd.to_numeric(frame["a.num_qubits"], errors="coerce").values,
            "twoQubitGates": pd.to_numeric(frame["b.two_qubit_gates"], errors="coerce").values,
            "observed": y_true,
            "predicted": y_pred,
        }
    )
    tmp = tmp[np.isfinite(tmp["observed"]) & np.isfinite(tmp["predicted"])]
    if tmp.empty:
        return []
    grouped = (
        tmp.groupby(["backend", "provider", "algorithm", "config"], as_index=False)
        .agg(
            width=("width", "mean"),
            twoQubitGates=("twoQubitGates", "mean"),
            observed=("observed", "mean"),
            predicted=("predicted", "mean"),
            jobs=("observed", "size"),
        )
    )
    grouped["residual"] = grouped["observed"] - grouped["predicted"]
    grouped["split"] = split_name
    return grouped.to_dict(orient="records")


def _run_h2_scalability(
    train_pool: pd.DataFrame,
    target_col: str,
    features: list[str],
    fast_model: Pipeline,
) -> list[dict[str, Any]]:
    """Evaluate H2 with the circuit footprint only (no calibration features).

    Scaling extrapolation trains on the smaller 75% of configurations and tests on the
    largest 25%; this is also the closest offline analogue of the decay experiment.
    """
    rows: list[dict[str, Any]] = []
    valid = train_pool[np.isfinite(train_pool[target_col])].copy()

    # 1. Within-family scaling extrapolation (train smaller 75% configs -> test top 25% largest 2Q gates)
    for fam_key, fam_algos in FAMILIES.items():
        sub = valid[valid["meta.algorithm"].isin(fam_algos)].copy()
        cfg_sizes = (
            sub.groupby(["meta.algorithm", "meta.config_id"])["b.two_qubit_gates"]
            .median()
            .sort_values()
        )
        if len(cfg_sizes) < 6:
            continue
        cutoff_idx = max(int(math.floor(len(cfg_sizes) * 0.75)), 3)
        train_cfgs = set(cfg_sizes.index[:cutoff_idx])
        test_cfgs = set(cfg_sizes.index[cutoff_idx:])
        cfg_keys = list(zip(sub["meta.algorithm"], sub["meta.config_id"]))
        tr_mask = [k in train_cfgs for k in cfg_keys]
        te_mask = [k in test_cfgs for k in cfg_keys]
        sub_tr, sub_te = sub.iloc[tr_mask], sub.iloc[te_mask]
        if len(sub_tr) < 10 or len(sub_te) < 5:
            continue
        preds = _fit_predict(
            fast_model,
            sub_tr[features],
            sub_tr[target_col].to_numpy(dtype=float),
            sub_te[features],
        )
        metrics = evaluate_predictions(
            sub_te[target_col].to_numpy(dtype=float), preds, sub_te["meta.config_id"].to_numpy()
        )
        rows.append(
            {
                "protocol": "scaling_extrapolation",
                "task": f"Scaling · {fam_key.title()} ({'/'.join(fam_algos)})",
                "family": fam_key,
                "trainScope": f"<= {float(cfg_sizes.iloc[cutoff_idx - 1]):.0f} 2Q gates",
                "testTarget": f"> {float(cfg_sizes.iloc[cutoff_idx - 1]):.0f} 2Q gates",
                "nTrain": int(len(sub_tr)),
                "nTest": int(len(sub_te)),
                **metrics,
            }
        )

    # 2. Leave-one-algorithm-out across core algorithms
    core_sub = valid[valid["meta.algorithm"].isin(CORE_ALGORITHMS)].copy()
    for algo in CORE_ALGORITHMS:
        sub_tr = core_sub[core_sub["meta.algorithm"] != algo]
        sub_te = core_sub[core_sub["meta.algorithm"] == algo]
        if len(sub_tr) < 20 or len(sub_te) < 5:
            continue
        preds = _fit_predict(
            fast_model,
            sub_tr[features],
            sub_tr[target_col].to_numpy(dtype=float),
            sub_te[features],
        )
        metrics = evaluate_predictions(
            sub_te[target_col].to_numpy(dtype=float), preds, sub_te["meta.config_id"].to_numpy()
        )
        rows.append(
            {
                "protocol": "leave_algorithm_out",
                "task": f"Zero-shot · Core 5 -> {algo}",
                "family": str(sub_te["meta.family"].iloc[0]),
                "trainScope": "Remaining 5 core algorithms",
                "testTarget": algo,
                "nTrain": int(len(sub_tr)),
                "nTest": int(len(sub_te)),
                **metrics,
            }
        )

    # 3. Core 6 -> Composite Shor anchor
    shor_sub = valid[valid["meta.algorithm"] == COMPOSITE_ANCHOR]
    if len(core_sub) >= 20 and len(shor_sub) >= 4:
        preds = _fit_predict(
            fast_model,
            core_sub[features],
            core_sub[target_col].to_numpy(dtype=float),
            shor_sub[features],
        )
        metrics = evaluate_predictions(
            shor_sub[target_col].to_numpy(dtype=float), preds, shor_sub["meta.config_id"].to_numpy()
        )
        rows.append(
            {
                "protocol": "composite_anchor",
                "task": f"Zero-shot composite · Core 6 -> {COMPOSITE_ANCHOR}",
                "family": "composite",
                "trainScope": "All 6 core paradigm algorithms",
                "testTarget": COMPOSITE_ANCHOR,
                "nTrain": int(len(core_sub)),
                "nTest": int(len(shor_sub)),
                **metrics,
            }
        )
    return rows


def _run_h3_hardware_boundary(
    train_df: pd.DataFrame,
    holdout_df: pd.DataFrame,
    target_col: str,
    footprint_cols: list[str],
    hw_submit_cols: list[str],
    exec_to_submit: Mapping[str, str],
    fast_model: Pipeline,
) -> dict[str, Any]:
    """Evaluate H3: Circuit-Only vs Hardware-Only vs Mixed (Submit c.* vs Exec d.*) + drift."""
    regimes: list[dict[str, Any]] = []

    y_tr = train_df[target_col].to_numpy(dtype=float)
    y_te = holdout_df[target_col].to_numpy(dtype=float)
    eval_df = holdout_df if len(holdout_df) >= 10 else train_df
    y_eval = y_te if len(holdout_df) >= 10 else y_tr
    split_label = "holdout" if len(holdout_df) >= 10 else "cv"

    mixed_cols = footprint_cols + hw_submit_cols
    feature_sets: list[tuple[str, str, list[str]]] = [
        ("circuit_only", "Circuit Footprint Only (a.* + b.*)", footprint_cols),
        ("hardware_only", "Hardware Calibration Only (c.*)", hw_submit_cols),
        ("mixed_submit", "Mixed · Footprint + Submit Calib (c.*)", mixed_cols),
    ]

    for key, label, cols in feature_sets:
        if not cols:
            continue
        cv_preds = _group_cv_predictions(
            fast_model, train_df[cols], y_tr, train_df["meta.config_id"]
        )
        cv_m = evaluate_predictions(y_tr, cv_preds)
        if split_label == "holdout":
            te_preds = _fit_predict(fast_model, train_df[cols], y_tr, holdout_df[cols])
            te_m = evaluate_predictions(y_te, te_preds, holdout_df["meta.config_id"].to_numpy())
        else:
            te_m = cv_m
        regimes.append(
            {
                "regime": key,
                "label": label,
                "featureCount": len(cols),
                "cv": cv_m,
                "holdout": te_m,
            }
        )

    # Evaluate calibration drift impact using execution-time d.* mapped into c.* columns
    drift_summary: dict[str, Any] = {"available": False, "rows": []}
    aligned_exec_cols = [c for c in mixed_cols if c in footprint_cols or c in exec_to_submit.values()]
    if aligned_exec_cols and exec_to_submit and split_label == "holdout":
        exec_train_X = make_exec_feature_frame(train_df, footprint_cols, exec_to_submit)[aligned_exec_cols]
        exec_test_X = make_exec_feature_frame(holdout_df, footprint_cols, exec_to_submit)[aligned_exec_cols]

        preds_submit = _fit_predict(
            fast_model, train_df[aligned_exec_cols], y_tr, holdout_df[aligned_exec_cols]
        )
        preds_submit_on_exec = _fit_predict(
            fast_model, train_df[aligned_exec_cols], y_tr, exec_test_X
        )
        preds_retrained_exec = _fit_predict(fast_model, exec_train_X, y_tr, exec_test_X)

        regimes.append(
            {
                "regime": "mixed_exec_eval",
                "label": "Mixed · Submit Model Evaluated on Exec Calib (d.*)",
                "featureCount": len(aligned_exec_cols),
                "cv": evaluate_predictions(
                    y_tr,
                    _group_cv_predictions(
                        fast_model, train_df[aligned_exec_cols], y_tr, train_df["meta.config_id"]
                    ),
                ),
                "holdout": evaluate_predictions(y_te, preds_submit_on_exec),
            }
        )
        regimes.append(
            {
                "regime": "mixed_exec",
                "label": "Mixed · Footprint + Exec Calib (d.*)",
                "featureCount": len(aligned_exec_cols),
                "cv": evaluate_predictions(
                    y_tr,
                    _group_cv_predictions(
                        fast_model, exec_train_X, y_tr, train_df["meta.config_id"]
                    ),
                ),
                "holdout": evaluate_predictions(y_te, preds_retrained_exec),
            }
        )

        if "d.changed_since_prepare" in holdout_df.columns:
            changed = holdout_df["d.changed_since_prepare"].astype(bool).values
            drift_rows = []
            for label_str, mask in (
                ("All Holdout Jobs", np.ones(len(holdout_df), dtype=bool)),
                ("Calibration Unchanged", ~changed),
                ("Calibration Changed Before Execution", changed),
            ):
                if mask.sum() < 3:
                    continue
                m_sub = evaluate_predictions(y_te[mask], preds_submit[mask])
                m_exec = evaluate_predictions(y_te[mask], preds_submit_on_exec[mask])
                drift_rows.append(
                    {
                        "subset": label_str,
                        "jobs": int(mask.sum()),
                        "submitR2": m_sub["r2"],
                        "submitMae": m_sub["mae"],
                        "execR2": m_exec["r2"],
                        "execMae": m_exec["mae"],
                        "maeDeltaExecMinusSubmit": (
                            None
                            if m_exec["mae"] is None or m_sub["mae"] is None
                            else float(m_exec["mae"] - m_sub["mae"])
                        ),
                    }
                )
            drift_summary = {"available": bool(drift_rows), "rows": drift_rows}

    return {"regimes": regimes, "drift": drift_summary}


def _run_h4_benchmarking_regimes(
    train_df: pd.DataFrame,
    holdout_df: pd.DataFrame,
    target_col: str,
    features: list[str],
    fast_model: Pipeline,
    n_matched_draws: int = 10,
    random_state: int = 11,
) -> list[dict[str, Any]]:
    """Evaluate H4 on held-out paradigm jobs using the circuit footprint only.

    Regimes: random-only, paradigm-only, combined, and a *size-matched* paradigm-only
    control. The raw regimes differ in training-set size by ~10x, so a higher paradigm
    score alone cannot distinguish "more informative" from "more data". The matched
    control subsamples paradigm configurations to the random-only row count (averaged
    over ``n_matched_draws`` stratified draws) and is the fair comparison for H4.
    """
    eval_src = holdout_df if len(holdout_df[holdout_df["meta.algorithm"].isin(CORE_ALGORITHMS)]) >= 15 else train_df
    test_paradigm = eval_src[
        eval_src["meta.algorithm"].isin(CORE_ALGORITHMS) & np.isfinite(eval_src[target_col])
    ].copy()
    if test_paradigm.empty:
        return []

    tr_valid = train_df[np.isfinite(train_df[target_col])].copy()
    rand_tr = tr_valid[tr_valid["meta.algorithm"] == RANDOM_ALGORITHM]
    para_tr = tr_valid[tr_valid["meta.algorithm"].isin(CORE_ALGORITHMS)]
    comb_tr = tr_valid[tr_valid["meta.algorithm"].isin(CORE_ALGORITHMS + (RANDOM_ALGORITHM,))]

    y_te = test_paradigm[target_col].to_numpy(dtype=float)
    te_groups = test_paradigm["meta.config_id"].to_numpy()

    def _score(preds: np.ndarray, with_ci: bool = True) -> dict[str, Any]:
        overall = evaluate_predictions(y_te, preds, te_groups if with_ci else None)
        by_family: dict[str, Any] = {}
        for fam_key, fam_algos in FAMILIES.items():
            fmask = test_paradigm["meta.algorithm"].isin(fam_algos).values
            if fmask.sum() >= 3:
                by_family[fam_key] = evaluate_predictions(y_te[fmask], preds[fmask])
        return {**overall, "byFamily": by_family}

    out: list[dict[str, Any]] = []
    for key, label, sub_tr in (
        ("random_only", "Random Volumetric Only (RV)", rand_tr),
        ("paradigm_only", "Paradigm Algorithms Only (6 Core)", para_tr),
        ("combined", "Combined (RV + 6 Core)", comb_tr),
    ):
        if len(sub_tr) < 10:
            continue
        preds = _fit_predict(
            fast_model,
            sub_tr[features],
            sub_tr[target_col].to_numpy(dtype=float),
            test_paradigm[features],
        )
        out.append(
            {
                "regime": key,
                "label": label,
                "nTrain": int(len(sub_tr)),
                "nTest": int(len(test_paradigm)),
                **_score(preds),
            }
        )

    n_match = len(rand_tr)
    cfg_ids = para_tr["meta.config_id"].unique()
    if n_match >= 10 and len(para_tr) > n_match and len(cfg_ids) >= 5:
        rng = np.random.default_rng(random_state)
        draw_preds: list[np.ndarray] = []
        for _ in range(n_matched_draws):
            order = rng.permutation(cfg_ids)
            picked: list[Any] = []
            total = 0
            counts = para_tr.groupby("meta.config_id").size()
            for cfg in order:
                if total >= n_match:
                    break
                picked.append(cfg)
                total += int(counts[cfg])
            sub = para_tr[para_tr["meta.config_id"].isin(picked)]
            draw_preds.append(
                _fit_predict(
                    fast_model,
                    sub[features],
                    sub[target_col].to_numpy(dtype=float),
                    test_paradigm[features],
                )
            )
        mean_pred = np.mean(draw_preds, axis=0)
        entry = _score(mean_pred)
        entry["r2PerDraw"] = [
            evaluate_predictions(y_te, p)["r2"] for p in draw_preds
        ]
        out.append(
            {
                "regime": "paradigm_matched",
                "label": f"Paradigm Only, size-matched to RV (~{n_match} rows)",
                "nTrain": int(n_match),
                "nTest": int(len(test_paradigm)),
                **entry,
            }
        )
    return out


def compute_cross_chip_transfer(
    bundle: DatasetBundle,
    target_key: str,
    features_by_backend: Mapping[str, Mapping[str, list[str]]],
    fast_model: Pipeline,
) -> list[dict[str, Any]]:
    """Cross-backend transfer matrix (H3).

    ``features_by_backend[src]`` holds the regime feature lists that were selected on
    ``src``'s own *training* period. A model trained on ``src`` therefore only ever sees
    features chosen without looking at ``dst``. Cells where source and target share a
    provider are flagged ``crossProvider=False``: they measure cross-*chip* transfer and
    cannot, on their own, support the cross-*provider* claim of H3.
    """
    frame = bundle.frame
    target_col = TARGETS[target_key][0]
    valid = frame[np.isfinite(frame[target_col])].copy()
    backends = sorted(b for b in valid["meta.backend_name"].unique() if b in features_by_backend)
    if len(backends) < 2:
        return []

    cells: list[dict[str, Any]] = []
    regime_labels = {
        "circuit_only": "Circuit Footprint Only",
        "hardware_only": "Hardware Calibration Only",
        "mixed_submit": "Mixed (Footprint + Hardware)",
    }

    for src in backends:
        src_df = valid[valid["meta.backend_name"] == src]
        src_prov, _ = infer_provider(src)
        for dst in backends:
            dst_df = valid[valid["meta.backend_name"] == dst]
            dst_prov, _ = infer_provider(dst)
            for reg_key, reg_label in regime_labels.items():
                cols = features_by_backend[src].get(reg_key, [])
                shared_cols = [
                    c
                    for c in cols
                    if c in src_df.columns
                    and c in dst_df.columns
                    and src_df[c].notna().any()
                    and dst_df[c].notna().any()
                ]
                if not shared_cols:
                    continue
                groups = dst_df["meta.config_id"].to_numpy()
                if src == dst:
                    preds = _group_cv_predictions(
                        fast_model,
                        src_df[shared_cols],
                        src_df[target_col].to_numpy(dtype=float),
                        src_df["meta.config_id"],
                    )
                    eval_mode = "within_chip_cv"
                else:
                    preds = _fit_predict(
                        fast_model,
                        src_df[shared_cols],
                        src_df[target_col].to_numpy(dtype=float),
                        dst_df[shared_cols],
                    )
                    eval_mode = "cross_chip_zero_shot"
                metrics = evaluate_predictions(
                    dst_df[target_col].to_numpy(dtype=float), preds, groups
                )
                cells.append(
                    {
                        "sourceBackend": src,
                        "sourceProvider": src_prov,
                        "targetBackend": dst,
                        "targetProvider": dst_prov,
                        "regime": reg_key,
                        "regimeLabel": reg_label,
                        "mode": eval_mode,
                        "crossProvider": src_prov != dst_prov,
                        "nTrain": int(len(src_df)),
                        "nTest": int(len(dst_df)),
                        **metrics,
                    }
                )
    return cells


# `c.*` columns summarise the qubits the circuit was mapped to, and some of them
# describe the circuit itself rather than the device (r=0.998 between c.num_used_qubits
# and logical width). They would turn the "hardware-only" regime into a circuit-size
# model, so they are excluded from every calibration-feature regime.
CIRCUIT_DEPENDENT_HW_COLUMNS = frozenset(
    {"c.num_used_qubits", "c.duration_s", "c.calibration_coverage"}
)
CIRCUIT_DEPENDENT_HW_PREFIXES = ("c.idle_over_t1.",)


def _is_device_only_hw(col: str) -> bool:
    return col not in CIRCUIT_DEPENDENT_HW_COLUMNS and not col.startswith(
        CIRCUIT_DEPENDENT_HW_PREFIXES
    )


def _select_hardware_predictors(
    tr_t: pd.DataFrame,
    hw_pool: Sequence[str],
    target_col: str,
) -> list[str]:
    """Select VIF-screened device-only `.median` calibration predictors (no circuit proxies)."""
    device_pool = [c for c in hw_pool if _is_device_only_hw(c)]
    preferred_hw = [c for c in device_pool if c.endswith(".median")]
    hw_candidates = preferred_hw if len(preferred_hw) >= 3 else device_pool
    if not hw_candidates:
        return []
    hw_submit_cols, _ = curate_footprint_vif(
        tr_t, hw_candidates, target_col, max_vif=10.0, max_features=8
    )
    return hw_submit_cols if hw_submit_cols else hw_candidates[:6]


def _evaluate_leaderboard(
    models: Mapping[str, Pipeline],
    tr_t: pd.DataFrame,
    te_t: pd.DataFrame,
    y_tr: np.ndarray,
    y_te: np.ndarray,
    feature_cols: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Run GroupKFold CV and temporal holdout evaluation for all models on `feature_cols`."""
    cols = list(feature_cols)
    leaderboard: list[dict[str, Any]] = []
    cv_preds_by_model: dict[str, np.ndarray] = {}
    te_preds_by_model: dict[str, np.ndarray] = {}

    cv_groups = tr_t["meta.config_id"].to_numpy()
    te_groups = te_t["meta.config_id"].to_numpy() if not te_t.empty else None
    for model_id, pipe in models.items():
        cv_pred = _group_cv_predictions(pipe, tr_t[cols], y_tr, tr_t["meta.config_id"])
        cv_m = evaluate_predictions(y_tr, cv_pred, cv_groups)
        cv_preds_by_model[model_id] = cv_pred

        if not te_t.empty:
            te_pred = _fit_predict(pipe, tr_t[cols], y_tr, te_t[cols])
            te_m = evaluate_predictions(y_te, te_pred, te_groups)
            te_preds_by_model[model_id] = te_pred
        else:
            te_m = None

        leaderboard.append(
            {
                "model": model_id,
                "label": MODEL_LABELS.get(model_id, model_id),
                "kind": "ml_ensemble" if "Stacking" in model_id else "ml",
                "cv": cv_m,
                "holdout": te_m,
            }
        )

    # Model selection uses ONLY grouped-CV R^2 on the training period. The temporal
    # holdout is never consulted, so its R^2 stays an unbiased estimate for H1.
    leaderboard.sort(
        key=lambda row: row["cv"]["r2"] if row["cv"]["r2"] is not None else -999.0,
        reverse=True,
    )
    return leaderboard, cv_preds_by_model, te_preds_by_model


def _save_regime_model(
    models_dir: Path,
    scope_name: str,
    target_key: str,
    target_col: str,
    regime: str,
    best_row: Mapping[str, Any],
    base_pipeline: Pipeline,
    valid_all: pd.DataFrame,
    features: Sequence[str],
    train_rows: int,
) -> dict[str, Any]:
    """Fit best deployment pipeline on all valid data for `(scope, target, regime)` and save `.joblib`."""
    models_dir.mkdir(parents=True, exist_ok=True)
    cols = list(features)
    deployed = clone(base_pipeline)
    y_all = valid_all[target_col].to_numpy(dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        deployed.fit(valid_all[cols], y_all)

    fname = f"{scope_name}_{target_key}_{regime}.joblib"
    out_path = models_dir / fname
    eval_split = best_row["holdout"] or best_row["cv"]
    bundle_obj = {
        "schema_version": SCHEMA_VERSION,
        "scope": scope_name,
        "target": target_key,
        "target_column": target_col,
        "regime": regime,
        "model_name": best_row["model"],
        "model_label": best_row["label"],
        "features": cols,
        "clip_bounds": [0.0, 1.0],
        "pipeline": deployed,
        "cv_metrics": best_row["cv"],
        "holdout_metrics": best_row["holdout"],
        "train_rows": int(train_rows),
        "total_rows": int(len(valid_all)),
    }
    joblib.dump(bundle_obj, out_path, compress=3)
    size_kb = round(out_path.stat().st_size / 1024.0, 2)
    return {
        "scope": scope_name,
        "target": target_key,
        "regime": regime,
        "model": best_row["model"],
        "label": best_row["label"],
        "path": f"models/{fname}",
        "fileName": fname,
        "featureCount": len(cols),
        "features": cols,
        "sizeKb": size_kb,
        "r2": eval_split.get("r2"),
        "mae": eval_split.get("mae"),
        "rmse": eval_split.get("rmse"),
        "cvR2": best_row["cv"].get("r2"),
        "cvMae": best_row["cv"].get("mae"),
    }


def analyze_scope(
    bundle: DatasetBundle,
    scope_name: str,
    scope_frame: pd.DataFrame,
    holdout_campaigns: Sequence[str] | None,
    transfer_cache: dict[str, list[dict[str, Any]]],
    models_dir: Path | None = None,
    random_state: int = 11,
    holdout_configs: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Run full Phase 6-8 analysis for one chip/scope and return a serializable snapshot."""
    if holdout_configs is not None:
        is_holdout = scope_frame["meta.config_id"].astype(str).isin(set(holdout_configs))
        holdout_periods: list[str] = []
        split_info: dict[str, Any] = {
            "mode": "config",
            "holdoutConfigs": len(set(holdout_configs) & set(scope_frame["meta.config_id"].astype(str))),
            "totalConfigs": int(scope_frame["meta.config_id"].nunique()),
        }
        ordering: dict[str, Any] = {"available": False}
    else:
        is_holdout, holdout_periods = split_temporal_and_cv(scope_frame, holdout_campaigns)
        split_info = {"mode": "temporal"}
        ordering = temporal_ordering(scope_frame, is_holdout)
    train_df = scope_frame.loc[~is_holdout].copy()
    holdout_df = scope_frame.loc[is_holdout].copy()
    if train_df.empty:
        train_df = scope_frame.copy()
        holdout_df = scope_frame.iloc[0:0].copy()

    circuit_pool = _usable_columns(train_df, bundle.circuit_features, min_non_null=0.60)
    hw_pool = _usable_columns(train_df, bundle.hardware_submit_features, min_non_null=0.60)
    models = build_models(random_state=random_state)
    fast_model = models["LightGBM"]

    targets_payload: dict[str, Any] = {}
    for target_key, (target_col, target_label, higher_better) in TARGETS.items():
        tr_t = train_df[np.isfinite(train_df[target_col])].copy()
        te_t = holdout_df[np.isfinite(holdout_df[target_col])].copy()
        valid_all = scope_frame[np.isfinite(scope_frame[target_col])].copy()
        if len(tr_t) < 20:
            continue
        print(f"  [{scope_name}] target={target_key} (train={len(tr_t)}, holdout={len(te_t)})", flush=True)

        # Two-stage pre-runtime predictor selection: VIF screening -> SHAP + Perm rank -> top-k CV ablation
        footprint_cols, footprint_items, ablation_curve = select_best_footprint(
            tr_t,
            te_t,
            circuit_pool,
            target_col,
            contrib_model=models["XGBoost"],
            ablation_model=fast_model,
            groups=tr_t["meta.config_id"],
            max_vif=10.0,
            max_candidates=16,
            min_features=5,
            max_selected=10,
            r2_tolerance=0.0015,
            random_state=random_state,
        )
        hw_submit_cols = _select_hardware_predictors(
            tr_t,
            hw_pool,
            target_col,
        )
        mixed_cols = footprint_cols + hw_submit_cols

        # Phase 7: H1 Leaderboards on Mixed Submit AND Pure Pre-Runtime Footprint
        y_tr = tr_t[target_col].to_numpy(dtype=float)
        y_te = te_t[target_col].to_numpy(dtype=float) if not te_t.empty else np.array([])
        leaderboard, cv_preds_by_model, te_preds_by_model = _evaluate_leaderboard(
            models, tr_t, te_t, y_tr, y_te, mixed_cols
        )
        best_model = leaderboard[0]["model"]

        if hw_submit_cols:
            circuit_leaderboard, _, _ = _evaluate_leaderboard(
                models, tr_t, te_t, y_tr, y_te, footprint_cols
            )
        else:
            circuit_leaderboard = leaderboard

        saved_models: dict[str, Any] = {}
        if models_dir is not None:
            best_circuit_row = circuit_leaderboard[0]
            saved_models["circuit_only"] = _save_regime_model(
                models_dir,
                scope_name,
                target_key,
                target_col,
                "circuit_only",
                best_circuit_row,
                models[best_circuit_row["model"]],
                valid_all,
                footprint_cols,
                train_rows=len(tr_t),
            )
            saved_models["mixed_submit"] = _save_regime_model(
                models_dir,
                scope_name,
                target_key,
                target_col,
                "mixed_submit",
                leaderboard[0],
                models[best_model],
                valid_all,
                mixed_cols,
                train_rows=len(tr_t),
            )

        # Evaluate analytical M1/M2 baselines on the same splits
        baselines: list[dict[str, Any]] = []
        tr_base = baseline_predictions(tr_t, target_key)
        te_base = baseline_predictions(te_t, target_key) if not te_t.empty else {}
        for b_name, tr_series in tr_base.items():
            b_cv = evaluate_predictions(y_tr, tr_series.to_numpy(dtype=float))
            b_te = (
                evaluate_predictions(y_te, te_base[b_name].to_numpy(dtype=float))
                if b_name in te_base
                else None
            )
            baselines.append(
                {
                    "model": b_name,
                    "label": b_name,
                    "kind": "analytical_baseline",
                    "cv": b_cv,
                    "holdout": b_te,
                }
            )

        # Config-level Observed vs Predicted scatter points for best model
        scatter_points = _aggregate_scatter_points(
            tr_t, y_tr, cv_preds_by_model[best_model], "cv"
        )
        if not te_t.empty:
            scatter_points.extend(
                _aggregate_scatter_points(
                    te_t, y_te, te_preds_by_model[best_model], "holdout"
                )
            )

        # Phase 8 Hypotheses H2, H3, H4
        h2_rows = _run_h2_scalability(scope_frame, target_col, footprint_cols, fast_model)
        h3_data = _run_h3_hardware_boundary(
            tr_t,
            te_t,
            target_col,
            footprint_cols,
            hw_submit_cols,
            bundle.exec_to_submit_map,
            fast_model,
        )
        h3_data["transferMatrix"] = []  # filled by run_pipeline once all scopes are fitted
        h4_rows = _run_h4_benchmarking_regimes(
            tr_t, te_t, target_col, footprint_cols, fast_model
        )

        targets_payload[target_key] = {
            "key": target_key,
            "column": target_col,
            "label": target_label,
            "higherBetter": higher_better,
            "r2Threshold": H1_R2_THRESHOLD,
            "bestModel": best_model,
            "footprintCount": len(footprint_cols),
            "candidateFootprintCount": len(footprint_items),
            "hardwareFeatureCount": len(hw_submit_cols),
            "selectedFootprintFeatures": footprint_cols,
            "selectedHardwareFeatures": hw_submit_cols,
            "footprintAblation": ablation_curve,
            "savedModels": saved_models,
            "leaderboard": leaderboard,
            "circuitLeaderboard": circuit_leaderboard,
            "baselines": baselines,
            "points": scatter_points,
            "footprint": footprint_items,
            "h2": h2_rows,
            "h3": h3_data,
            "h4": h4_rows,
        }

    prov, modality = (
        ("multi", "mixed") if scope_name == "pooled" else infer_provider(scope_name)
    )
    return _clean_json(
        {
            "schemaVersion": SCHEMA_VERSION,
            "backend": scope_name,
            "provider": prov,
            "modality": modality,
            "manifestHash": bundle.manifest_hash,
            "inputs": bundle.inputs,
            "jobs": int(len(scope_frame)),
            "trainJobs": int(len(train_df)),
            "holdoutJobs": int(len(holdout_df)),
            "holdoutPeriods": holdout_periods,
            "split": split_info,
            "temporalOrdering": ordering,
            "algorithms": sorted(scope_frame["meta.algorithm"].unique().tolist()),
            "backendsIncluded": sorted(scope_frame["meta.backend_name"].unique().tolist()),
            "providersIncluded": sorted(scope_frame["meta.provider"].unique().tolist()),
            "targets": targets_payload,
        }
    )


def _collect_target_rows(
    scope: str,
    tkey: str,
    tdata: Mapping[str, Any],
    lb_rows: list,
    fp_rows: list,
    ablation_rows: list,
    h2_rows: list,
    h3_rows: list,
    xfer_rows: list,
    h4_rows: list,
    saved_model_rows: list,
    global_stats: Mapping[str, dict[str, Any]],
) -> None:
    """Flatten one K-fold target payload into the report CSV row lists."""
    for ab in tdata.get("footprintAblation", []):
        ablation_rows.append(
            {
                "scope": scope,
                "target": tkey,
                "k": ab["k"],
                "cv_r2": ab["cvR2"],
                "cv_mae": ab["cvMae"],
                "selected": ab["selected"],
                "features": ";".join(ab["features"]),
            }
        )
    for _, minfo in sorted(tdata.get("savedModels", {}).items()):
        saved_model_rows.append(minfo)
    for regime, board in (
        ("circuit_only", tdata.get("leaderboard", [])),
        ("mixed_submit", tdata.get("mixedLeaderboard", [])),
        ("analytical", tdata.get("baselines", [])),
    ):
        for entry in board:
            cv = entry["cv"] or {}
            lb_rows.append(
                {
                    "scope": scope,
                    "target": tkey,
                    "regime": regime,
                    "model": entry["model"],
                    "kind": entry["kind"],
                    "r2": cv.get("r2"),
                    "r2_sd": cv.get("r2Sd"),
                    "r2_ci_low": cv.get("r2CiLow"),
                    "r2_ci_high": cv.get("r2CiHigh"),
                    "mae": cv.get("mae"),
                    "rmse": cv.get("rmse"),
                    "spearman_rho": cv.get("spearmanRho"),
                    "n_repeats": cv.get("nRepeats"),
                    "h1_verdict": cv.get("h1Verdict"),
                    "selection_counts": json.dumps(entry.get("selectionCounts")) if entry.get("selectionCounts") else None,
                }
            )
    for item in tdata.get("footprint", []):
        fp_rows.append({"scope": scope, "target": tkey, **item})
        if item.get("selected"):
            st = global_stats[item["feature"]]
            st["label"] = item["label"]
            st["category"] = item["category"]
            st["selectionCount"] += 1
            st["ranks"].append(int(item.get("rank", 1)))
            st["shaps"].append(float(item["shapMeanAbs"]))
            st["perms"].append(float(item["permutationImportance"]))
            st.setdefault("foldFreq", []).append(float(item.get("selectionFrequency", 0.0)))
    for item in tdata.get("h2", []):
        h2_rows.append({"scope": scope, "target": tkey, **item})
    h3 = tdata.get("h3", {})
    for item in h3.get("regimes", []):
        h3_rows.append(
            {
                "scope": scope,
                "target": tkey,
                "evaluation": "kfold",
                "regime": item["regime"],
                "label": item["label"],
                "r2": item["cv"].get("r2"),
                "r2_sd": item["cv"].get("r2Sd"),
                "mae": item["cv"].get("mae"),
            }
        )
    temporal = h3.get("temporal") or {}
    for item in temporal.get("regimes", []):
        h3_rows.append(
            {
                "scope": scope,
                "target": tkey,
                "evaluation": "temporal_drift",
                "regime": item["regime"],
                "label": item["label"],
                "r2": (item.get("holdout") or {}).get("r2"),
                "r2_ci_low": (item.get("holdout") or {}).get("r2CiLow"),
                "r2_ci_high": (item.get("holdout") or {}).get("r2CiHigh"),
                "mae": (item.get("holdout") or {}).get("mae"),
                "train_cv_r2": item["cv"].get("r2"),
            }
        )
    if scope == "pooled":
        for item in h3.get("transferMatrix", []):
            xfer_rows.append({"target": tkey, **item})
    for item in tdata.get("h4", []):
        h4_rows.append(
            {
                "scope": scope,
                "target": tkey,
                "regime": item["regime"],
                "r2": item["r2"],
                "r2_ci_low": item.get("r2CiLow"),
                "r2_ci_high": item.get("r2CiHigh"),
                "mae": item["mae"],
                "rmse": item["rmse"],
                "nTrain": item["nTrain"],
                "nTest": item["nTest"],
                **{f"{fam}_r2": (m or {}).get("r2") for fam, m in (item.get("byFamily") or {}).items()},
            }
        )


def _fmt(v: Any, nd: int = 3) -> str:
    return "—" if v is None else f"{v:.{nd}f}"


def _hypothesis_sections(snapshots: Mapping[str, dict[str, Any]]) -> list[str]:
    """H2/H3/H4 report sections for the K-fold evaluation (success target as headline)."""
    out: list[str] = []
    key = "success"
    out += [
        "## H2 · Generalization to unseen configurations (success rate)",
        "",
        "Footprint chosen on each protocol's own training set. `M2 prior + residual` adds the analytical "
        "M2 estimate (uses submit-time calibration) as a decay prior and learns its residual from the "
        "footprint; it is calibration-aware, so it is reported separately from the circuit-only claim.",
        "",
        "| Scope | Protocol | Task | nTrain / nTest | R² [95% CI] | MAE |",
        "|---|---|---|---:|---:|---:|",
    ]
    for scope, snap in snapshots.items():
        for row in snap["targets"].get(key, {}).get("h2", []):
            ci = (
                f" [{row['r2CiLow']:.2f}, {row['r2CiHigh']:.2f}]" if row.get("r2CiLow") is not None else ""
            )
            out.append(
                f"| `{scope}` | {row['protocol']} | {row['task']} | {row['nTrain']} / {row['nTest']} "
                f"| {_fmt(row.get('r2'))}{ci} | {_fmt(row.get('mae'), 4)} |"
            )
    out.append("")

    out += [
        "## H3 · Hardware context and drift (success rate)",
        "",
        "K-fold columns: unseen configurations, same calibration windows. Temporal columns: train on "
        "earlier windows, test on the latest window (mostly the same configurations), so they measure drift.",
        "",
        "| Scope | Regime | K-fold R² ± sd | Temporal R² [95% CI] | Temporal MAE |",
        "|---|---|---:|---:|---:|",
    ]
    for scope, snap in snapshots.items():
        t = snap["targets"].get(key)
        if not t:
            continue
        temporal = {r["regime"]: r for r in ((t["h3"].get("temporal") or {}).get("regimes") or [])}
        for reg in t["h3"]["regimes"]:
            tr = temporal.get(reg["regime"], {}).get("holdout") or {}
            ci = f" [{tr['r2CiLow']:.2f}, {tr['r2CiHigh']:.2f}]" if tr.get("r2CiLow") is not None else ""
            out.append(
                f"| `{scope}` | {reg['label']} | {_fmt(reg['cv'].get('r2'))} ± {_fmt(reg['cv'].get('r2Sd'))} "
                f"| {_fmt(tr.get('r2'))}{ci} | {_fmt(tr.get('mae'), 4)} |"
            )
    out.append("")
    out.append(
        "Cross-chip transfer (zero-shot, footprint chosen on the source chip) is in "
        "`h3_cross_chip_transfer.csv`. Both chips are IBM Heron, so it supports cross-*chip* transfer "
        "only; the cross-*provider* claim needs Rigetti/IonQ data."
    )
    out.append("")

    out += [
        "## H4 · Paradigm vs random-volumetric training (success rate)",
        "",
        "Every paradigm configuration predicted once (repeat-0 folds). `size-matched` trains on as many "
        "paradigm rows as random-only has, so training size is not confounded with signal.",
        "",
        "| Scope | Regime | nTrain | R² [95% CI] | MAE |",
        "|---|---|---:|---:|---:|",
    ]
    for scope, snap in snapshots.items():
        for row in snap["targets"].get(key, {}).get("h4", []):
            ci = f" [{row['r2CiLow']:.2f}, {row['r2CiHigh']:.2f}]" if row.get("r2CiLow") is not None else ""
            out.append(
                f"| `{scope}` | {row['label']} | {row['nTrain']} | {_fmt(row.get('r2'))}{ci} | {_fmt(row.get('mae'), 4)} |"
            )
    out.append("")
    return out


def write_reports(snapshots: Mapping[str, dict[str, Any]], report_dir: Path) -> None:
    """Export CSV tables, best pre-runtime predictors JSON, model manifest, and report.md."""
    report_dir.mkdir(parents=True, exist_ok=True)
    models_dir = report_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    lb_rows, fp_rows, ablation_rows = [], [], []
    h2_rows, h3_rows, xfer_rows, h4_rows = [], [], [], []
    saved_model_rows: list[dict[str, Any]] = []
    by_scope_target: dict[str, dict[str, Any]] = {}
    global_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "label": "",
            "category": "",
            "selectionCount": 0,
            "ranks": [],
            "shaps": [],
            "perms": [],
        }
    )
    total_targets = 0

    lines = [
        "# QAQS Quantum Circuit Quality Estimation Report",
        "",
        f"Scopes evaluated: {', '.join(snapshots.keys())}",
        "",
    ]

    kfold_mode = any((snap.get("split") or {}).get("mode") == "kfold" for snap in snapshots.values())
    if kfold_mode:
        any_snap = next(iter(snapshots.values()))
        sp = any_snap["split"]
        lines += [
            f"Evaluation: nested repeated grouped K-fold ({sp['nSplits']} folds x {sp['nRepeats']} repeats) "
            f"over {sp['totalConfigs']} circuit configurations. Every configuration is predicted once per "
            "repeat by a model that never saw it, on any chip. Footprint selection, calibration-feature "
            "selection, tuning and model choice happen inside each training fold.",
            "",
            "**QAQS row** = score of that whole procedure (the honest H1 estimate). "
            "Per-model rows are shown for comparison; choosing the best of them afterwards is optimistic.",
            "",
            "R² = mean over repeats ± sd between repeats. CI = mean of per-repeat 95% cluster-bootstrap "
            "intervals (resampling configurations). H1 PASS needs the CI above 0.80.",
            "",
            "Drift is *not* tested here: every configuration also ran in the training windows. "
            "See the temporal drift section and the external validation run.",
            "",
        ]

    for scope, snap in snapshots.items():
        by_scope_target[scope] = {}
        if kfold_mode:
            lines.append(f"## Scope: `{scope}` ({snap['jobs']} jobs, {snap['split']['totalConfigs']} configurations)")
            lines.append("")
            lines.append(
                "| Target | QAQS circuit-only R² ± sd [95% CI] | MAE | Mixed (+calib) R² | Best single model (R²) "
                "| Deployed model | k* (fold range) | H1 |"
            )
            lines.append("|---|---:|---:|---:|---|---|---|:---:|")
            for tkey, tdata in snap["targets"].items():
                proc = tdata["leaderboard"][0]["cv"] if tdata["leaderboard"] else {}
                mixed = tdata.get("mixedLeaderboard") or []
                mixed_r2 = mixed[0]["cv"].get("r2") if mixed else None
                singles = [r for r in tdata["leaderboard"][1:] if r["cv"].get("r2") is not None]
                best_single = singles[0] if singles else None
                ci = (
                    f" [{proc['r2CiLow']:.2f}, {proc['r2CiHigh']:.2f}]"
                    if proc.get("r2CiLow") is not None
                    else ""
                )
                fs = tdata.get("footprintSizeAcrossFolds", {})
                r2_txt = f"{proc['r2']:.3f} ± {proc.get('r2Sd', 0):.3f}{ci}" if proc.get("r2") is not None else "—"
                mae_txt = f"{proc['mae']:.4f}" if proc.get("mae") is not None else "—"
                mixed_txt = f"{mixed_r2:.3f}" if mixed_r2 is not None else "—"
                single_txt = (
                    f"{best_single['model']} ({best_single['cv']['r2']:.3f})" if best_single else "—"
                )
                lines.append(
                    f"| {tdata['label']} (`{tkey}`) | {r2_txt} | {mae_txt} | {mixed_txt} | {single_txt} "
                    f"| {tdata['bestModel']} | {tdata['footprintCount']} ({fs.get('min', '?')}–{fs.get('max', '?')}) "
                    f"| {proc.get('h1Verdict', 'inconclusive').upper()} |"
                )
                by_scope_target[scope][tkey] = {
                    "circuit_only": tdata.get("selectedFootprintFeatures", []),
                    "hardware_submit": tdata.get("selectedHardwareFeatures", []),
                    "mixed_submit": (
                        tdata.get("selectedFootprintFeatures", []) + tdata.get("selectedHardwareFeatures", [])
                    ),
                    "ablation": tdata.get("footprintAblation", []),
                }
                total_targets += 1
                _collect_target_rows(
                    scope, tkey, tdata, lb_rows, fp_rows, ablation_rows, h2_rows, h3_rows,
                    xfer_rows, h4_rows, saved_model_rows, global_stats,
                )
            lines.append("")
            continue
        lines.append(
            f"## Scope: `{scope}` ({snap['jobs']} jobs: {snap['trainJobs']} train/CV, "
            f"{snap['holdoutJobs']} {'config' if (snap.get('split') or {}).get('mode') == 'config' else 'temporal'} holdout)"
        )
        order = snap.get("temporalOrdering") or {}
        sp = snap.get("split") or {}
        if sp.get("mode") == "config":
            lines.append(
                f"Holdout: {sp['holdoutConfigs']} of {sp['totalConfigs']} circuit configurations "
                "(all repetitions, all windows), stratified by algorithm and size; none seen in training."
            )
        if order.get("available"):
            ok = "yes" if order.get("strict") else (
                f"NO — {order.get('holdoutJobsBeforeTrainEnd')} holdout jobs finished before the last training job"
            )
            lines.append(
                f"Temporal holdout strictly after training: {ok} "
                f"(train ≤ {order['trainEnd'][:16]}, holdout ≥ {order['holdoutStart'][:16]})."
            )
        lines.append("")
        lines.append(
            "| Target | Best Model (by CV) | k* Pre-Runtime / Candidates | Holdout R² [95% CI] | Holdout MAE | Holdout RMSE | CV R² | H1 (>=0.80) |"
        )
        lines.append("|---|---|---|---:|---:|---:|---:|:---:|")

        for tkey, tdata in snap["targets"].items():
            total_targets += 1
            best_row = tdata["leaderboard"][0]
            ho = best_row["holdout"] or {}
            cv = best_row["cv"] or {}
            verdict = (ho or cv).get("h1Verdict", "inconclusive")
            r2_s = f"{ho['r2']:.3f}" if ho.get("r2") is not None else "—"
            if ho.get("r2") is not None and ho.get("r2CiLow") is not None:
                r2_s += f" [{ho['r2CiLow']:.2f}, {ho['r2CiHigh']:.2f}]"
            mae_s = f"{ho['mae']:.4f}" if ho.get("mae") is not None else "—"
            rmse_s = f"{ho['rmse']:.4f}" if ho.get("rmse") is not None else "—"
            cv_r2_s = f"{cv['r2']:.3f}" if cv.get("r2") is not None else "—"
            k_info = f"{tdata['footprintCount']} / {tdata.get('candidateFootprintCount', tdata['footprintCount'])}"
            lines.append(
                f"| {tdata['label']} (`{tkey}`) | {best_row['model']} | {k_info} | {r2_s} | {mae_s} | {rmse_s} | {cv_r2_s} | {verdict.upper()} |"
            )

            by_scope_target[scope][tkey] = {
                "circuit_only": tdata.get("selectedFootprintFeatures", []),
                "hardware_submit": tdata.get("selectedHardwareFeatures", []),
                "mixed_submit": (
                    tdata.get("selectedFootprintFeatures", [])
                    + tdata.get("selectedHardwareFeatures", [])
                ),
                "ablation": tdata.get("footprintAblation", []),
            }

            for ab in tdata.get("footprintAblation", []):
                ablation_rows.append(
                    {
                        "scope": scope,
                        "target": tkey,
                        "k": ab["k"],
                        "cv_r2": ab["cvR2"],
                        "cv_mae": ab["cvMae"],
                        "selected": ab["selected"],
                        "features": ";".join(ab["features"]),
                    }
                )

            for _, minfo in sorted(tdata.get("savedModels", {}).items()):
                saved_model_rows.append(minfo)

            for entry in tdata["leaderboard"] + tdata["baselines"]:
                lb_rows.append(
                    {
                        "scope": scope,
                        "target": tkey,
                        "model": entry["model"],
                        "kind": entry["kind"],
                        "cv_r2": entry["cv"]["r2"],
                        "cv_mae": entry["cv"]["mae"],
                        "cv_rmse": entry["cv"]["rmse"],
                        "holdout_r2": (entry["holdout"] or {}).get("r2"),
                        "holdout_mae": (entry["holdout"] or {}).get("mae"),
                        "holdout_rmse": (entry["holdout"] or {}).get("rmse"),
                        "holdout_r2_ci_low": (entry["holdout"] or {}).get("r2CiLow"),
                        "holdout_r2_ci_high": (entry["holdout"] or {}).get("r2CiHigh"),
                        "meets_h1": (entry["holdout"] or entry["cv"]).get("meetsH1"),
                        "h1_verdict": (entry["holdout"] or entry["cv"]).get("h1Verdict"),
                    }
                )
            for item in tdata["footprint"]:
                fp_rows.append({"scope": scope, "target": tkey, **item})
                if item.get("selected", True):
                    st = global_stats[item["feature"]]
                    st["label"] = item["label"]
                    st["category"] = item["category"]
                    st["selectionCount"] += 1
                    st["ranks"].append(int(item.get("rank", 1)))
                    st["shaps"].append(float(item["shapMeanAbs"]))
                    st["perms"].append(float(item["permutationImportance"]))
            for item in tdata["h2"]:
                h2_rows.append({"scope": scope, "target": tkey, **item})
            for item in tdata["h3"]["regimes"]:
                h3_rows.append(
                    {
                        "scope": scope,
                        "target": tkey,
                        "regime": item["regime"],
                        "label": item["label"],
                        "cv_r2": item["cv"]["r2"],
                        "cv_mae": item["cv"]["mae"],
                        "holdout_r2": (item["holdout"] or {}).get("r2"),
                        "holdout_mae": (item["holdout"] or {}).get("mae"),
                    }
                )
            if scope == "pooled":
                for item in tdata["h3"].get("transferMatrix", []):
                    xfer_rows.append({"target": tkey, **item})
            for item in tdata["h4"]:
                h4_rows.append(
                    {
                        "scope": scope,
                        "target": tkey,
                        "regime": item["regime"],
                        "r2": item["r2"],
                        "mae": item["mae"],
                        "rmse": item["rmse"],
                        "nTrain": item["nTrain"],
                        "nTest": item["nTest"],
                        "r2_ci_low": item.get("r2CiLow"),
                        "r2_ci_high": item.get("r2CiHigh"),
                    }
                )
        lines.append("")

    global_core = []
    denom = max(total_targets, 1)
    for feat, st in global_stats.items():
        global_core.append(
            {
                "feature": feat,
                "label": st["label"],
                "category": st["category"],
                "selectionCount": st["selectionCount"],
                "totalTargets": total_targets,
                "selectionRate": round(st["selectionCount"] / denom, 4),
                "meanRank": round(float(np.mean(st["ranks"])), 2),
                "meanShap": round(float(np.mean(st["shaps"])), 6),
                "meanPermutationImportance": round(float(np.mean(st["perms"])), 6),
                "meanFoldSelectionFrequency": (
                    round(float(np.mean(st["foldFreq"])), 4) if st.get("foldFreq") else None
                ),
            }
        )
    global_core.sort(
        key=lambda r: (r["selectionCount"], r["meanShap"], r["meanPermutationImportance"]),
        reverse=True,
    )

    lines.append("## Selected Best Pre-Runtime Predictors (Global Core Footprint)")
    lines.append("")
    lines.append("| Feature | Category | Selected (Scopes×Targets) | Mean Rank | Mean |SHAP| | Mean Perm ΔR² |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for row in global_core[:15]:
        lines.append(
            f"| `{row['feature']}` | {row['category']} | {row['selectionCount']} / {row['totalTargets']} "
            f"| {row['meanRank']:.1f} | {row['meanShap']:.4f} | {row['meanPermutationImportance']:.4f} |"
        )
    lines.append("")

    lines.append("## Top-k Pre-Runtime Feature Selection Ablation")
    lines.append("")
    lines.append("| Scope | Target | Selected k* (CV R²) | Full Candidates k (CV R²) |")
    lines.append("|---|---|---|---:|")
    for scope, tmap in by_scope_target.items():
        for tkey, info in tmap.items():
            ab = info.get("ablation", [])
            sel_row = next((r for r in ab if r["selected"]), None)
            full_row = ab[-1] if ab else None
            sel_s = (
                f"k={sel_row['k']} ({sel_row['cvR2']:.3f})"
                if sel_row and sel_row["cvR2"] is not None
                else "—"
            )
            full_s = (
                f"k={full_row['k']} ({full_row['cvR2']:.3f})"
                if full_row and full_row["cvR2"] is not None
                else "—"
            )
            lines.append(f"| `{scope}` | `{tkey}` | {sel_s} | {full_s} |")
    lines.append("")

    if kfold_mode:
        lines += _hypothesis_sections(snapshots)

    if saved_model_rows:
        lines.append("## Saved Trained Model Artifacts")
        lines.append("")
        lines.append("| Scope | Target | Regime | Best Model | Features | R² | MAE | Size (KB) | Artifact |")
        lines.append("|---|---|---|---|---:|---:|---:|---:|---|")
        for m in saved_model_rows:
            r2_s = f"{m['r2']:.3f}" if m.get("r2") is not None else "—"
            mae_s = f"{m['mae']:.4f}" if m.get("mae") is not None else "—"
            lines.append(
                f"| `{m['scope']}` | `{m['target']}` | `{m['regime']}` | {m['model']} "
                f"| {m['featureCount']} | {r2_s} | {mae_s} | {m['sizeKb']:.1f} | `{m['path']}` |"
            )
        lines.append("")

    for name, rows in (
        ("leaderboard.csv", lb_rows),
        ("footprint.csv", fp_rows),
        ("footprint_ablation.csv", ablation_rows),
        ("h2_scalability.csv", h2_rows),
        ("h3_hardware_regimes.csv", h3_rows),
        ("h3_cross_chip_transfer.csv", xfer_rows),
        ("h4_benchmarking_regimes.csv", h4_rows),
    ):
        pd.DataFrame(rows).to_csv(report_dir / name, index=False)

    (report_dir / "best_predictors.json").write_text(
        json.dumps(
            _clean_json(
                {
                    "schemaVersion": SCHEMA_VERSION,
                    "globalCorePreRuntimePredictors": global_core,
                    "byScopeTarget": by_scope_target,
                }
            ),
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    (models_dir / "models_manifest.json").write_text(
        json.dumps(
            _clean_json({"schemaVersion": SCHEMA_VERSION, "models": saved_model_rows}),
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    (report_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def run_pipeline(
    tables: Path = DEFAULT_TABLES,
    report_out: Path = DEFAULT_REPORT_OUT,
    dashboard_out: Path = DEFAULT_DASHBOARD_OUT,
    holdout_campaigns: Sequence[str] | None = None,
    backends: Sequence[str] | None = None,
    split_mode: str = "kfold",
    holdout_frac: float = 0.15,
    split_seed: int = 11,
    n_splits: int = 5,
    n_repeats: int = 3,
    n_jobs: int = -1,
) -> dict[str, dict[str, Any]]:
    """Execute full QAQS ML estimation pipeline and write dashboard, model & report artifacts.

    ``split_mode``:
      * ``kfold`` (default): nested repeated grouped K-fold over configurations. Every
        configuration is tested once per repeat; selection and tuning happen inside folds.
      * ``config``: single holdout of ``holdout_frac`` configurations.
      * ``temporal``: hold out the latest campaigns.
    """
    bundle = load_ml_dataset(tables, backends=backends)
    frame = bundle.frame
    detected_backends = sorted(frame["meta.backend_name"].unique().tolist())

    if split_mode == "kfold" and not holdout_campaigns:
        from experiments.qaqs_kfold import analyze_scope_kfold, assign_config_folds

        fold_table = assign_config_folds(frame, n_splits=n_splits, n_repeats=n_repeats, seed=split_seed)
        print(
            f"K-fold: {n_splits} folds x {n_repeats} repeats over "
            f"{len(fold_table)} configurations (seed={split_seed}).",
            flush=True,
        )
        scopes = [(b, frame[frame["meta.backend_name"] == b].copy()) for b in detected_backends]
        if len(detected_backends) > 1:
            scopes.append(("pooled", frame.copy()))
        snapshots = {
            name: analyze_scope_kfold(
                bundle,
                name,
                sub,
                fold_table,
                models_dir=report_out / "models",
                random_state=split_seed,
                n_jobs=n_jobs,
            )
            for name, sub in scopes
        }
        return _finish_pipeline(bundle, snapshots, detected_backends, report_out, dashboard_out)

    holdout_configs: list[str] | None = None
    if split_mode == "config" and not holdout_campaigns:
        _, holdout_configs = split_by_config(frame, holdout_frac, split_seed)
        print(
            f"Config split: {len(holdout_configs)} of {frame['meta.config_id'].nunique()} "
            f"configurations held out (seed={split_seed}).",
            flush=True,
        )

    dashboard_out.mkdir(parents=True, exist_ok=True)
    models_dir = report_out / "models"
    transfer_cache: dict[str, list[dict[str, Any]]] = {}
    snapshots: dict[str, dict[str, Any]] = {}

    for backend in detected_backends:
        sub = frame[frame["meta.backend_name"] == backend].copy()
        snapshots[backend] = analyze_scope(
            bundle,
            backend,
            sub,
            holdout_campaigns,
            transfer_cache,
            models_dir=models_dir,
            holdout_configs=holdout_configs,
        )

    if len(detected_backends) > 1:
        snapshots["pooled"] = analyze_scope(
            bundle,
            "pooled",
            frame.copy(),
            holdout_campaigns,
            transfer_cache,
            models_dir=models_dir,
            holdout_configs=holdout_configs,
        )

    return _finish_pipeline(bundle, snapshots, detected_backends, report_out, dashboard_out)


def _finish_pipeline(
    bundle: DatasetBundle,
    snapshots: dict[str, dict[str, Any]],
    detected_backends: Sequence[str],
    report_out: Path,
    dashboard_out: Path,
) -> dict[str, dict[str, Any]]:
    """Cross-chip transfer matrix, dashboard snapshots and report files."""
    dashboard_out.mkdir(parents=True, exist_ok=True)
    chip_scopes = [b for b in detected_backends if b in snapshots]
    if len(chip_scopes) > 1:
        model_for_transfer = build_models()["LightGBM"]
        for target_key in TARGETS:
            feats = {}
            for chip in chip_scopes:
                tdata = snapshots[chip]["targets"].get(target_key)
                if tdata:
                    fp = tdata["selectedFootprintFeatures"]
                    hw = tdata["selectedHardwareFeatures"]
                    feats[chip] = {"circuit_only": fp, "hardware_only": hw, "mixed_submit": fp + hw}
            matrix = compute_cross_chip_transfer(bundle, target_key, feats, model_for_transfer)
            for scope_payload in snapshots.values():
                if target_key in scope_payload["targets"]:
                    scope_payload["targets"][target_key]["h3"]["transferMatrix"] = _clean_json(matrix)

    for scope, payload in snapshots.items():
        out_path = dashboard_out / f"{scope}.json"
        out_path.write_text(
            json.dumps(payload, separators=(",", ":"), allow_nan=False, sort_keys=True),
            encoding="utf-8",
        )
    print(f"Wrote estimation snapshots for {list(snapshots.keys())}", flush=True)

    write_reports(snapshots, report_out)
    return snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_OUT)
    parser.add_argument("--dashboard-out", type=Path, default=DEFAULT_DASHBOARD_OUT)
    parser.add_argument(
        "--holdout-campaign",
        action="append",
        help="Repeatable campaign ID to hold out as temporal unseen validation set.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        help="Optional backend filter (e.g., ibm_fez, ibm_kingston, ankaa_3, ionq_aria).",
    )
    parser.add_argument(
        "--split",
        choices=("kfold", "config", "temporal"),
        default="kfold",
        help=(
            "kfold: nested repeated grouped K-fold over configurations (default); "
            "config: single 15%% configuration holdout; temporal: hold out later campaigns."
        ),
    )
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=-1, help="Parallel workers for K-fold (-1 = all cores).")
    parser.add_argument("--holdout-frac", type=float, default=0.15)
    parser.add_argument("--split-seed", type=int, default=11)
    args = parser.parse_args()
    snapshots = run_pipeline(
        tables=args.tables,
        report_out=args.report_out,
        dashboard_out=args.dashboard_out,
        holdout_campaigns=args.holdout_campaign,
        backends=args.backend,
        split_mode=args.split,
        holdout_frac=args.holdout_frac,
        split_seed=args.split_seed,
        n_splits=args.folds,
        n_repeats=args.repeats,
        n_jobs=args.jobs,
    )
    for scope, snap in snapshots.items():
        parts = []
        for tkey, tdata in snap["targets"].items():
            row = tdata["leaderboard"][0]
            m = row["holdout"] or row["cv"]
            if m.get("r2") is not None:
                parts.append(f"{tkey}={m['r2']:.3f}")
        print(f"[{scope}] jobs={snap['jobs']} | {row['model'] if snap['targets'] else ''} R2: {', '.join(parts)}")


if __name__ == "__main__":
    main()
