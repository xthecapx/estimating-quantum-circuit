"""Phase 6 Quantum Circuit Footprint curation: Spearman, VIF, Permutation Importance & SHAP."""

from __future__ import annotations

import warnings
from typing import Any, Sequence

import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor

CORE_FOOTPRINT_CATEGORIES: tuple[str, ...] = (
    "ISA Compiled",
    "Logical Complexity",
    "Logical Structural",
    "Logical Behavioral",
    "Logical Element",
    "Quantum Specific",
    "Logical Basic",
)

CUSTOM_LABELS: dict[str, str] = {
    "a.num_qubits": "Logical qubits",
    "a.num_clbits": "Measured bits",
    "a.depth": "Logical depth",
    "a.size": "Logical operations",
    "a.quantum_specific_present": "QuantumSpecific available (<=8q static)",
    "a.quantum_specific.coherence": "Quantum coherence",
    "a.quantum_specific.entanglement_ratio": "Quantum entanglement ratio",
    "a.quantum_specific.magic": "Quantum magic",
    "a.quantum_specific.sensitivity": "Circuit sensitivity",
    "a.quantum_specific.spposq_ratio": "Superposition qubit ratio",
    "b.active_qubits": "Active physical qubits",
    "b.depth": "ISA compiled depth",
    "b.size": "ISA compiled operations",
    "b.two_qubit_depth": "ISA two-qubit depth",
    "b.two_qubit_gates": "ISA two-qubit gates",
    "b.ComplexityMetrics.gate_based_metrics.two_qubit_count": "ISA Complexity 2Q count",
    "b.ComplexityMetrics.entanglement_metrics.entangling_gate_density": "ISA entangling gate density",
    "b.StructuralMetrics.volume": "ISA structural volume",
    "b.BehavioralMetrics.program_communication": "ISA program communication",
}


def feature_category(col: str) -> str:
    """Classify a dataset column into its thesis QWARD / hardware category."""
    if col.startswith(("c.", "d.")):
        return "Hardware Calibration"
    if col.startswith("a.quantum_specific"):
        return "Quantum Specific"
    if col.startswith("b."):
        return "ISA Compiled"
    if "ComplexityMetrics" in col:
        return "Logical Complexity"
    if "StructuralMetrics" in col:
        return "Logical Structural"
    if "BehavioralMetrics" in col:
        return "Logical Behavioral"
    if "ElementMetrics" in col:
        return "Logical Element"
    return "Logical Basic"


def feature_label(col: str) -> str:
    """Return a readable short label for a dataset metric column."""
    if col in CUSTOM_LABELS:
        return CUSTOM_LABELS[col]
    prefix = ""
    if col.startswith("a."):
        prefix = "Logical · "
    elif col.startswith("b."):
        prefix = "ISA · "
    elif col.startswith("c."):
        prefix = "HW Submit · "
    elif col.startswith("d."):
        prefix = "HW Exec · "
    tail = col.split(".")[-2:] if "." in col else [col]
    cleaned = " ".join(part.replace("_", " ") for part in tail if part not in {"mean", "median"})
    if col.endswith((".mean", ".median", ".max", ".min")):
        stat = col.split(".")[-1]
        base = col.split(".")[1].replace("_", " ")
        return f"{prefix}{base} ({stat})"
    return f"{prefix}{cleaned}".strip()


def _safe_spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 5:
        return 0.0, 1.0
    xm, ym = x[mask], y[mask]
    if np.nanstd(xm) < 1e-12 or np.nanstd(ym) < 1e-12:
        return 0.0, 1.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = spearmanr(xm, ym)
    rho = float(res.statistic) if np.isfinite(res.statistic) else 0.0
    pval = float(res.pvalue) if np.isfinite(res.pvalue) else 1.0
    return rho, pval


