"""QAQS quality-estimation pipeline: evaluate, save models, write report and dashboard data.

    python -m experiments.ml_estimation

One evaluation path: nested repeated grouped K-fold over circuit configurations
(``qaqs_kfold``). Scopes are derived from the export: one per chip, one per provider
when several providers are present, and ``pooled`` when there is more than one chip.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from experiments.ml_dataset import ALL_TARGETS, CAMPAIGN_ROLES, DatasetBundle, load_ml_dataset
from experiments.qaqs_kfold import analyze_scope_kfold, assign_config_folds, provider_transfer
from experiments.qaqs_models import (  # noqa: F401  (re-exported for callers of this module)
    H1_R2_THRESHOLD,
    ROOT,
    _clean_json,
    build_models,
    compute_cross_chip_transfer,
    evaluate_predictions,
    h1_verdict,
)
from experiments.qaqs_report import write_reports

DEFAULT_TABLES = ROOT / "experiments" / "dataset_out"
DEFAULT_REPORT_OUT = ROOT / "report" / "ml_estimation"
DEFAULT_DASHBOARD_OUT = ROOT / "dashboard" / "experiments" / "estimation"


def build_scopes(frame: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Scopes to evaluate, from the data: chips, then providers, then ``pooled``."""
    chips = sorted(frame["meta.backend_name"].unique().tolist())
    scopes = [(chip, frame[frame["meta.backend_name"] == chip].copy()) for chip in chips]
    providers = sorted(frame["meta.provider"].unique().tolist())
    if len(providers) > 1:
        for prov in providers:
            sub = frame[frame["meta.provider"] == prov]
            if sub["meta.backend_name"].nunique() > 1:  # a one-chip provider is its chip scope
                scopes.append((f"provider_{prov}", sub.copy()))
    if len(chips) > 1:
        scopes.append(("pooled", frame.copy()))
    return scopes


def dataset_summary(tables: Path, bundle: DatasetBundle) -> dict[str, Any]:
    everything = load_ml_dataset(tables, roles=CAMPAIGN_ROLES).frame
    return {
        "manifestHash": bundle.manifest_hash,
        "chips": sorted(bundle.frame["meta.backend_name"].unique().tolist()),
        "providers": sorted(bundle.frame["meta.provider"].unique().tolist()),
        "campaignRoles": {k: int(v) for k, v in everything["meta.campaign_role"].value_counts().items()},
    }


def run_pipeline(
    tables: Path = DEFAULT_TABLES,
    report_out: Path = DEFAULT_REPORT_OUT,
    dashboard_out: Path = DEFAULT_DASHBOARD_OUT,
    backends: Sequence[str] | None = None,
    split_seed: int = 11,
    n_splits: int = 5,
    n_repeats: int = 3,
    n_jobs: int = -1,
) -> dict[str, dict[str, Any]]:
    """Evaluate every scope and write models, report tables and dashboard snapshots."""
    bundle = load_ml_dataset(tables, backends=backends)
    frame = bundle.frame
    fold_table = assign_config_folds(frame, n_splits=n_splits, n_repeats=n_repeats, seed=split_seed)
    print(
        f"K-fold: {n_splits} folds x {n_repeats} repeats over {len(fold_table)} configurations "
        f"(seed={split_seed}).",
        flush=True,
    )
    snapshots = {
        name: analyze_scope_kfold(
            bundle, name, sub, fold_table,
            models_dir=report_out / "models", random_state=split_seed, n_jobs=n_jobs,
        )
        for name, sub in build_scopes(frame)
    }

    # Transfer between chips and between providers, attached to every scope's payload.
    chips = [c for c in sorted(frame["meta.backend_name"].unique()) if c in snapshots]
    model_for_transfer = build_models(random_state=split_seed)["LightGBM"]
    for target_key in ALL_TARGETS:
        feats = {}
        for chip in chips:
            t = snapshots[chip]["targets"].get(target_key)
            if t:
                fp, hw, dev = t["selectedFootprintFeatures"], t["selectedHardwareFeatures"], t["selectedDeviceFeatures"]
                feats[chip] = {"circuit_only": fp, "hardware_only": dev, "layout_only": hw, "mixed_submit": fp + hw}
        matrix = compute_cross_chip_transfer(bundle, target_key, feats, model_for_transfer) if len(feats) > 1 else []
        providers = provider_transfer(bundle, target_key, random_state=split_seed)
        for payload in snapshots.values():
            if target_key in payload["targets"]:
                payload["targets"][target_key]["h3"]["transferMatrix"] = _clean_json(matrix)
                payload["targets"][target_key]["h3"]["providerTransfer"] = _clean_json(providers)

    dashboard_out.mkdir(parents=True, exist_ok=True)
    for stale in dashboard_out.glob("*.json"):
        if stale.stem not in snapshots:
            stale.unlink()
    for scope, payload in snapshots.items():
        (dashboard_out / f"{scope}.json").write_text(
            json.dumps(payload, separators=(",", ":"), allow_nan=False, sort_keys=True), encoding="utf-8"
        )
    print(f"Wrote estimation snapshots for {list(snapshots)}", flush=True)
    write_reports(snapshots, report_out, dataset_summary(tables, bundle))
    return snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_OUT)
    parser.add_argument("--dashboard-out", type=Path, default=DEFAULT_DASHBOARD_OUT)
    parser.add_argument("--backend", action="append", help="Optional chip filter; repeatable. Default: every chip.")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=-1, help="Parallel workers (-1 = all cores).")
    parser.add_argument("--split-seed", type=int, default=11)
    args = parser.parse_args()
    snapshots = run_pipeline(
        tables=args.tables,
        report_out=args.report_out,
        dashboard_out=args.dashboard_out,
        backends=args.backend,
        split_seed=args.split_seed,
        n_splits=args.folds,
        n_repeats=args.repeats,
        n_jobs=args.jobs,
    )
    for scope, snap in snapshots.items():
        parts = []
        for tkey, tdata in snap["targets"].items():
            cv = tdata["leaderboard"][0]["cv"] if tdata["leaderboard"] else {}
            if cv.get("r2") is not None:
                parts.append(f"{tkey}={cv['r2']:.3f} ({cv.get('h1Verdict')})")
        print(f"[{scope}] jobs={snap['jobs']} | procedure R2: {', '.join(parts)}")


if __name__ == "__main__":
    main()
