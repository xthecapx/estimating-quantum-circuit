#!/usr/bin/env python3
"""Re-stamp dashboard snapshots after an export that only *added* columns or rows.

Every dashboard snapshot records the export manifest hash and part hashes, so any new
export invalidates them even when their numbers cannot change. This script verifies
that claim before re-stamping:

* every column of the previous export is byte-identical in the new one for the rows a
  snapshot was computed from (training rows for estimation/decay, all rows for
  prospective), and
* rows were only added, never removed.

Pass the previous export directory with --previous; it is never modified.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.ml_dataset import load_ml_dataset  # noqa: E402

SNAPSHOT_DIRS = ("estimation", "decay", "prospective", "cost")


def manifest_inputs(tables: Path):
    manifest = tables / "dataset_manifest.json"
    parts = json.loads(manifest.read_text(encoding="utf-8"))["parts"]
    return (
        hashlib.sha256(manifest.read_bytes()).hexdigest(),
        {p["file"]: hashlib.sha256((tables / p["file"]).read_bytes()).hexdigest() for p in parts},
    )


def verify_additive(previous: Path, current: Path) -> None:
    old = load_ml_dataset(previous, include_validation=True).frame.set_index("meta.job_id").sort_index()
    new = load_ml_dataset(current, include_validation=True).frame.set_index("meta.job_id")
    missing = old.index.difference(new.index)
    if len(missing):
        raise SystemExit(f"{len(missing)} jobs disappeared from the export; snapshots must be recomputed")
    new = new.loc[old.index]
    cols = [c for c in old.columns if c != "meta.record_path"]
    absent = [c for c in cols if c not in new.columns]
    if absent:
        raise SystemExit(f"columns removed from the export: {absent[:5]}")
    changed = [c for c in cols if not ((old[c] == new[c]) | (old[c].isna() & new[c].isna())).all()]
    if changed:
        raise SystemExit(f"existing columns changed ({changed[:5]}); snapshots must be recomputed")
    print(f"verified additive export: {len(old)} existing jobs unchanged, {len(new.columns) - len(cols) - 1} columns added")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--previous", type=Path, required=True, help="Previous export directory (read only)")
    parser.add_argument("--tables", type=Path, default=ROOT / "experiments" / "dataset_out")
    args = parser.parse_args()
    verify_additive(args.previous, args.tables)
    old_digest, _ = manifest_inputs(args.previous)
    digest, inputs = manifest_inputs(args.tables)
    for sub in SNAPSHOT_DIRS:
        for path in sorted((ROOT / "dashboard" / "experiments" / sub).glob("*.json")):
            snap = json.loads(path.read_text(encoding="utf-8"))
            if snap.get("manifestHash") != old_digest:
                print(f"skip {path.relative_to(ROOT)}: built from another export")
                continue
            snap["manifestHash"], snap["inputs"] = digest, inputs
            path.write_text(json.dumps(snap, separators=(",", ":"), allow_nan=False, sort_keys=True), encoding="utf-8")
            print(f"re-stamped {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