def compute_spearman_table(
    frame: pd.DataFrame,
    features: Sequence[str],
    target_col: str,
) -> pd.DataFrame:
    """Rank candidate predictors by absolute Spearman correlation with target_col."""
    y = pd.to_numeric(frame[target_col], errors="coerce").to_numpy(dtype=float)
    rows = []
    for col in features:
        if col not in frame.columns:
            continue
        x = pd.to_numeric(frame[col], errors="coerce").to_numpy(dtype=float)
        non_null = np.isfinite(x).sum()
        if non_null < 10 or float(np.nanstd(x)) < 1e-10:
            continue
        rho, pval = _safe_spearman(x, y)
        rows.append(
            {
                "feature": col,
                "label": feature_label(col),
                "category": feature_category(col),
                "spearman_rho": rho,
                "abs_spearman": abs(rho),
                "p_value": pval,
                "non_null": int(non_null),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=["feature", "label", "category", "spearman_rho", "abs_spearman", "p_value", "non_null"]
        )
    return pd.DataFrame(rows).sort_values("abs_spearman", ascending=False).reset_index(drop=True)


def _compute_vif_map(X_scaled: np.ndarray, cols: Sequence[str]) -> dict[str, float]:
    """Compute VIF for each standardized column via correlation matrix inverse with OLS fallback."""
    if len(cols) == 0:
        return {}
    if len(cols) == 1:
        return {cols[0]: 1.0}
    try:
        corr = np.corrcoef(X_scaled, rowvar=False)
        if np.all(np.isfinite(corr)) and np.linalg.cond(corr) < 1e8:
            diag = np.diag(np.linalg.inv(corr))
            return {
                col: (float(val) if np.isfinite(val) and val > 0 else float("inf"))
                for col, val in zip(cols, diag)
            }
    except Exception:
        pass
    exog = np.column_stack([np.ones(X_scaled.shape[0]), X_scaled])
    vifs: dict[str, float] = {}
    for idx, col in enumerate(cols, start=1):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                val = float(variance_inflation_factor(exog, idx))
            vifs[col] = val if np.isfinite(val) else float("inf")
        except Exception:
            vifs[col] = float("inf")
    return vifs


def _prepare_standardized(frame: pd.DataFrame, cols: Sequence[str]) -> np.ndarray:
    imp = SimpleImputer(strategy="median", keep_empty_features=True)
    scaler = StandardScaler()
    arr = frame[list(cols)].to_numpy(dtype=float)
    return scaler.fit_transform(imp.fit_transform(arr))


def curate_footprint_vif(
    train_frame: pd.DataFrame,
    candidate_features: Sequence[str],
    target_col: str,
    max_vif: float = 10.0,
    max_features: int = 16,
    min_non_null_ratio: float = 0.65,
) -> tuple[list[str], pd.DataFrame]:
    """Select a diverse, low-collinearity Quantum Circuit Footprint via Spearman + iterative VIF.

    Returns ``(selected_features, candidate_summary_df)``.
    """
    spearman_df = compute_spearman_table(train_frame, candidate_features, target_col)
    if spearman_df.empty:
        return [], spearman_df

    n_rows = max(len(train_frame), 1)
    eligible = spearman_df[spearman_df["non_null"] / n_rows >= min_non_null_ratio].copy()
    if eligible.empty:
        eligible = spearman_df.copy()

    selected: list[str] = []
    for feat in eligible["feature"].astype(str):
        if len(selected) >= max_features:
            break
        trial = selected + [feat]
        X_trial = _prepare_standardized(train_frame, trial)
        if np.any(np.std(X_trial, axis=0) < 1e-10):
            continue
        # Fast pairwise gate before exact VIF <= max_vif
        if len(trial) > 1:
            corr = np.corrcoef(X_trial, rowvar=False)
            off_diag = np.abs(corr[-1, :-1])
            if np.any(~np.isfinite(off_diag)) or float(np.max(off_diag)) >= 0.985:
                continue
        vifs = _compute_vif_map(X_trial, trial)
        if max(vifs.values()) <= max_vif:
            selected.append(feat)

    if not selected:
        selected = eligible["feature"].astype(str).head(min(5, len(eligible))).tolist()

    final_vifs = _compute_vif_map(_prepare_standardized(train_frame, selected), selected)
    eligible["selected"] = eligible["feature"].isin(selected)
    eligible["vif"] = eligible["feature"].map(final_vifs)
    return selected, eligible.reset_index(drop=True)


def compute_feature_contributions(
    fitted_pipeline: Any,
    X_eval: pd.DataFrame,
    y_eval: pd.Series | np.ndarray,
    feature_names: Sequence[str],
    spearman_df: pd.DataFrame,
    vif_map: dict[str, float],
    random_state: int = 11,
) -> list[dict[str, Any]]:
    """Compute Permutation Importance and SHAP mean(|phi|) on held-out evaluation data."""
    X_df = X_eval[list(feature_names)]
    y_arr = np.asarray(y_eval, dtype=float)
    valid = np.isfinite(y_arr)
    X_df = X_df.loc[valid]
    y_arr = y_arr[valid]

    perm = permutation_importance(
        fitted_pipeline,
        X_df,
        y_arr,
        n_repeats=10,
        random_state=random_state,
        scoring="r2",
        n_jobs=1,
    )
    perm_mean = perm.importances_mean

    # Transform through preprocessing steps inside pipeline before TreeExplainer.
    if hasattr(fitted_pipeline, "steps") and len(fitted_pipeline.steps) > 1:
        X_trans = fitted_pipeline[:-1].transform(X_df)
        estimator = fitted_pipeline[-1]
    else:
        X_trans = X_df.to_numpy(dtype=float)
        estimator = fitted_pipeline

    shap_mean_abs: np.ndarray
    try:
        explainer = shap.TreeExplainer(estimator)
        shap_vals = explainer.shap_values(X_trans)
        shap_arr = np.asarray(shap_vals, dtype=float)
        if shap_arr.ndim == 3:
            shap_arr = shap_arr[0]
        shap_mean_abs = np.mean(np.abs(shap_arr), axis=0)
    except Exception:
        bg = X_trans[: min(50, len(X_trans))]
        explainer = shap.Explainer(estimator.predict, bg)
        shap_vals = explainer(X_trans[: min(150, len(X_trans))]).values
        shap_mean_abs = np.mean(np.abs(np.asarray(shap_vals, dtype=float)), axis=0)

    rho_lookup = {
        str(r.feature): float(r.spearman_rho) for r in spearman_df.itertuples()
    }

    rows: list[dict[str, Any]] = []
    raw_scores: list[float] = []
    for i, feat in enumerate(feature_names):
        shap_v = float(shap_mean_abs[i]) if i < len(shap_mean_abs) and np.isfinite(shap_mean_abs[i]) else 0.0
        perm_v = float(perm_mean[i]) if i < len(perm_mean) and np.isfinite(perm_mean[i]) else 0.0
        vif_v = vif_map.get(feat)
        raw_comp = max(perm_v, 0.0) * 0.5 + shap_v
        raw_scores.append(raw_comp)
        rows.append(
            {
                "feature": feat,
                "label": feature_label(feat),
                "category": feature_category(feat),
                "spearmanRho": rho_lookup.get(feat, 0.0),
                "vif": float(vif_v) if vif_v is not None and np.isfinite(vif_v) else None,
                "permutationImportance": perm_v,
                "shapMeanAbs": shap_v,
                "compositeScore": raw_comp,
                "selected": True,
            }
        )

    max_comp = max(raw_scores, default=0.0)
    if max_comp > 0.0:
        for r in rows:
            r["compositeScore"] = float(r["compositeScore"] / max_comp)
    rows.sort(key=lambda r: r["shapMeanAbs"], reverse=True)
    for idx, r in enumerate(rows, start=1):
        r["rank"] = idx
    return rows


def _oof_feature_contributions(
    contrib_model: Any,
    train_frame: pd.DataFrame,
    target_col: str,
    features: Sequence[str],
    groups: pd.Series,
    spearman_df: pd.DataFrame,
    vif_map: dict[str, float],
    random_state: int = 11,
    max_splits: int = 3,
) -> list[dict[str, Any]]:
    """Compute out-of-fold Permutation Importance and SHAP when no holdout split is provided."""
    n_groups = int(groups.nunique())
    n_splits = min(max_splits, n_groups)
    y_tr = train_frame[target_col].to_numpy(dtype=float)

    if n_splits < 2:
        est = clone(contrib_model)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            est.fit(train_frame[list(features)], y_tr)
        return compute_feature_contributions(
            est,
            train_frame,
            y_tr,
            features,
            spearman_df,
            vif_map,
            random_state=random_state,
        )

    fold_rows: list[dict[str, dict[str, Any]]] = []
    splitter = GroupKFold(n_splits=n_splits)
    for train_idx, val_idx in splitter.split(train_frame[list(features)], y_tr, groups=groups):
        if len(val_idx) < 5:
            continue
        est = clone(contrib_model)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            est.fit(train_frame[list(features)].iloc[train_idx], y_tr[train_idx])
        rows = compute_feature_contributions(
            est,
            train_frame.iloc[val_idx],
            y_tr[val_idx],
            features,
            spearman_df,
            vif_map,
            random_state=random_state,
        )
        fold_rows.append({str(r["feature"]): r for r in rows})

    if not fold_rows:
        est = clone(contrib_model)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            est.fit(train_frame[list(features)], y_tr)
        return compute_feature_contributions(
            est, train_frame, y_tr, features, spearman_df, vif_map, random_state=random_state
        )

    agg_rows: list[dict[str, Any]] = []
    raw_scores: list[float] = []
    for feat in features:
        samples = [f[feat] for f in fold_rows if feat in f]
        template = dict(samples[0])
        perm_v = float(np.mean([s["permutationImportance"] for s in samples]))
        shap_v = float(np.mean([s["shapMeanAbs"] for s in samples]))
        raw_comp = max(perm_v, 0.0) * 0.5 + shap_v
        raw_scores.append(raw_comp)
        template["permutationImportance"] = perm_v
        template["shapMeanAbs"] = shap_v
        template["compositeScore"] = raw_comp
        agg_rows.append(template)

    max_comp = max(raw_scores, default=0.0)
    if max_comp > 0.0:
        for r in agg_rows:
            r["compositeScore"] = float(r["compositeScore"] / max_comp)
    agg_rows.sort(key=lambda r: r["shapMeanAbs"], reverse=True)
    for idx, r in enumerate(agg_rows, start=1):
        r["rank"] = idx
    return agg_rows


def _is_tail_noise(item: dict[str, Any]) -> bool:
    return item["permutationImportance"] <= 0.0 and item["shapMeanAbs"] < 0.005


def _group_cv_r2_mae(
    model: Any,
    X: pd.DataFrame,
    y: np.ndarray,
    groups: pd.Series,
    max_splits: int = 5,
) -> tuple[float | None, float | None]:
    """Compute clipped [0, 1] out-of-fold GroupKFold R^2 and MAE for feature ablation."""
    n_groups = int(groups.nunique())
    n_splits = min(max_splits, n_groups)
    preds = np.full(len(X), np.nan, dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if n_splits < 2:
            est = clone(model)
            est.fit(X, y)
            preds = np.clip(np.asarray(est.predict(X), dtype=float), 0.0, 1.0)
        else:
            splitter = GroupKFold(n_splits=n_splits)
            for train_idx, val_idx in splitter.split(X, y, groups=groups):
                est = clone(model)
                est.fit(X.iloc[train_idx], y[train_idx])
                preds[val_idx] = np.clip(
                    np.asarray(est.predict(X.iloc[val_idx]), dtype=float), 0.0, 1.0
                )
    mask = np.isfinite(y) & np.isfinite(preds)
    if int(mask.sum()) < 3:
        return None, None
    yt, yp = y[mask], preds[mask]
    r2 = float(r2_score(yt, yp)) if np.std(yt) > 1e-12 else 0.0
    mae = float(mean_absolute_error(yt, yp))
    return (r2 if np.isfinite(r2) else None), (mae if np.isfinite(mae) else None)


def select_best_footprint(
    train_frame: pd.DataFrame,
    eval_frame: pd.DataFrame,
    candidate_features: Sequence[str],
    target_col: str,
    contrib_model: Any,
    ablation_model: Any,
    groups: pd.Series,
    max_vif: float = 10.0,
    max_candidates: int = 16,
    min_features: int = 4,
    max_selected: int = 10,
    r2_tolerance: float = 0.0015,
    random_state: int = 11,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    """Two-stage selection of minimal, high-signal pre-runtime Quantum Circuit Footprint.

    Stage 1 screens collinear candidates via Spearman + VIF (<= ``max_vif``), fits
    ``contrib_model`` to compute out-of-sample Permutation Importance and SHAP, and
    ranks candidates by composite predictive contribution.
    Stage 2 runs a GroupKFold CV ablation over top-k subsets and selects the smallest
    parsimonious subset within ``r2_tolerance`` of peak positive-feature CV R^2.

    Returns ``(best_features, ranked_footprint_items, ablation_curve)``.
    """
    vif_candidates, spearman_df = curate_footprint_vif(
        train_frame,
        candidate_features,
        target_col,
        max_vif=max_vif,
        max_features=max_candidates,
    )
    if not vif_candidates:
        return [], [], []

    y_tr = train_frame[target_col].to_numpy(dtype=float)
    vif_map = {
        str(r.feature): float(r.vif)
        for r in spearman_df.itertuples()
        if getattr(r, "selected", False) and pd.notna(r.vif)
    }
    has_distinct_eval = (
        len(eval_frame) >= 15 and not eval_frame.index.equals(train_frame.index)
    )
    if has_distinct_eval:
        fitted_contrib = clone(contrib_model)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fitted_contrib.fit(train_frame[vif_candidates], y_tr)
        footprint_items = compute_feature_contributions(
            fitted_contrib,
            eval_frame,
            eval_frame[target_col],
            vif_candidates,
            spearman_df,
            vif_map,
            random_state=random_state,
        )
    else:
        footprint_items = _oof_feature_contributions(
            contrib_model,
            train_frame,
            target_col,
            vif_candidates,
            groups,
            spearman_df,
            vif_map,
            random_state=random_state,
        )

    # Sort primarily by whether the feature passes noise filtering, then composite signal.
    footprint_items.sort(
        key=lambda r: (
            not _is_tail_noise(r),
            max(r["permutationImportance"], 0.0) * 0.5 + r["shapMeanAbs"],
            r["shapMeanAbs"],
            abs(r["spearmanRho"]),
        ),
        reverse=True,
    )
    ranked_feats = [str(r["feature"]) for r in footprint_items]

    n_avail = len(ranked_feats)
    non_noise_count = sum(1 for r in footprint_items if not _is_tail_noise(r))
    min_eff = min(min_features, max(non_noise_count, 2), n_avail)
    max_useful_k = min(max(non_noise_count, min_eff), n_avail)
    max_k_allowed = min(max_selected, max_useful_k)

    raw_ks = {2, 3, 4, 5, 6, 7, 8, 10, 12, min_eff, max_useful_k, max_k_allowed, n_avail}
    ks = sorted(k for k in raw_ks if 1 <= k <= n_avail)

    ablation_curve: list[dict[str, Any]] = []
    for k in ks:
        feats_k = ranked_feats[:k]
        cv_r2, cv_mae = _group_cv_r2_mae(
            ablation_model,
            train_frame[feats_k],
            y_tr,
            groups,
        )
        ablation_curve.append(
            {
                "k": int(k),
                "cvR2": cv_r2,
                "cvMae": cv_mae,
                "features": feats_k,
                "selected": False,
            }
        )

    eligible_rows = [
        row
        for row in ablation_curve
        if min_eff <= row["k"] <= max_k_allowed and row["cvR2"] is not None
    ]
    if eligible_rows:
        peak_r2 = max(float(row["cvR2"]) for row in eligible_rows)
        best_k = min(
            int(row["k"])
            for row in eligible_rows
            if float(row["cvR2"]) >= peak_r2 - r2_tolerance
        )
    else:
        best_k = min_eff

    for row in ablation_curve:
        row["selected"] = int(row["k"]) == best_k

    best_features = ranked_feats[:best_k]
    final_vifs = _compute_vif_map(_prepare_standardized(train_frame, best_features), best_features)
    best_set = set(best_features)
    for idx, item in enumerate(footprint_items, start=1):
        feat = str(item["feature"])
        is_sel = feat in best_set
        item["rank"] = idx
        item["selected"] = is_sel
        if feat in final_vifs and np.isfinite(final_vifs[feat]):
            item["vif"] = float(final_vifs[feat])

    return best_features, footprint_items, ablation_curve
