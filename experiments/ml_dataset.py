"""Provider-agnostic dataset loading and split helpers for QAQS ML estimation."""

from __future__ import annotations

import hashlib
import json
import re
import warnings
from dataclasses import dataclass, field
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

# Chance-corrected targets: the outcome with the chance level of the circuit removed,
# so an algorithm that only reaches chance scores 0 whatever its success-set size.
# Kept apart from ``TARGETS`` because the frozen v1 models and their prospective
# scores cover ``TARGETS`` only.
CHANCE_CORRECTED_TARGETS: dict[str, tuple[str, str, bool]] = {
    "success_adj": (
        "f.fidelity.chance_corrected_success",
        "Chance-Corrected Success",
        True,
    ),
}
ALL_TARGETS: dict[str, tuple[str, str, bool]] = {**TARGETS, **CHANCE_CORRECTED_TARGETS}

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

# --------------------------------------------------------------------------- campaigns
#
# Every campaign has exactly one role. Nothing else in the pipeline names a campaign.
#
#   train        enters model fitting, feature selection, tuning and every split.
#   validation   prospective validation: scored against frozen models, never trained on.
#   exploratory  one-off studies with their own question (e.g. a transfer window). Kept
#                out of training so they can never leak into a later evaluation.
#
# New providers need no entry here: an unlisted campaign is `train` unless its id
# carries a validation marker.
VALIDATION_CAMPAIGN_MARKERS: tuple[str, ...] = ("-validation-v",)
EXPLORATORY_CAMPAIGNS: frozenset[str] = frozenset({"fez-ghz-bv-transfer-v1-2026-11-23"})
CAMPAIGN_ROLES: tuple[str, ...] = ("train", "validation", "exploratory")

# Calibration-cycle validation holds out the latest windows of each chip until they
# cover at least this share of the chip's training-role jobs.
CALIBRATION_CYCLE_HOLDOUT_SHARE = 0.30

# Device-level calibration: one value per (chip, calibration snapshot). The exported
# `c.*` columns summarise only the qubits a circuit was mapped to, so they encode circuit
# size; `cal.*` is the median of those summaries over every job that shares a snapshot.
DEVICE_CALIBRATION_PREFIX = "cal."
CHANCE_BASELINE_COLUMN = "f.fidelity.chance_baseline"


def is_validation_campaign(campaign_id: str) -> bool:
    return any(marker in str(campaign_id) for marker in VALIDATION_CAMPAIGN_MARKERS)


def campaign_role(campaign_id: str) -> str:
    """Role of a campaign: ``train``, ``validation`` or ``exploratory``."""
    if is_validation_campaign(campaign_id):
        return "validation"
    if str(campaign_id) in EXPLORATORY_CAMPAIGNS:
        return "exploratory"
    return "train"


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
    device_calibration_features: list[str] = field(default_factory=list)


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
    roles: Sequence[str] | None = None,
) -> DatasetBundle:
    """Load and validate CSV dataset parts against `dataset_manifest.json`.

    Compatible with current IBM exports and future Rigetti / IonQ CSV exports using
    the same schema convention (`meta.*`, `a.*`, `b.*`, `c.*`, `d.*`, `e.*`, `f.*`, `g.*`).

    Only ``train``-role campaigns are returned by default (see ``campaign_role``), so the
    training pipeline can never see prospective-validation or exploratory collections.
    ``include_validation=True`` returns every campaign; ``roles`` selects explicitly.
    ``manifest_hash``/``inputs`` still describe the full export.
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

    frame["meta.campaign_role"] = frame["meta.campaign_id"].map(campaign_role)
    wanted = set(roles) if roles is not None else (set(CAMPAIGN_ROLES) if include_validation else {"train"})
    unknown = wanted - set(CAMPAIGN_ROLES)
    if unknown:
        raise ValueError(f"Unknown campaign roles: {sorted(unknown)}")
    frame = frame[frame["meta.campaign_role"].isin(wanted)].copy()
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
    device_features = add_device_calibration(frame, hw_submit_features)

    # Ensure targets and baselines are numeric where present.
    for col, _, _ in ALL_TARGETS.values():
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
        device_calibration_features=device_features,
    )


def add_device_calibration(frame: pd.DataFrame, hw_submit_features: Sequence[str]) -> list[str]:
    """Add ``cal.*`` device-level calibration columns in place; return their names.

    One value per (chip, calibration snapshot): the median, over every job submitted
    under that snapshot, of the job's ``c.<metric>.median``. It cannot vary with the
    circuit inside a snapshot, unlike ``c.*``. Jobs without a snapshot timestamp fall
    back to their collection window.
    """
    if "c.calibrated_at" in frame.columns:
        snapshot = frame["c.calibrated_at"].astype(str)
        snapshot = snapshot.where(frame["c.calibrated_at"].notna(), frame["period"].astype(str))
    else:
        snapshot = frame["period"].astype(str)
    key = frame["meta.backend_name"].astype(str) + " @ " + snapshot
    out: list[str] = []
    with warnings.catch_warnings():  # a handful of in-place columns on an already wide frame
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        frame["meta.calibration_snapshot"] = key
        for col in hw_submit_features:
            if not col.endswith(".median"):
                continue
            name = DEVICE_CALIBRATION_PREFIX + col[2 : -len(".median")]
            frame[name] = frame.groupby(key)[col].transform("median")
            if frame[name].notna().any():
                out.append(name)
    return out


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
    holdout_share: float = CALIBRATION_CYCLE_HOLDOUT_SHARE,
) -> tuple[pd.Series, list[str]]:
    """Calibration-cycle split: boolean mask ``is_holdout`` and the held-out periods.

    Per chip, collection windows are ordered by their last finished job and the latest
    ones are held out until they cover ``holdout_share`` of the chip's jobs. The rule
    is derived from the data, so a new chip or provider needs no configuration.
    ``holdout_campaigns`` overrides it with explicit campaign ids.
    """
    is_holdout = pd.Series(False, index=frame.index)
    if holdout_campaigns:
        is_holdout = frame["meta.campaign_id"].isin(set(holdout_campaigns))
    else:
        has_time = "g.finished_at" in frame.columns
        for _, sub in frame.groupby("meta.backend_name"):
            if sub["period"].nunique() < 2:
                continue
            if has_time and sub["g.finished_at"].notna().any():
                finished = pd.to_datetime(sub["g.finished_at"], utc=True, errors="coerce")
                order = finished.groupby(sub["period"]).max().sort_values().index.tolist()
            else:
                order = sorted(sub["period"].unique())
            sizes = sub["period"].value_counts()
            held: list[str] = []
            covered = 0
            for period in reversed(order[1:]):  # the earliest window always trains
                held.append(period)
                covered += int(sizes[period])
                if covered >= holdout_share * len(sub):
                    break
            is_holdout.loc[sub.index] = sub["period"].isin(held)

    holdout_periods = sorted(frame.loc[is_holdout, "period"].unique().tolist())
    return is_holdout, holdout_periods


def headline_mask(frame: pd.DataFrame, target_key: str) -> pd.Series:
    """Jobs that count towards the headline score of a target.

    The composite anchor sits at its chance level on raw targets, so separating it
    from the other algorithms earns R^2 without predicting anything: it is scored
    separately. On a chance-corrected target every job counts.
    """
    if target_key in CHANCE_CORRECTED_TARGETS:
        return pd.Series(True, index=frame.index)
    return frame["meta.algorithm"] != COMPOSITE_ANCHOR


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
