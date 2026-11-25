"""Build the dashboard's prospective-validation snapshot from pre-registered predictions.

    python dashboard/export_prospective.py

Reads every scored ``report/ml_estimation/prospective/*-validation-v*_predictions.json``
(skipping abandoned collections), joins each prediction to its observed job in the
export, and writes ``dashboard/experiments/prospective/validation-v1.json``:

* ``scores`` -- per chip / model scope / regime / target / group: R², 95% CI, MAE,
  H1 verdict, plus the unseen-circuit validation reference of the same frozen model.
* ``points`` -- per configuration: observed mean vs pre-registered prediction, for
  scatter plots. Observations are averaged over the job's repetitions.

Like the other dashboard snapshots it records the export manifest hash and part
hashes, so ``build.py`` only publishes it next to the export it was computed from.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parent
ROOT = PROJECT.parent
sys.path.insert(0, str(ROOT))

from experiments.ml_dataset import TARGETS, load_ml_dataset  # noqa: E402
from experiments.qaqs_models import evaluate_predictions  # noqa: E402
from experiments.qaqs_prospective import ABANDONED_CAMPAIGNS  # noqa: E402
from experiments.validation_profile import GROUPS  # noqa: E402

PROSPECTIVE = ROOT / "report" / "ml_estimation" / "prospective"
MODELS = ROOT / "report" / "ml_estimation" / "models" / "models_manifest.json"
SCHEMA_VERSION = 1


def _clean(value):
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else round(float(value), 5)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def build(tables: Path, out: Path) -> Path:
    manifest = tables / "dataset_manifest.json"
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    parts = json.loads(manifest.read_text(encoding="utf-8"))["parts"]
    inputs = {p["file"]: hashlib.sha256((tables / p["file"]).read_bytes()).hexdigest() for p in parts}

    obs = load_ml_dataset(tables, include_validation=True).frame
    training = {
        (m["scope"], m["target"], m["regime"]): {"r2": m.get("cvR2"), "mae": m.get("cvMae"), "model": m["model"]}
        for m in json.loads(MODELS.read_text(encoding="utf-8"))["models"]
    }

    chips, scores, points = [], [], []
    for path in sorted(PROSPECTIVE.glob("*-validation-v*_predictions.json")):
        reg = json.loads(path.read_text(encoding="utf-8"))
        if reg["campaignId"] in ABANDONED_CAMPAIGNS:
            continue
        sub = obs[obs["meta.campaign_id"] == reg["campaignId"]]
        if sub.empty:
            continue  # pre-registered but not yet executed/exported
        chips.append(
            {
                "backend": reg["backend"],
                "qpu": reg.get("qpu", "seen"),
                "campaignId": reg["campaignId"],
                "createdAt": reg["createdAt"],
                "gitCommit": reg["gitCommit"],
                "jobs": int(len(sub)),
                "configs": int(sub["meta.config_id"].nunique()),
                "executedFrom": str(pd.to_datetime(sub["g.finished_at"], utc=True).min()),
                "executedTo": str(pd.to_datetime(sub["g.finished_at"], utc=True).max()),
                "trainingChips": reg.get("trainingChips", []),
            }
        )
        pred = pd.DataFrame(reg["predictions"])
        if "qpu" not in pred.columns:
            pred["qpu"], pred["transfer"] = "seen", "same_chip"
        meta = sub[["meta.config_id", "meta.algorithm", "b.two_qubit_gates", "a.num_qubits"]].drop_duplicates(
            "meta.config_id"
        )
        for (scope, target, regime), p in pred.groupby(["scope", "target", "regime"]):
            col = TARGETS[target][0]
            joined = sub[["meta.config_id", col]].merge(
                p[["config_id", "group", "predicted"]], left_on="meta.config_id", right_on="config_id"
            )
            base = {
                "backend": reg["backend"],
                "qpu": p["qpu"].iloc[0],
                "scope": scope,
                "transfer": p["transfer"].iloc[0],
                "target": target,
                "regime": regime,
                "model": training.get((scope, target, regime), {}).get("model"),
            }
            for group in ("all",) + tuple(GROUPS):
                g = joined if group == "all" else joined[joined["group"] == group]
                if len(g) < 3:
                    continue
                m = evaluate_predictions(
                    g[col].to_numpy(dtype=float), g["predicted"].to_numpy(dtype=float), g["meta.config_id"].to_numpy()
                )
                ref = training.get((scope, target, regime), {})
                scores.append(
                    {
                        **base,
                        "group": group,
                        "jobs": int(len(g)),
                        "configs": int(g["meta.config_id"].nunique()),
                        **{k: m[k] for k in ("r2", "r2CiLow", "r2CiHigh", "mae", "rmse", "spearmanRho", "h1Verdict")},
                        "trainingR2": ref.get("r2"),
                        "trainingMae": ref.get("mae"),
                    }
                )
            per_cfg = (
                joined.groupby(["meta.config_id", "group"], as_index=False)
                .agg(observed=(col, "mean"), predicted=("predicted", "first"), jobs=(col, "size"))
                .merge(meta, on="meta.config_id", how="left")
            )
            for row in per_cfg.itertuples(index=False):
                points.append(
                    {
                        **{k: base[k] for k in ("backend", "scope", "target", "regime")},
                        "config": row[0],
                        "group": row[1],
                        "observed": row.observed,
                        "predicted": row.predicted,
                        "jobs": int(row.jobs),
                        "algorithm": row[5],
                        "twoQubitGates": row[6],
                        "qubits": row[7],
                    }
                )

    payload = _clean(
        {
            "schemaVersion": SCHEMA_VERSION,
            "backend": "validation-v1",
            "manifestHash": digest,
            "inputs": inputs,
            "groups": list(GROUPS),
            "chips": chips,
            "scores": scores,
            "points": points,
        }
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False, sort_keys=True), encoding="utf-8")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tables", type=Path, default=ROOT / "experiments" / "dataset_out")
    parser.add_argument("--out", type=Path, default=PROJECT / "experiments" / "prospective" / "validation-v1.json")
    args = parser.parse_args()
    print(build(args.tables, args.out))
