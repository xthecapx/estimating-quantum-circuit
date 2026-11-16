"""QAQS prospective validation: pre-register predictions, then score them.

Two stages, with a commit in between:

1. ``predict`` (after ``ibm_campaign_ci.py prepare``, before ``submit``). Reads the
   frozen prepared records of a validation collection, builds the same pre-runtime
   feature row the exporter would, and predicts every target with the frozen models
   in ``report/ml_estimation/models``. Writes one predictions file per collection
   with the model manifest hash, the git commit and every input hash. Commit it
   before submitting any job.

2. ``score`` (after ``recover`` and ``export-ibm``). Joins the committed predictions
   to the observed results by job configuration, checks that the prepared records
   and models still have the hashes recorded at prediction time, and reports R²,
   MAE and 95% cluster-bootstrap intervals per group (anchor / new / extrapolation),
   target, regime and scope.

Pre-registered pass criteria (fixed before any execution; see ``CRITERIA``):

* H1 (``new`` group, circuit-only, per chip): R² 95% CI lower bound >= 0.80 passes;
  CI entirely below 0.80 fails; otherwise inconclusive. Reported for every target.
* Calibration drift (``anchor`` group): MAE compared with the unseen-circuit
  validation MAE of the same scope/target; reported, no threshold.
* H2 (``extrapolation`` group): reported as measured, no threshold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd

from experiments import validation_profile as vp
from experiments.dataset_export import _group, flatten
from experiments.ml_dataset import TARGETS, load_ml_dataset
from experiments.ml_estimation import H1_R2_THRESHOLD, evaluate_predictions

ROOT = Path(__file__).resolve().parents[1]
MODELS_SUBDIR = Path("report") / "ml_estimation" / "models"
OUT_SUBDIR = Path("report") / "ml_estimation" / "prospective"


def models_dir() -> Path:
    return ROOT / MODELS_SUBDIR


def default_out_dir() -> Path:
    return ROOT / OUT_SUBDIR
SCHEMA_VERSION = 1

CRITERIA = {
    "h1": {
        "group": "new",
        "regime": "circuit_only",
        "threshold": H1_R2_THRESHOLD,
        "rule": "pass if 95% CI lower bound >= threshold; fail if upper bound < threshold; else inconclusive",
    },
    "drift": {"group": "anchor", "rule": "report MAE vs unseen-circuit validation MAE; no threshold"},
    "h2": {"group": "extrapolation", "rule": "report as measured; no threshold"},
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        )
        # Only tracked files count: a fresh `prepare` legitimately leaves new, untracked
        # plans and records, which are committed together with the predictions.
        dirty = subprocess.run(
            [
                "git", "status", "--porcelain", "--untracked-files=no", "--",
                "report/ml_estimation/models", "experiments", "scripts",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


# ----------------------------------------------------------------- feature rows


def prepared_row(prepared: Mapping[str, Any]) -> Dict[str, Any]:
    """Pre-runtime feature row from a prepared record; same column names as the export."""
    features = prepared["payload"].get("features", {})
    row: Dict[str, Any] = {
        "meta.algorithm": prepared["algorithm"],
        "meta.config_id": prepared["config_id"],
        "meta.backend_name": prepared["backend_name"],
        "meta.campaign_id": prepared["campaign_id"],
    }
    logical, isa = dict(features.get("logical", {})), dict(features.get("isa", {}))
    for source, prefix in ((logical, "a"), (isa, "b")):
        metrics = source.pop("qward_metrics", None)
        _group(prefix, source, row)
        if metrics:
            flatten(metrics, prefix, row)
    _group("c", features.get("hardware_at_submission"), row)
    _group("e", features.get("baselines"), row)
    qs = row.get("a.quantum_specific.available")
    row["a.quantum_specific_present"] = 1.0 if str(qs).lower() in {"true", "1", "1.0"} else 0.0
    return row


def check_group_sizes(frame: pd.DataFrame, tables: Path) -> List[str]:
    """Verify group labels against the compiled circuits of *this* preparation.

    ``new`` must stay within, and ``extrapolation`` must exceed, the largest compiled
    two-qubit-gate count measured for the same algorithm on the same chip. Returns
    violations; ``predict`` refuses to pre-register if any exist.
    """
    train = load_ml_dataset(tables).frame
    backend = str(frame["meta.backend_name"].iloc[0])
    measured = train[train["meta.backend_name"] == backend].groupby("meta.algorithm")["b.two_qubit_gates"].max()
    problems = []
    for idx in frame.index:
        algo = frame.at[idx, "meta.algorithm"]
        group = frame.at[idx, "validation.group"]
        size = float(frame.at[idx, "b.two_qubit_gates"])
        limit = float(measured.get(algo, np.nan))
        cfg = frame.at[idx, "meta.config_id"]
        if group == "new" and size > limit:
            problems.append(f"{cfg}: new but {size:.0f} 2Q gates > measured max {limit:.0f}")
        if group == "extrapolation" and not size > limit:
            problems.append(f"{cfg}: extrapolation but {size:.0f} 2Q gates <= measured max {limit:.0f}")
    return problems


def _collection_records(campaign_id: str) -> List[Path]:
    """Prepared record JSON paths of one collection, via its plan manifests."""
    paths: List[Path] = []
    for manifest in sorted(ROOT.glob("experiments/*/plans/*_manifest.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("campaign_id") != campaign_id:
            continue
        for item in data["items"]:
            record = Path(item["record_path"])
            if not record.is_absolute() or not record.exists():
                record = manifest.parent.parent / "data" / "qpu" / "v2" / Path(item["record_path"]).name
            paths.append(record)
    return paths


def _load_bundles(scopes: Sequence[str]) -> Dict[tuple, Dict[str, Any]]:
    bundles = {}
    for path in sorted(models_dir().glob("*.joblib")):
        bundle = joblib.load(path)
        if bundle["scope"] in scopes:
            bundles[(bundle["scope"], bundle["target"], bundle["regime"])] = {
                "bundle": bundle,
                "path": path,
                "sha256": _sha256(path),
            }
    return bundles


# ----------------------------------------------------------------------- predict


def predict(
    campaign_id: str,
    out_dir: Path | None = None,
    tables: Path | None = None,
    allow_dirty: bool = False,
) -> Path:
    """Write the pre-registered predictions for one prepared collection."""
    out_dir = out_dir or default_out_dir()
    tables = tables or ROOT / "experiments" / "dataset_out"
    records = _collection_records(campaign_id)
    if not records:
        raise FileNotFoundError(f"No prepared manifests found for {campaign_id}; run prepare first")
    groups = vp.group_of()
    rows, inputs = [], {}
    for record in records:
        journal = json.loads(record.read_text(encoding="utf-8"))
        prepared_path = record.parent / journal["artifact_directory"] / "prepared.json"
        prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
        if journal.get("individual_results"):
            raise ValueError(f"{record.name} already has results; predictions must precede execution")
        row = prepared_row(prepared)
        if row["meta.config_id"] not in groups:
            raise ValueError(f"{row['meta.config_id']} is not in {vp.PROFILE_NAME}")
        row["validation.group"] = groups[row["meta.config_id"]]
        rows.append(row)
        inputs[str(prepared_path.relative_to(ROOT))] = _sha256(prepared_path)

    frame = pd.DataFrame(rows)
    backend = str(frame["meta.backend_name"].iloc[0])
    problems = check_group_sizes(frame, tables)
    if problems:
        raise ValueError("Group labels contradict the compiled circuits:\n  " + "\n  ".join(problems))
    scopes = [backend, "pooled"]
    bundles = _load_bundles(scopes)
    if not bundles:
        raise FileNotFoundError(f"No frozen models for {scopes} in {models_dir()}")
    manifest_path = models_dir() / "models_manifest.json"
    commit = _git_commit()
    if not allow_dirty and (commit is None or commit.endswith("-dirty")):
        raise RuntimeError(
            f"Frozen models/code must be committed before pre-registration (git: {commit}). "
            "Commit, then re-run predict."
        )

    predictions: List[Dict[str, Any]] = []
    for (scope, target, regime), info in sorted(bundles.items()):
        bundle = info["bundle"]
        X = pd.DataFrame(index=frame.index)
        missing = []
        for col in bundle["features"]:
            if col in frame.columns:
                X[col] = pd.to_numeric(frame[col], errors="coerce")
            else:
                X[col] = np.nan
                missing.append(col)
        pred = np.clip(bundle["pipeline"].predict(X), *bundle.get("clip_bounds", (0.0, 1.0)))
        for idx, value in zip(frame.index, pred):
            predictions.append(
                {
                    "config_id": frame.at[idx, "meta.config_id"],
                    "algorithm": frame.at[idx, "meta.algorithm"],
                    "group": frame.at[idx, "validation.group"],
                    "scope": scope,
                    "target": target,
                    "regime": regime,
                    "model": bundle["model_name"],
                    "predicted": float(value),
                    "missingFeatures": missing,
                }
            )

    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "profile": vp.PROFILE_NAME,
        "campaignId": campaign_id,
        "backend": backend,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "gitCommit": commit,
        "criteria": CRITERIA,
        "modelsManifestSha256": _sha256(manifest_path),
        "models": {
            f"{s}/{t}/{r}": {"path": str(i["path"].relative_to(ROOT)), "sha256": i["sha256"]}
            for (s, t, r), i in sorted(bundles.items())
        },
        "preparedInputs": inputs,
        "configurations": {
            row["meta.config_id"]: {"algorithm": row["meta.algorithm"], "group": row["validation.group"]}
            for row in rows
        },
        "predictions": predictions,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{campaign_id}_predictions.json"
    if out.exists():
        raise FileExistsError(f"{out} exists; pre-registered predictions are never overwritten")
    out.write_text(json.dumps(payload, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return out


# ------------------------------------------------------------------------- score


def score(predictions_path: Path, tables: Path, out_dir: Path | None = None) -> Path:
    """Score committed predictions against the exported observations of the same collection."""
    out_dir = out_dir or default_out_dir()
    reg = json.loads(predictions_path.read_text(encoding="utf-8"))
    for rel, digest in reg["preparedInputs"].items():
        if _sha256(ROOT / rel) != digest:
            raise ValueError(f"Prepared record changed after pre-registration: {rel}")
    for key, info in reg["models"].items():
        if _sha256(ROOT / info["path"]) != info["sha256"]:
            raise ValueError(f"Frozen model changed after pre-registration: {key}")

    obs = load_ml_dataset(tables).frame
    obs = obs[obs["meta.campaign_id"] == reg["campaignId"]]
    if obs.empty:
        raise ValueError(f"No exported observations for {reg['campaignId']}; run recover and export-ibm")
    pred = pd.DataFrame(reg["predictions"])
    unseen = _unseen_circuit_mae()

    rows: List[Dict[str, Any]] = []
    for (scope, target, regime), p in pred.groupby(["scope", "target", "regime"]):
        col = TARGETS[target][0]
        joined = obs[["meta.config_id", col]].merge(
            p[["config_id", "group", "predicted"]], left_on="meta.config_id", right_on="config_id"
        )
        for group in ("all",) + vp.GROUPS:
            sub = joined if group == "all" else joined[joined["group"] == group]
            if len(sub) < 3:
                continue
            m = evaluate_predictions(
                sub[col].to_numpy(dtype=float),
                sub["predicted"].to_numpy(dtype=float),
                sub["meta.config_id"].to_numpy(),
            )
            rows.append(
                {
                    "scope": scope,
                    "target": target,
                    "regime": regime,
                    "group": group,
                    "jobs": int(len(sub)),
                    "configs": int(sub["meta.config_id"].nunique()),
                    **{k: m[k] for k in ("r2", "r2CiLow", "r2CiHigh", "mae", "rmse", "spearmanRho", "h1Verdict")},
                    "unseenCircuitMae": unseen.get((scope, target, regime)),
                }
            )
    result = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = reg["campaignId"]
    result.to_csv(out_dir / f"{stem}_scores.csv", index=False)

    lines = [
        f"# Prospective validation · `{stem}`",
        "",
        f"Predictions pre-registered at {reg['createdAt']} (commit `{reg['gitCommit']}`), "
        f"{len(reg['configurations'])} configurations on `{reg['backend']}`. "
        "Prepared records and frozen models were re-hashed before scoring and match.",
        "",
        "Pre-registered criteria: H1 uses the `new` group with circuit-only models (pass needs the "
        "95% CI above 0.80). `anchor` = known circuits, new calibration cycle (drift). "
        "`extrapolation` = larger than any measured circuit (H2).",
        "",
        "| Scope | Target | Regime | Group | Configs / jobs | R² [95% CI] | MAE | Unseen-circuit MAE | Verdict |",
        "|---|---|---|---|---:|---:|---:|---:|:---:|",
    ]
    fmt = lambda v, nd=3: "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{nd}f}"  # noqa: E731
    for r in result.sort_values(["scope", "regime", "target", "group"]).itertuples():
        ci = f" [{r.r2CiLow:.2f}, {r.r2CiHigh:.2f}]" if pd.notna(r.r2CiLow) else ""
        verdict = r.h1Verdict.upper() if r.group == "new" and r.regime == "circuit_only" else ""
        lines.append(
            f"| `{r.scope}` | {r.target} | {r.regime} | {r.group} | {r.configs} / {r.jobs} "
            f"| {fmt(r.r2)}{ci} | {fmt(r.mae, 4)} | {fmt(r.unseenCircuitMae, 4)} | {verdict} |"
        )
    report = out_dir / f"{stem}_report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def _unseen_circuit_mae() -> Dict[tuple, float]:
    """Unseen-circuit validation MAE of each frozen model, from the model manifest."""
    manifest = json.loads((models_dir() / "models_manifest.json").read_text(encoding="utf-8"))
    return {(m["scope"], m["target"], m["regime"]): m.get("cvMae") for m in manifest["models"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("predict", help="Pre-register predictions after prepare, before submit.")
    p.add_argument("--campaign", required=True, help="e.g. kingston-validation-v1-2026-11-17")
    p.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Testing only: allow uncommitted models/code (the result is not a valid pre-registration).",
    )
    s = sub.add_parser("score", help="Score committed predictions after recover + export-ibm.")
    s.add_argument("--predictions", type=Path, required=True)
    s.add_argument("--tables", type=Path, default=ROOT / "experiments" / "dataset_out")
    args = parser.parse_args()
    if args.command == "predict":
        print(predict(args.campaign, allow_dirty=args.allow_dirty))
    else:
        print(score(args.predictions, args.tables))


if __name__ == "__main__":
    main()
