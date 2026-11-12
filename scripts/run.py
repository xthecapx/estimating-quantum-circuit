#!/usr/bin/env python3
"""Thesis collection commands; use an environment with published QWARD installed."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    "ibm": [sys.executable, str(ROOT / "scripts/ibm_campaign_ci.py")],
    "ibm-windows": ["bash", str(ROOT / "experiments/run_campaign.sh")],
    "rigetti": [sys.executable, "-m", "experiments.aws_campaign"],
    "decay": [sys.executable, "-m", "experiments.scalability_regression"],
    "export-ibm": [sys.executable, "-m", "experiments.dataset_export"],
    "dashboard": [sys.executable, str(ROOT / "dashboard/build.py")],
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=ROUTES)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    return subprocess.run(ROUTES[args.target] + args.arguments, cwd=ROOT,
                          env=environment, check=False).returncode

if __name__ == "__main__":
    raise SystemExit(main())
