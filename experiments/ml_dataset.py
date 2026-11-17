"""Provider-agnostic dataset loading and split helpers for QAQS ML estimation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

TARGETS: dict[str, tuple[str, str, bool]] = {
    "dsr": (
        "f.fidelity.dsr",
        "Differential Success Rate",
        True,
    ),
    "hellinger": (
        "f.fidelity.hellinger_fidelity",
        "Hellinger Fidelity",
        True,
    ),
    "tvd": (
        "f.fidelity.tvd",
        "Total Variation Distance",
        False,
    ),
    "success": (
        "f.fidelity.success_rate",
        "Success Rate",
        True,
    ),
}

FAMILIES: dict[str, tuple[str, str]] = {
    "fourier": ("QFT", "PHASE-ESTIMATION"),
    "oracle": ("GROVER", "BERNSTEIN-VAZIRANI"),
    "entanglement": ("VTP", "GHZ"),
}

CORE_ALGORITHMS: tuple[str, ...] = tuple(
    algo for pair in FAMILIES.values() for algo in pair
)
RANDOM_ALGORITHM = "RANDOM-VOLUMETRIC"
COMPOSITE_ANCHOR = "SHOR"

PROVIDER_PREFIXES: tuple[tuple[str, str, str], ...] = (
    ("ibm", "ibm", "superconducting"),
    ("fake", "ibm", "superconducting"),
    ("ankaa", "rigetti", "superconducting"),
    ("rigetti", "rigetti", "superconducting"),
    ("ionq", "ionq", "trapped_ion"),
    ("aria", "ionq", "trapped_ion"),
    ("forte", "ionq", "trapped_ion"),
    ("harmony", "ionq", "trapped_ion"),
)

EXCLUDED_EXACT = {
    "a.available",
    "a.reason",
    "a.dynamic",
    "a.quantum_specific.available",
    "a.quantum_specific.cached",
    "a.quantum_specific.compute_seconds",
    "a.quantum_specific.reason",
    "a.quantum_specific.seed",
    "a.QiskitMetrics.basic_metrics.has_calibrations",
    "a.QiskitMetrics.basic_metrics.has_layout",
    "a.QiskitMetrics.scheduling_metrics.is_scheduled",
    "b.available",
    "b.reason",
    "b.physical_layout",
    "b.QiskitMetrics.basic_metrics.has_calibrations",
    "b.QiskitMetrics.basic_metrics.has_layout",
    "b.QiskitMetrics.scheduling_metrics.is_scheduled",
    "c.available",
    "c.calibrated_at",
    "c.collected_at",
    "c.source",
    "c.scheduled",
    "d.available",
    "d.calibrated_at",
    "d.collected_at",
    "d.source",
    "d.scheduled",
    "d.changed_since_prepare",
    "d.changed_values",
}

EXCLUDED_PREFIXES = (
    "a.QiskitMetrics.basic_metrics.count_ops.",
    "a.QiskitMetrics.instruction_metrics.instructions.",
    "a.QiskitMetrics.scheduling_metrics.",
    "b.count_ops.",
    "b.QiskitMetrics.basic_metrics.count_ops.",
    "b.QiskitMetrics.instruction_metrics.instructions.",
    "b.QiskitMetrics.scheduling_metrics.",
)

# Explicit holdout campaign patterns per backend for reproducible thesis evaluation.
DEFAULT_HOLDOUT_CAMPAIGNS: dict[str, tuple[str, ...]] = {
    # `fez-dataset-v2-pilot-r2` is deliberately NOT held out: it ran on 2026-11-04 01:43Z,
    # before the `fez-dataset-v2` window-1 training data (2026-11-04 13:13Z), so holding
    # it out would break the strictly-later-than-training guarantee of the temporal split.
    "ibm_fez": (
        "fez-full-shor-growth-v1-2026-11-06",
        "fez-oracle-growth-v1-2026-11-07",
        "fez-oracle-growth-v1-2026-11-07-makeup",
        "fez-oracle-growth-v1-2026-11-07-standalone",
    ),
    "ibm_kingston": (
        "kingston-full-oracle-growth-v1-2026-11-11",
    ),
}


# Prospective-validation collections. They are scored against frozen models and must
# never enter training, feature selection or tuning: excluded unless explicitly asked.
VALIDATION_CAMPAIGN_MARKERS: tuple[str, ...] = ("-validation-v",)


def is_validation_campaign(campaign_id: str) -> bool:
    return any(marker in str(campaign_id) for marker in VALIDATION_CAMPAIGN_MARKERS)


@dataclass(frozen=True)
class DatasetBundle:
    """Loaded dataset together with manifest provenance and feature registries."""

    frame: pd.DataFrame
    manifest_hash: str
    inputs: dict[str, str]
    circuit_features: list[str]
    hardware_submit_features: list[str]
    hardware_exec_features: list[str]
    exec_to_submit_map: dict[str, str]


def infer_provider(backend_name: str, explicit_provider: str | None = None) -> tuple[str, str]:
    """Map backend identifiers from IBM, Rigetti, or IonQ to (provider, modality)."""
    if explicit_provider and str(explicit_provider).strip():
        prov = str(explicit_provider).strip().lower()
        modality = "trapped_ion" if prov == "ionq" else "superconducting"
        return prov, modality
    lower = str(backend_name or "").strip().lower()
    for prefix, prov, modality in PROVIDER_PREFIXES:
        if lower.startswith(prefix) or prefix in lower:
            return prov, modality
    return "unknown", "unknown"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_excluded_feature(col: str) -> bool:
    if col in EXCLUDED_EXACT:
        return True
    if any(col.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return True
    if col.endswith((".compute_seconds", ".seed", ".cached", ".available", ".reason")):
        return True
    return False


def _extract_numeric_features(frame: pd.DataFrame, prefix: str) -> list[str]:
    """Return sorted numeric feature names under a group prefix, preserving usable predictors."""
    features: list[str] = []
    for col in sorted(frame.columns):
        if not col.startswith(prefix) or _is_excluded_feature(col):
            continue
        series = pd.to_numeric(frame[col], errors="coerce")
        if series.notna().sum() == 0:
            continue
        frame[col] = series.astype(float)
        features.append(col)
    return features


def _canonicalize_hardware_columns(
    frame: pd.DataFrame, submit_cols: list[str], exec_cols: list[str]
) -> dict[str, str]:
    """Map execution-time `d.*` columns to their submission-time `c.*` counterparts."""
    submit_set = set(submit_cols)
    mapping: dict[str, str] = {}
    for d_col in exec_cols:
        c_col = "c." + d_col[2:]
        if c_col in submit_set:
            mapping[d_col] = c_col
    return mapping


def load_ml_dataset(
    tables: Path,
    backends: Sequence[str] | None = None,
    providers: Sequence[str] | None = None,
    include_validation: bool = False,
) -> DatasetBundle:
    """Load and validate CSV dataset parts against `dataset_manifest.json`.

    Compatible with current IBM exports and future Rigetti / IonQ CSV exports using
    the same schema convention (`meta.*`, `a.*`, `b.*`, `c.*`, `d.*`, `e.*`, `f.*`, `g.*`).

    Prospective-validation campaigns are dropped unless ``include_validation`` is set,
    so the training pipeline can never see them. ``manifest_hash``/``inputs`` still
    describe the full export.
    """
    manifest_path = tables / "dataset_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != "1.0":
            raise ValueError(f"Unsupported dataset manifest schema: {manifest.get('schema_version')}")
        parts = manifest["parts"]
        manifest_hash = _sha256(manifest_path)
    else:
        csv_path = tables / "dataset.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Neither dataset_manifest.json nor dataset.csv found in {tables}")
        parts = [{"file": "dataset.csv"}]
        manifest_hash = _sha256(csv_path)

    frames: list[pd.DataFrame] = []
    inputs: dict[str, str] = {}
    for part in parts:
        part_name = part["file"]
        part_path = tables / part_name
        if "bytes" in part and part_path.stat().st_size != part["bytes"]:
            raise ValueError(f"Dataset part size mismatch: {part_name}")
        if not part_path.name.endswith(".csv") or not re.fullmatch(r"[\w.-]+\.csv", part_path.name):
            raise ValueError(f"Invalid dataset part filename: {part_name}")
        inputs[part_name] = _sha256(part_path)
        df_part = pd.read_csv(part_path, low_memory=False)
        if "rows" in part and len(df_part) != part["rows"]:
            raise ValueError(f"Dataset part row count mismatch: {part_name}")
        frames.append(df_part)

    frame = pd.concat(frames, ignore_index=True).copy()

    # Normalize provider and modality columns even for datasets exported before multi-provider metadata.
    explicit_prov = (
        frame["meta.provider"] if "meta.provider" in frame.columns else [None] * len(frame)
    )
    inferred = [
        infer_provider(b, p)
        for b, p in zip(frame["meta.backend_name"].astype(str), explicit_prov)
    ]
    frame["meta.provider"] = [pair[0] for pair in inferred]
    frame["meta.modality"] = [pair[1] for pair in inferred]

    if not include_validation:
        frame = frame[~frame["meta.campaign_id"].map(is_validation_campaign)].copy()
    if backends:
        allowed_backends = set(backends)
        frame = frame[frame["meta.backend_name"].isin(allowed_backends)].copy()
    if providers:
        allowed_providers = {p.lower() for p in providers}
        frame = frame[frame["meta.provider"].str.lower().isin(allowed_providers)].copy()

    if frame.empty:
        raise ValueError("No rows match the requested backend/provider filter.")

    frame = frame.reset_index(drop=True).copy()
    frame["period"] = (
        frame["meta.campaign_id"].astype(str) + " / w" + frame["meta.window"].astype(str)
    )

    # Explicit binary indicator for QuantumSpecific availability (Static & <= 8 qubits).
    qs_avail = frame.get("a.quantum_specific.available")
    if qs_avail is not None:
        frame["a.quantum_specific_present"] = (
            qs_avail.astype(str).str.lower().isin({"true", "1", "1.0"}).astype(float)
        )
    else:
        frame["a.quantum_specific_present"] = 0.0

    # Family annotation matching thesis Section 3.2.
    algo_to_family = {
        algo: fam for fam, algos in FAMILIES.items() for algo in algos
    }
    frame["meta.family"] = frame["meta.algorithm"].map(
        lambda a: algo_to_family.get(
            a,
            "control" if a == RANDOM_ALGORITHM else ("composite" if a == COMPOSITE_ANCHOR else "other"),
        )
    )

    a_cols = _extract_numeric_features(frame, "a.")
    b_cols = _extract_numeric_features(frame, "b.")
    circuit_features = a_cols + b_cols
    if "a.quantum_specific_present" not in circuit_features:
        circuit_features.append("a.quantum_specific_present")

    hw_submit_features = _extract_numeric_features(frame, "c.")
    hw_exec_features = _extract_numeric_features(frame, "d.")
    exec_to_submit = _canonicalize_hardware_columns(frame, hw_submit_features, hw_exec_features)

    # Ensure targets and baselines are numeric where present.
    for col, _, _ in TARGETS.values():
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

    for prefix in ("e.", "e_exec."):
        for suffix in ("m1_error", "m1_mixture_error", "m2_error", "m1_tvd", "m1_mixture_tvd", "m2_tvd"):
            col = prefix + suffix
            if col in frame.columns:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")

    if "d.changed_since_prepare" in frame.columns:
        frame["d.changed_since_prepare"] = (
            frame["d.changed_since_prepare"].astype(str).str.lower().isin({"true", "1", "1.0"})
        )

    return DatasetBundle(
        frame=frame,
        manifest_hash=manifest_hash,
        inputs=inputs,
        circuit_features=circuit_features,
        hardware_submit_features=hw_submit_features,
        hardware_exec_features=hw_exec_features,
        exec_to_submit_map=exec_to_submit,
    )


def baseline_predictions(frame: pd.DataFrame, target_key: str) -> dict[str, pd.Series]:
    """Return analytical M1 / M1-mixture / M2 predictions mapped into target space.

    Never returns inputs for ML training; used solely to benchmark ML models against
    the analytical baseline equations on static circuits where `e.*` is defined.
    """
    preds: dict[str, pd.Series] = {}
    if target_key == "success":
        for name, col in (
            ("M1 (Submit)", "e.m1_error"),
            ("M1-Mixture (Submit)", "e.m1_mixture_error"),
            ("M2 (Submit)", "e.m2_error"),
            ("M1 (Exec)", "e_exec.m1_error"),
            ("M2 (Exec)", "e_exec.m2_error"),
        ):
            if col in frame.columns:
                preds[name] = 1.0 - pd.to_numeric(frame[col], errors="coerce")
    elif target_key == "tvd":
        for name, col in (
            ("M1 (Submit)", "e.m1_tvd"),
            ("M1-Mixture (Submit)", "e.m1_mixture_tvd"),
            ("M2 (Submit)", "e.m2_tvd"),
            ("M1 (Exec)", "e_exec.m1_tvd"),
            ("M2 (Exec)", "e_exec.m2_tvd"),
        ):
            if col in frame.columns:
                preds[name] = pd.to_numeric(frame[col], errors="coerce")
    return preds


def split_temporal_and_cv(
    frame: pd.DataFrame,
    holdout_campaigns: Sequence[str] | None = None,
) -> tuple[pd.Series, list[str]]:
    """Return boolean mask `is_holdout` and list of holdout period labels.

    Supports multi-backend / multi-provider datasets by holding out the specified
    `holdout_campaigns`, or else the backend defaults (`DEFAULT_HOLDOUT_CAMPAIGNS`),
    or automatically the chronologically latest period for newly added backends
    (such as future Rigetti or IonQ campaigns).
    """
    is_holdout = pd.Series(False, index=frame.index)
    explicit = set(holdout_campaigns) if holdout_campaigns else set()

    if explicit:
        is_holdout = frame["meta.campaign_id"].isin(explicit)
    else:
        for backend, sub in frame.groupby("meta.backend_name"):
            default_campaigns = DEFAULT_HOLDOUT_CAMPAIGNS.get(str(backend))
            if default_campaigns:
                matched = sub["meta.campaign_id"].isin(default_campaigns)
                if matched.any() and (~matched).any():
                    is_holdout.loc[sub.index] = matched
                    continue
            # Automatic chronological fallback for future QPUs (Rigetti, IonQ, new IBM).
            periods = sub["period"].unique()
            if len(periods) > 1:
                if "g.finished_at" in sub.columns and sub["g.finished_at"].notna().any():
                    order = (
                        sub.groupby("period")["g.finished_at"]
                        .max()
                        .sort_values()
                        .index.tolist()
                    )
                else:
                    order = sorted(periods)
                latest_period = order[-1]
                is_holdout.loc[sub.index] = sub["period"] == latest_period

    holdout_periods = sorted(frame.loc[is_holdout, "period"].unique().tolist())
    return is_holdout, holdout_periods


def split_by_config(
    frame: pd.DataFrame,
    holdout_frac: float = 0.15,
    seed: int = 11,
) -> tuple[pd.Series, list[str]]:
    """Hold out ``holdout_frac`` of circuit *configurations* (never individual jobs).

    All repetitions of a configuration, on every chip and in every window, go to the
    same side, so train and test never share a circuit. Configurations are stratified
    by algorithm and by size (median two-qubit gate count): each algorithm's sorted
    configurations are cut into ``k`` contiguous size bins and one is drawn per bin,
    so the holdout spans small and large circuits of every algorithm.

    The choice depends only on the set of configuration ids, so the same holdout is
    obtained for each single-chip scope and for the pooled scope.
    """
    size_col = "b.two_qubit_gates" if "b.two_qubit_gates" in frame.columns else "a.num_qubits"
    cfg = (
        frame.assign(_size=pd.to_numeric(frame[size_col], errors="coerce"))
        .groupby("meta.config_id")
        .agg(algorithm=("meta.algorithm", "first"), size=("_size", "median"))
        .reset_index()
    )
    rng = np.random.default_rng(seed)
    held: list[str] = []
    for _, grp in cfg.groupby("algorithm"):
        grp = grp.sort_values(["size", "meta.config_id"])
        n = len(grp)
        k = int(round(holdout_frac * n))
        if n < 4 or k < 1:
            continue
        for chunk in np.array_split(grp["meta.config_id"].to_numpy(), k):
            held.append(str(rng.choice(chunk)))
    held_sorted = sorted(held)
    return frame["meta.config_id"].astype(str).isin(set(held_sorted)), held_sorted


def temporal_ordering(frame: pd.DataFrame, is_holdout: pd.Series) -> dict[str, object]:
    """Report whether every holdout job finished strictly after every training job.

    The thesis validates on executions collected in *later* calibration cycles, so the
    split is only a genuine temporal holdout when ``holdoutStart > trainEnd``.
    """
    if "g.finished_at" not in frame.columns:
        return {"available": False}
    t = pd.to_datetime(frame["g.finished_at"], utc=True, errors="coerce")
    train_t, hold_t = t[~is_holdout].dropna(), t[is_holdout].dropna()
    if train_t.empty or hold_t.empty:
        return {"available": False}
    return {
        "available": True,
        "trainStart": train_t.min().isoformat(),
        "trainEnd": train_t.max().isoformat(),
        "holdoutStart": hold_t.min().isoformat(),
        "holdoutEnd": hold_t.max().isoformat(),
        "strict": bool(hold_t.min() > train_t.max()),
        "holdoutJobsBeforeTrainEnd": int((hold_t <= train_t.max()).sum()),
    }


def make_exec_feature_frame(
    frame: pd.DataFrame,
    circuit_cols: Sequence[str],
    exec_to_submit: Mapping[str, str],
) -> pd.DataFrame:
    """Build a DataFrame where `d.*` execution calibration columns wear `c.*` names.

    This allows both (a) evaluating a `c.*`-trained model under execution-time calibration
    and (b) training a calibration-updated model using exact aligned columns.
    """
    cols = list(circuit_cols) + list(exec_to_submit.values())
    out = pd.DataFrame(index=frame.index)
    for col in circuit_cols:
        if col in frame.columns:
            out[col] = frame[col]
    for d_col, c_col in exec_to_submit.items():
        if d_col in frame.columns:
            out[c_col] = frame[d_col]
    return out
