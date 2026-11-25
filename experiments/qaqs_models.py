"""QAQS models, metrics and shared evaluation helpers.

Everything here is provider-agnostic: chips, providers and calibration columns are read
from the dataset, never hardcoded.
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from scipy.stats import spearmanr
from sklearn.base import BaseEstimator, RegressorMixin, clone
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

from experiments.footprint_analysis import curate_footprint_vif
from experiments.ml_dataset import (
    ALL_TARGETS,
    DEVICE_CALIBRATION_PREFIX,
    DatasetBundle,
    headline_mask,
    infer_provider,
    make_exec_feature_frame,
)

ROOT = Path(__file__).resolve().parents[1]
# Models frozen on 2026-11-16 together with their pre-registered predictions and scores.
# Never regenerated: the prospective result is only valid for these exact artifacts.
FROZEN_DIR = ROOT / "report" / "frozen_v1"
SCHEMA_VERSION = 2
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


def cluster_bootstrap_r2_diff(
    y: np.ndarray,
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    groups: Sequence[Any],
    n_boot: int = 1000,
    seed: int = 11,
) -> dict[str, Any] | None:
    """Paired cluster bootstrap of ``R2(a) - R2(b)`` on the same jobs.

    Both predictions are scored on identical resamples of configurations, so the
    interval is for the *difference*; two overlapping marginal intervals say nothing
    about it.
    """
    mask = np.isfinite(y) & np.isfinite(pred_a) & np.isfinite(pred_b)
    y, pred_a, pred_b = y[mask], pred_a[mask], pred_b[mask]
    codes, _ = pd.factorize(pd.Series(list(np.asarray(list(groups))[mask])))
    n_groups = int(codes.max()) + 1 if len(codes) else 0
    if n_groups < 5 or np.std(y) <= 1e-12:
        return None
    members = [np.flatnonzero(codes == g) for g in range(n_groups)]
    rng = np.random.default_rng(seed)
    diffs: list[float] = []
    for _ in range(n_boot):
        idx = np.concatenate([members[g] for g in rng.integers(0, n_groups, size=n_groups)])
        yt = y[idx]
        if np.std(yt) <= 1e-12:
            continue
        diffs.append(float(r2_score(yt, pred_a[idx]) - r2_score(yt, pred_b[idx])))
    if len(diffs) < 50:
        return None
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    arr = np.asarray(diffs)
    return {
        "diff": float(r2_score(y, pred_a) - r2_score(y, pred_b)),
        "ciLow": float(lo),
        "ciHigh": float(hi),
        "shareAbove0": float((arr > 0).mean()),
        "nConfigs": n_groups,
    }


class HurdleRegressor(BaseEstimator, RegressorMixin):
    """Two-stage model for a target with a point mass at its floor (DSR clips to 0).

    Stage 1 classifies ``y > floor``; stage 2 regresses ``y`` on the rows above the
    floor. Prediction is ``P(above) * E[y | above]``. With fewer than ``min_floor``
    rows at the floor it reduces to the plain regressor.
    """

    def __init__(self, floor: float = 0.02, min_floor: int = 10, random_state: int = 11):
        self.floor = floor
        self.min_floor = min_floor
        self.random_state = random_state

    def _reg(self) -> LGBMRegressor:
        return LGBMRegressor(
            n_estimators=120, max_depth=6, num_leaves=31, learning_rate=0.07, subsample=0.85,
            colsample_bytree=0.85, random_state=self.random_state, n_jobs=1, verbose=-1,
        )

    def fit(self, X, y):
        y = np.asarray(y, dtype=float)
        above = y > self.floor
        self.two_stage_ = bool((~above).sum() >= self.min_floor and above.sum() >= self.min_floor)
        if self.two_stage_:
            self.clf_ = LGBMClassifier(
                n_estimators=120, max_depth=6, num_leaves=31, learning_rate=0.07,
                random_state=self.random_state, n_jobs=1, verbose=-1,
            ).fit(X, above.astype(int))
            self.reg_ = self._reg().fit(X[above] if isinstance(X, np.ndarray) else X.loc[above], y[above])
        else:
            self.reg_ = self._reg().fit(X, y)
        return self

    def predict(self, X):
        pred = np.asarray(self.reg_.predict(X), dtype=float)
        if self.two_stage_:
            pred = pred * self.clf_.predict_proba(X)[:, 1]
        return pred


def build_hurdle(random_state: int = 11) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("model", HurdleRegressor(random_state=random_state)),
        ]
    )


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


def _run_h3_hardware_boundary(
    train_df: pd.DataFrame,
    holdout_df: pd.DataFrame,
    target_col: str,
    footprint_cols: list[str],
    hw_submit_cols: list[str],
    exec_to_submit: Mapping[str, str],
    fast_model: Pipeline,
    device_cols: Sequence[str] = (),
    extra_sets: Mapping[str, tuple[str, list[str]]] | None = None,
) -> dict[str, Any]:
    """Calibration-cycle regimes: circuit, device calibration, layout calibration, mixed, + drift.

    ``hw_submit_cols`` are layout-aware (``c.*`` over the qubits the circuit uses);
    ``device_cols`` are device-level (``cal.*``, one value per calibration snapshot).
    """
    regimes: list[dict[str, Any]] = []

    y_tr = train_df[target_col].to_numpy(dtype=float)
    y_te = holdout_df[target_col].to_numpy(dtype=float)
    eval_df = holdout_df if len(holdout_df) >= 10 else train_df
    y_eval = y_te if len(holdout_df) >= 10 else y_tr
    split_label = "holdout" if len(holdout_df) >= 10 else "cv"

    mixed_cols = footprint_cols + hw_submit_cols
    device_cols = list(device_cols)
    feature_sets: list[tuple[str, str, list[str]]] = [
        (key, REGIME_LABELS[key], cols)
        for key, cols in (
            ("circuit_only", footprint_cols),
            ("hardware_only", device_cols),
            ("layout_only", hw_submit_cols),
            ("mixed_device", footprint_cols + device_cols),
            ("mixed_submit", mixed_cols),
        )
    ]
    for key, (label, cols) in (extra_sets or {}).items():
        feature_sets.append((key, label, list(cols)))

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
    target_col = ALL_TARGETS[target_key][0]
    if target_col not in frame.columns:
        return []
    valid = frame[np.isfinite(frame[target_col])].copy()
    scored = headline_mask(valid, target_key)
    backends = sorted(b for b in valid["meta.backend_name"].unique() if b in features_by_backend)
    if len(backends) < 2:
        return []

    cells: list[dict[str, Any]] = []
    regime_labels = {
        "circuit_only": "Circuit Footprint Only",
        "hardware_only": "Device Calibration Only",
        "layout_only": "Layout Calibration Only",
        "mixed_submit": "Mixed (Footprint + Layout Calibration)",
    }

    for src in backends:
        src_df = valid[valid["meta.backend_name"] == src]
        src_prov = str(src_df["meta.provider"].iloc[0]) if len(src_df) else infer_provider(src)[0]
        for dst in backends:
            dst_df = valid[(valid["meta.backend_name"] == dst) & (scored if src != dst else True)]
            dst_prov = str(dst_df["meta.provider"].iloc[0]) if len(dst_df) else infer_provider(dst)[0]
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
                keep = scored.loc[dst_df.index].to_numpy()
                metrics = evaluate_predictions(
                    dst_df[target_col].to_numpy(dtype=float)[keep], preds[keep], groups[keep]
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
                        "nTest": int(keep.sum()),
                        **metrics,
                    }
                )
    return cells


# Regime names. `hardware_only` is device-level: it must not be able to see the circuit.
REGIME_LABELS: dict[str, str] = {
    "circuit_only": "Circuit footprint only (a.* + b.*)",
    "hardware_only": "Device calibration only (cal.*, one value per snapshot)",
    "layout_only": "Layout calibration only (c.*, qubits the circuit uses)",
    "mixed_device": "Footprint + device calibration (cal.*)",
    "mixed_submit": "Footprint + layout calibration (c.*)",
    "circuit_window": "Footprint + collection-window id (control)",
    "circuit_chip": "Footprint + chip id",
    "size_baseline": "Size baseline (2Q gates, depth, width, measurements)",
    "hurdle": "Footprint, two-stage (floor / above floor)",
}

# Four plain size counts. A footprint that does not beat them adds nothing over size.
SIZE_BASELINE_FEATURES: tuple[str, ...] = (
    "b.two_qubit_gates",
    "b.depth",
    "a.num_qubits",
    "b.BehavioralMetrics.measurement",
)

# `c.*` columns summarise the qubits the circuit was mapped to, and some of them
# describe the circuit itself rather than the device (r=0.998 between c.num_used_qubits
# and logical width), so they are excluded from every calibration-feature regime. The
# remaining `c.*.median` columns still depend on the layout: they are the *layout*
# regime. The device regime uses `cal.*` (see ``ml_dataset.add_device_calibration``).
CIRCUIT_DEPENDENT_HW_COLUMNS = frozenset(
    {"c.num_used_qubits", "c.duration_s", "c.calibration_coverage"}
)
CIRCUIT_DEPENDENT_HW_PREFIXES = ("c.idle_over_t1.", DEVICE_CALIBRATION_PREFIX + "idle_over_t1")


def _is_device_only_hw(col: str) -> bool:
    return col not in CIRCUIT_DEPENDENT_HW_COLUMNS and not col.startswith(
        CIRCUIT_DEPENDENT_HW_PREFIXES
    )


def _select_hardware_predictors(
    tr_t: pd.DataFrame,
    hw_pool: Sequence[str],
    target_col: str,
) -> list[str]:
    """VIF-screened layout-calibration predictors (`c.*.median`, no circuit proxies)."""
    device_pool = [c for c in hw_pool if _is_device_only_hw(c)]
    preferred_hw = [c for c in device_pool if c.endswith(".median")]
    hw_candidates = preferred_hw if len(preferred_hw) >= 3 else device_pool
    if not hw_candidates:
        return []
    hw_submit_cols, _ = curate_footprint_vif(
        tr_t, hw_candidates, target_col, max_vif=10.0, max_features=8
    )
    return hw_submit_cols if hw_submit_cols else hw_candidates[:6]


def _select_device_predictors(tr_t: pd.DataFrame, device_pool: Sequence[str]) -> list[str]:
    """Device-level calibration predictors: every usable `cal.*` column that varies.

    No target-driven screening: there are few of them and a tree model is indifferent
    to collinearity, so nothing is selected on the labels.
    """
    out = []
    for col in device_pool:
        if col not in tr_t.columns or not _is_device_only_hw(col):
            continue
        series = pd.to_numeric(tr_t[col], errors="coerce")
        if series.notna().mean() >= 0.6 and float(series.std(skipna=True) or 0.0) > 1e-15:
            out.append(col)
    return out


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
    eval_split = best_row.get("holdout") or best_row["cv"]
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
        "holdout_metrics": best_row.get("holdout"),
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
