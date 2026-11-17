#!/usr/bin/env python3
"""Export the frozen QAQS models to a pickle-free JSON format for ``qward.qaqs``.

    python scripts/export_qaqs_models.py --qward ../qiskit-qward

Reads the frozen joblib bundles in ``report/ml_estimation`` (Fez and Kingston circuit-only
quality models, plus the execution-cost model) and writes, inside the QWARD checkout:

* ``qward/qaqs/data/models/<id>.json``  tree arrays / support vectors / medians, plus a model
  card (validation scores, training range, provenance). No pickles: installing QWARD never
  loads executable model code.
* ``tests/data/qaqs/golden_models.json``  feature rows and the predictions of the *original*
  scikit-learn / XGBoost models, so QWARD's NumPy inference can be tested for exact parity.

This script needs the thesis environment (scikit-learn, XGBoost); QWARD itself does not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import experiments.qaqs_cost as cost  # noqa: E402,F401  (registers the model classes for joblib)
from experiments.ml_dataset import load_ml_dataset  # noqa: E402

MODELS = ROOT / "report" / "ml_estimation" / "models"
COST = ROOT / "report" / "ml_estimation" / "cost"
SCHEMA = 1
CHIPS = ("ibm_fez", "ibm_kingston")
TARGETS = ("success", "hellinger", "tvd", "dsr")
GOLDEN_ROWS = 40
# Circuit-size columns reported in every model card so users can tell when a circuit is
# larger than anything the model was trained on (not all of them are model inputs).
EXTRA_RANGE = ["b.two_qubit_gates", "b.depth", "a.num_qubits"]
# Real validation circuits kept as test fixtures: small enough to bundle, spanning algorithms,
# the three groups, a dynamic circuit, and a twirled one.
FIXTURE_CONFIGS = ("GHZ3", "GHZ16", "BV9-SINGLE", "SR2", "PE-S5", "IV5-10011", "RV4-D8-S7", "M3-4", "VTP-V5-TRIPLE", "GHZ18")


def _tree_sklearn(tree) -> dict:
    t = tree.tree_
    return {
        "left": t.children_left.tolist(),
        "right": t.children_right.tolist(),
        "feature": t.feature.tolist(),
        "threshold": t.threshold.tolist(),
        "value": t.value[:, 0, 0].tolist(),
    }


def _trees_xgboost(booster) -> list[dict]:
    out = []
    for dump in booster.get_dump(dump_format="json"):
        nodes: dict[int, dict] = {}

        def walk(node):
            nodes[node["nodeid"]] = node
            for child in node.get("children", []):
                walk(child)

        walk(json.loads(dump))
        size = max(nodes) + 1
        left, right, feat, thr, val = [-1] * size, [-1] * size, [-1] * size, [0.0] * size, [0.0] * size
        for i, n in nodes.items():
            if "leaf" in n:
                val[i] = n["leaf"]
            else:
                left[i], right[i] = n["yes"], n["no"]  # condition true -> yes
                feat[i] = int(n["split"].lstrip("f"))
                thr[i] = n["split_condition"]
        out.append({"left": left, "right": right, "feature": feat, "threshold": thr, "value": val})
    return out


def _estimator(pipeline) -> tuple[str, dict, dict]:
    """(kind, estimator json, preprocessing json) for a fitted imputer[/scaler]/model pipeline."""
    steps = dict(pipeline.steps)
    pre = {"imputer": steps["imputer"].statistics_.tolist()}
    if "scaler" in steps:
        pre["scaler"] = {"mean": steps["scaler"].mean_.tolist(), "scale": steps["scaler"].scale_.tolist()}
    model = steps["model"]
    name = type(model).__name__
    if name == "RandomForestRegressor":
        return "random_forest", {"trees": [_tree_sklearn(e) for e in model.estimators_]}, pre
    if name == "XGBRegressor":
        booster = model.get_booster()
        base = float(json.loads(booster.save_config())["learner"]["learner_model_param"]["base_score"].strip("[]"))
        return "xgboost", {"base_score": base, "trees": _trees_xgboost(booster)}, pre
    if name == "SVR":
        if model.kernel != "rbf":
            raise NotImplementedError(f"SVR kernel {model.kernel}")
        return (
            "svr_rbf",
            {
                "gamma": float(model._gamma),  # noqa: SLF001
                "support_vectors": model.support_vectors_.tolist(),
                "dual_coef": model.dual_coef_[0].tolist(),
                "intercept": float(model.intercept_[0]),
            },
            pre,
        )
    raise NotImplementedError(f"model type {name}")


def _predict_pipeline(pipeline, X: pd.DataFrame) -> np.ndarray:
    return np.asarray(pipeline.predict(X), dtype=float)


def _num(x):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else x


def _rows(frame: pd.DataFrame, features: list[str], n: int, seed: int) -> pd.DataFrame:
    sample = frame.sample(n=min(n, len(frame)), random_state=seed)
    return sample[features].apply(pd.to_numeric, errors="coerce")


def _training_range(frame: pd.DataFrame, features: list[str]) -> dict:
    out = {}
    for f in features:
        v = pd.to_numeric(frame[f], errors="coerce").dropna()
        out[f] = {"min": float(v.min()), "max": float(v.max())} if len(v) else {"min": None, "max": None}
    return out


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _qpy_b64(path: Path) -> str:
    import base64

    return base64.b64encode(path.read_bytes()).decode()


def _write_fixtures(args, *, frame_all: pd.DataFrame, out: Path, model, saved) -> None:
    """Real validation circuits (logical + compiled QPY), their stored features, and the
    pre-registered / frozen-model predictions, for end-to-end parity tests in QWARD."""
    import glob

    chips = {"ibm_fez": "fez", "ibm_kingston": "kingston"}
    fixtures = []
    needed = sorted({f for t in TARGETS for c in CHIPS for f in json.loads(
        (args.qward / "qward" / "qaqs" / "data" / "models" / f"{c}_{t}.json").read_text())["features"]})
    cost_feats = list(saved["features"])
    for chip, short in chips.items():
        reg = json.loads((ROOT / "report" / "ml_estimation" / "prospective" / f"{short}-validation-v1-2026-11-16_predictions.json").read_text())
        preds = pd.DataFrame(reg["predictions"])
        for config in FIXTURE_CONFIGS:
            rows = frame_all[(frame_all["meta.backend_name"] == chip) & (frame_all["meta.config_id"] == config)
                             & frame_all["meta.campaign_id"].str.contains("validation-v")]
            if rows.empty:
                continue
            row = rows.iloc[0]
            rec = Path(row["meta.record_path"])
            journal = json.loads(rec.read_text())
            art = rec.parent / journal["artifact_directory"]
            prepared = json.loads((art / "prepared.json").read_text())
            expected = {
                t: float(preds[(preds.config_id == config) & (preds.scope == chip) & (preds.target == t) & (preds.regime == "circuit_only")].predicted.iloc[0])
                for t in TARGETS
            }
            feats = {f: _num(float(row[f])) if f in row and pd.notna(row[f]) else None for f in needed}
            cost_row = {f: (_num(float(row[f])) if f in row and pd.notna(row[f]) else None) for f in cost_feats if f not in ("shots", "duration_s", "twirling", "dynamic", "dynamical_decoupling")}
            sample = cost.cost_frame(args.tables)
            cj = sample[sample.job_id == row["meta.job_id"]]
            fixtures.append({
                "chip": chip,
                "config": config,
                "group": ("anchor" if config in {"GHZ3", "GHZ16", "BV9-SINGLE", "SR2", "PE-S5", "M3-4", "VTP-V5-TRIPLE"} else "new" if config in {"IV5-10011", "RV4-D8-S7"} else "extrapolation"),
                "dynamic": bool(prepared["dynamic_circuit"]),
                "twirling": bool(prepared["runtime_options"]["twirling"]["enable_gates"]),
                "dynamicalDecoupling": bool(prepared["runtime_options"]["dynamical_decoupling"]["enable"]),
                "logicalQpy": _qpy_b64(art / "logical.qpy"),
                "isaQpy": _qpy_b64(art / "isa.qpy"),
                "storedFeatures": feats,
                "storedDuration": _num(float(row["c.duration_s"])) if pd.notna(row["c.duration_s"]) else None,
                "expectedQuality": expected,
                "observedBilledSeconds": float(cj["billed_seconds"].iloc[0]) if len(cj) else None,
                "expectedCostSeconds": float(model.predict(cj)[0]) if len(cj) else None,
            })
    (out / "validation_fixtures.json").write_text(json.dumps({"schemaVersion": SCHEMA, "fixtures": fixtures}, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"wrote {len(fixtures)} validation fixtures")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--qward", type=Path, required=True, help="Path to the qiskit-qward checkout")
    parser.add_argument("--tables", type=Path, default=ROOT / "experiments" / "dataset_out")
    args = parser.parse_args()

    out_models = args.qward / "qward" / "qaqs" / "data" / "models"
    out_golden = args.qward / "tests" / "data" / "qaqs"
    out_models.mkdir(parents=True, exist_ok=True)
    out_golden.mkdir(parents=True, exist_ok=True)
    for stale in out_models.glob("*.json"):
        stale.unlink()

    frame = load_ml_dataset(args.tables).frame  # training view: validation campaigns excluded
    manifest = {(m["scope"], m["target"], m["regime"]): m for m in json.loads((MODELS / "models_manifest.json").read_text())["models"]}
    summary = pd.read_csv(ROOT / "report" / "ml_estimation" / "prospective" / "validation-v1_summary.csv")
    provenance = {
        "thesisCommit": _git("rev-parse", "HEAD"),
        "modelsManifestSha256": hashlib.sha256((MODELS / "models_manifest.json").read_bytes()).hexdigest(),
        "datasetManifestSha256": hashlib.sha256((args.tables / "dataset_manifest.json").read_bytes()).hexdigest(),
        "trainingJobs": int(len(frame)),
    }
    golden: dict = {"schemaVersion": SCHEMA, "models": {}}

    for chip in CHIPS:
        sub = frame[frame["meta.backend_name"] == chip]
        for target in TARGETS:
            bundle = joblib.load(MODELS / f"{chip}_{target}_circuit_only.joblib")
            kind, estimator, pre = _estimator(bundle["pipeline"])
            features = list(bundle["features"])
            row = manifest[(chip, target, "circuit_only")]
            rows = summary[(summary.regime == "circuit_only") & (summary.group == "new") & (summary.target == target) & (summary.scope == chip)]
            same = rows[rows.backend == chip]
            unseen = rows[rows.backend == "ibm_marrakesh"]

            def card(df):
                if df.empty:
                    return None
                r = df.iloc[0]
                return {k: _num(float(r[k])) if k != "h1Verdict" else r[k] for k in ("r2", "r2CiLow", "r2CiHigh", "mae", "h1Verdict")} | {
                    "configs": int(r["configs"]), "jobs": int(r["jobs"])}

            payload = {
                "schemaVersion": SCHEMA,
                "id": f"{chip}/{target}",
                "kind": kind,
                "chip": chip,
                "target": target,
                "targetColumn": bundle["target_column"],
                "modelName": bundle["model_name"],
                "features": features,
                "clip": list(bundle["clip_bounds"]),
                "preprocessing": pre,
                "estimator": estimator,
                "card": {
                    "trainedOnJobs": int(bundle["total_rows"]),
                    "unseenCircuitValidation": {"r2": _num(row["cvR2"]), "mae": _num(row["cvMae"])},
                    "prospectiveValidation": {"sameChip": card(same), "unseenChip": card(unseen)},
                    "trainingRange": _training_range(sub, features + EXTRA_RANGE),
                    "provenance": provenance,
                },
            }
            (out_models / f"{chip}_{target}.json").write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
            X = _rows(sub, features, GOLDEN_ROWS, seed=11)
            raw = _predict_pipeline(bundle["pipeline"], X)
            golden["models"][payload["id"]] = {
                "features": features,
                "rows": [[_num(float(v)) for v in r] for r in X.to_numpy()],
                "raw": raw.tolist(),
                "clipped": np.clip(raw, *bundle["clip_bounds"]).tolist(),
            }

    # ---- execution-cost model
    saved = joblib.load(COST / "cost_model.joblib")
    model = saved["pipeline"]
    snapshot = json.loads((ROOT / "dashboard" / "experiments" / "cost" / "cost-v1.json").read_text())
    data = cost.cost_frame(args.tables)
    train = data[~data["validation"]]
    res = model.residual_
    payload = {
        "schemaVersion": SCHEMA,
        "id": "cost/billed_seconds",
        "kind": "cost_hybrid",
        "chip": "all",
        "target": "billed_seconds",
        "features": list(saved["features"]),
        "shots": 1024,
        "physical": {
            "durationFill": float(model.physical_.duration_fill_),
            "shotCoef": model.physical_.shot_coef_.tolist(),
            "overhead": float(model.physical_.overhead_),
            "overheadTwirling": float(model.physical_.overhead_twirling_),
        },
        "preprocessing": {"imputer": model.imputer_.statistics_.tolist()},
        "estimator": {
            "init": float(res.init_.constant_[0, 0]),
            "learningRate": float(res.learning_rate),
            "trees": [_tree_sklearn(e[0]) for e in res.estimators_],
        },
        "secondsPerRu": 60.0,
        "card": {
            "trainedOnJobs": int(saved["trained_jobs"]),
            "unseenCircuitValidation": snapshot["unseenCircuit"]["metrics"][snapshot["primaryModel"]],
            "newRunValidation": snapshot["newRun"][snapshot["primaryModel"]],
            "ibmRuleOfThumbNewRun": snapshot["newRun"]["IBM rule of thumb"]["all"],
            "trainingRange": _training_range(train, [f for f in saved["features"] if f in train.columns]),
            "physicalTerms": saved["physical_terms"],
            "provenance": provenance,
        },
    }
    (out_models / "cost_billed_seconds.json").write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    sample = train.sample(n=GOLDEN_ROWS, random_state=11)
    X = sample[list(saved["features"])]
    golden["models"]["cost/billed_seconds"] = {
        "features": list(saved["features"]),
        "rows": [[_num(float(v)) for v in r] for r in X.to_numpy(dtype=float)],
        "raw": model.predict(sample).tolist(),
        "physical": model.physical_.predict(sample).tolist(),
        "circuitSeconds": model.physical_.predict_circuit_seconds(sample).tolist(),
    }
    (out_golden / "golden_models.json").write_text(json.dumps(golden, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    _write_fixtures(args, frame_all=load_ml_dataset(args.tables, include_validation=True).frame, out=out_golden, model=model, saved=saved)
    sizes = sum(p.stat().st_size for p in out_models.glob("*.json"))
    print(f"wrote {len(list(out_models.glob('*.json')))} models ({sizes / 1e6:.2f} MB) to {out_models}")
    print(f"wrote golden parity data to {out_golden / 'golden_models.json'}")


if __name__ == "__main__":
    main()
