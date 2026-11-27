#!/usr/bin/env python3
"""Print the current thesis dataset coverage: jobs per chip, algorithm, campaign and role.

Run from the estimating-quantum-circuit root:
    .venv/bin/python skills/phd-thesis/scripts/data_summary.py [--tables experiments/dataset_out]

Reads only identity columns, so it is fast and needs no QWARD import.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
COLUMNS = ["meta.backend_name", "meta.algorithm", "meta.campaign_id", "meta.config_id"]


def campaign_role(campaign_id: str) -> str:
    """Same rule as experiments.ml_dataset.campaign_role; imported when available."""
    try:
        sys.path.insert(0, str(ROOT))
        from experiments.ml_dataset import campaign_role as role  # noqa: PLC0415

        return role(campaign_id)
    except Exception:  # pragma: no cover - fallback keeps the script dependency-free
        return "validation" if "-validation-v" in campaign_id else "train"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", type=Path, default=ROOT / "experiments/dataset_out")
    args = parser.parse_args()

    manifest = json.loads((args.tables / "dataset_manifest.json").read_text(encoding="utf-8"))
    frame = pd.concat(
        pd.read_csv(args.tables / part["file"], usecols=COLUMNS) for part in manifest["parts"]
    )
    frame["role"] = frame["meta.campaign_id"].map(campaign_role)

    print(f"Export: {args.tables}  rows={len(frame)}  manifest rows={manifest['rows']}")
    print("\nJobs by algorithm and chip:")
    print(frame.pivot_table(index="meta.algorithm", columns="meta.backend_name",
                            values="meta.config_id", aggfunc="size", fill_value=0).to_string())
    print("\nJobs by role and chip:")
    print(frame.pivot_table(index="role", columns="meta.backend_name",
                            values="meta.config_id", aggfunc="size", fill_value=0).to_string())
    print("\nCampaigns:")
    campaigns = frame.groupby(["meta.campaign_id", "role", "meta.backend_name"]).size()
    print(campaigns.rename("jobs").reset_index().to_string(index=False))
    print("\nDistinct configurations per chip (train role):")
    train = frame[frame["role"] == "train"]
    print(train.groupby("meta.backend_name")["meta.config_id"].nunique().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
