#!/usr/bin/env python3
"""Verify copied files, optionally comparing the original QWARD source too."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Original qiskit-qward checkout")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "migration-manifest.json").read_text())
    errors = []
    for row in manifest["files"]:
        path = ROOT / row["destination"]
        if not path.is_file() or digest(path) != row["destination_sha256"]:
            errors.append("Changed/missing destination: " + row["destination"])
        if args.source:
            original = args.source / row["source"]
            if not original.is_file() or digest(original) != row["source_sha256"]:
                errors.append("Changed/missing original: " + row["source"])
    print(json.dumps({"checked_files": len(manifest["files"]), "errors": errors}, indent=2))
    return bool(errors)

if __name__ == "__main__":
    raise SystemExit(main())
