"""Compare the saved QAQS models on the validation run, which none of them trained on.

    python -m experiments.qaqs_compare

Candidates, all circuit-only unless named otherwise:

* ``pooled_chip``   one model for all chips with a one-hot chip id (the best model)
* ``pooled``        one model for all chips, no chip id
* ``per_chip``      one model per chip; an unseen chip falls back to ``pooled`` (reference)
* ``mixed``         per-chip footprint + layout calibration (reference)
* ``size``          LightGBM on four size counts, trained per chip (baseline)
* ``registered``    predictions committed before the run by the models of that date

Scores are R^2 and MAE per chip on every validation job except the composite anchor,
plus paired differences against ``pooled_chip``. The run has been used to choose the
model, so these numbers describe the choice; they are not a pre-registered test of it.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from experiments.ml_dataset import (
    COMPOSITE_ANCHOR,
    TARGETS,
    add_chip_indicators,
    load_ml_dataset,
)
from experiments.qaqs_kfold import WAITING_FOR_DATA
from experiments.qaqs_models import (
    PROSPECTIVE_DIR,
    ROOT,
    SIZE_BASELINE_FEATURES,
    _clean_json,
    _fit_predict,
    build_models,
    evaluate_predictions,
)
from experiments.validation_profile import group_of

DEFAULT_TABLES = ROOT / "experiments" / "dataset_out"
DEFAULT_REPORT = ROOT / "report" / "ml_estimation"
DEFAULT_DASHBOARD = ROOT / "dashboard" / "experiments" / "comparison"
BEST = "pooled_chip"
LABELS = {
    "pooled_chip": "Pooled + chip id (best)",
    "pooled": "Pooled, no chip id",
    "per_chip": "Per-chip models (reference)",
    "mixed": "Per-chip + layout calibration",
    "size": "Size baseline (4 counts)",
    "registered": "Pre-registered 2026-11-16",
}


def _predict(models_dir: Path, scope: str, target: str, regime: str, rows: pd.DataFrame) -> np.ndarray | None:
    path = models_dir / f"{scope}_{target}_{regime}.joblib"
    if not path.is_file():
        return None
    bundle = joblib.load(path)
    X = add_chip_indicators(rows.copy(), bundle["features"])[bundle["features"]]
    return np.clip(np.asarray(bundle["pipeline"].predict(X), dtype=float), 0.0, 1.0)


def _registered(val: pd.DataFrame, target: str, trained: set[str]) -> np.ndarray:
    """Committed circuit-only predictions: own-chip model, pooled model for an unseen chip."""
    out = pd.Series(np.nan, index=val.index, dtype=float)
    for path in sorted(PROSPECTIVE_DIR.glob("*-validation-v*_predictions.json")):
        if not path.with_name(path.name.replace("_predictions.json", "_scores.csv")).is_file():
            continue
        reg = json.loads(path.read_text(encoding="utf-8"))
        chip = reg["backend"]
        scope = chip if chip in trained else "pooled"
        pred = {
            p["config_id"]: p["predicted"]
            for p in reg["predictions"]
            if p["target"] == target and p["regime"] == "circuit_only" and p["scope"] == scope
        }
        mask = val["meta.backend_name"] == chip
        out[mask] = val.loc[mask, "meta.config_id"].map(pred)
    return out.to_numpy()


def _paired(y, a, b, groups, chips, n_boot=1000, seed=11) -> dict[str, Any] | None:
    """Mean over chips of R2(a) - R2(b), resampling configurations."""
    ok = np.isfinite(a) & np.isfinite(b)
    y, a, b, groups, chips = y[ok], a[ok], b[ok], groups[ok], chips[ok]
    if len(y) < 12:
        return None

    def stat(idx):
        return float(np.mean([r2_score(y[m], a[m]) - r2_score(y[m], b[m]) for m in (idx[chips[idx] == c] for c in np.unique(chips[idx]))]))

    cfgs = np.unique(groups)
    members = {c: np.flatnonzero(groups == c) for c in cfgs}
    rng = np.random.default_rng(seed)
    draws = [stat(np.concatenate([members[c] for c in rng.choice(cfgs, len(cfgs))])) for _ in range(n_boot)]
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"diff": stat(np.arange(len(y))), "ciLow": float(lo), "ciHigh": float(hi)}


def compare(tables: Path = DEFAULT_TABLES, report_dir: Path = DEFAULT_REPORT) -> dict[str, Any]:
    warnings.simplefilter("ignore")
    models_dir = report_dir / "models"
    train = load_ml_dataset(tables).frame
    val = load_ml_dataset(tables, roles=["validation"]).frame
    scored = {p.name.split("_predictions")[0] for p in PROSPECTIVE_DIR.glob("*_predictions.json")
              if p.with_name(p.name.replace("_predictions.json", "_scores.csv")).is_file()}
    val = val[val["meta.campaign_id"].isin(scored) & (val["meta.algorithm"] != COMPOSITE_ANCHOR)].reset_index(drop=True)
    if val.empty:
        return {"status": WAITING_FOR_DATA, "rows": [], "contrasts": []}
    val["group"] = val["meta.config_id"].map(group_of())
    trained = set(train["meta.backend_name"].unique())
    chips = val["meta.backend_name"].to_numpy()
    groups = val["meta.config_id"].to_numpy()
    rows, contrasts, points = [], [], []
    for target, (col, label, _) in TARGETS.items():
        y = val[col].to_numpy(dtype=float)
        preds: dict[str, np.ndarray] = {k: np.full(len(val), np.nan) for k in LABELS}
        preds["registered"] = _registered(val, target, trained)
        for chip, sub in val.groupby("meta.backend_name"):
            own = chip if chip in trained else "pooled"
            for key, scope, regime in (
                ("pooled_chip", "pooled", "circuit_chip"),
                ("pooled", "pooled", "circuit_only"),
                ("per_chip", own, "circuit_only"),
                ("mixed", own, "mixed_submit"),
            ):
                p = _predict(models_dir, scope, target, regime, sub)
                if p is not None:
                    preds[key][sub.index] = p
            tr = train[train["meta.algorithm"] != COMPOSITE_ANCHOR]
            tr = tr if own == "pooled" else tr[tr["meta.backend_name"] == own]
            cols = [c for c in SIZE_BASELINE_FEATURES if c in tr.columns]
            preds["size"][sub.index] = _fit_predict(
                build_models(11)["LightGBM"], tr[cols], tr[col].to_numpy(dtype=float), sub[cols]
            )
        for key, p in preds.items():
            for chip in sorted(np.unique(chips)):
                for gname in ("all", "new", "anchor", "extrapolation"):
                    m = (chips == chip) & np.isfinite(p) & ((val["group"] == gname).to_numpy() if gname != "all" else True)
                    if m.sum() < 6:
                        continue
                    rows.append(
                        {"target": target, "model": key, "label": LABELS[key], "chip": chip,
                         "seenChip": chip in trained, "group": gname, "jobs": int(m.sum()),
                         "configs": int(len(np.unique(groups[m]))), **evaluate_predictions(y[m], p[m], groups[m])}
                    )
            if key != BEST:
                d = _paired(y, preds[BEST], p, groups, chips)
                if d:
                    contrasts.append({"target": target, "against": key, "label": LABELS[key], **d})
        best = preds[BEST]
        for i in np.flatnonzero(np.isfinite(best)):
            points.append({"target": target, "chip": chips[i], "config": groups[i], "group": val["group"].iloc[i],
                           "algorithm": val["meta.algorithm"].iloc[i], "observed": float(y[i]), "predicted": float(best[i])})
    return {
        "status": "ok",
        "best": BEST,
        "labels": LABELS,
        "jobs": int(len(val)),
        "chips": sorted(np.unique(chips).tolist()),
        "trainedChips": sorted(trained),
        "rows": rows,
        "contrasts": contrasts,
        "points": points,
    }


def write(result: dict[str, Any], report_dir: Path, dashboard_out: Path | None) -> Path:
    out = report_dir / "model_comparison.md"
    if result["status"] != "ok":
        out.write_text(f"# QAQS model comparison\n\n{WAITING_FOR_DATA}: no scored validation run.\n", encoding="utf-8")
        return out
    rows = pd.DataFrame(result["rows"])
    rows.to_csv(report_dir / "model_comparison.csv", index=False)
    lines = [
        "# QAQS model comparison on the validation run",
        "",
        f"{result['jobs']} validation jobs on {', '.join(f'`{c}`' for c in result['chips'])} "
        f"(composite anchor excluded). Trained chips: {', '.join(f'`{c}`' for c in result['trainedChips'])}; "
        "any other chip is unseen. No model here trained on these jobs.",
        "",
        "The run was used to choose the best model, so this table describes that choice. It is not a "
        "pre-registered test of it; the next pre-registered run is.",
        "",
    ]
    allg = rows[rows["group"] == "all"]
    for target in TARGETS:
        t = allg[allg["target"] == target]
        lines += [f"## `{target}` · R² [95% CI] (MAE), all validation circuits", "",
                  "| Model | " + " | ".join(f"`{c}`" for c in result["chips"]) + " |", "|---|" + "---:|" * len(result["chips"])]
        for key, label in LABELS.items():
            cells = []
            for chip in result["chips"]:
                r = t[(t["model"] == key) & (t["chip"] == chip)]
                cells.append("—" if r.empty else
                             f"{r.iloc[0]['r2']:.3f} [{r.iloc[0]['r2CiLow']:.2f}, {r.iloc[0]['r2CiHigh']:.2f}] ({r.iloc[0]['mae']:.3f})")
            lines.append(f"| {label} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Best model against each alternative", "",
              "Paired difference in R² (best minus alternative), mean over chips, bootstrap over configurations.", "",
              "| Target | Alternative | ΔR² [95% CI] | Reading |", "|---|---|---:|---|"]
    for c in result["contrasts"]:
        reading = "best is better" if c["ciLow"] > 0 else ("alternative is better" if c["ciHigh"] < 0 else "no difference shown")
        lines.append(f"| `{c['target']}` | {c['label']} | {c['diff']:+.3f} [{c['ciLow']:.2f}, {c['ciHigh']:.2f}] | {reading} |")
    lines.append("")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if dashboard_out is not None:
        dashboard_out.mkdir(parents=True, exist_ok=True)
        (dashboard_out / "validation-v1.json").write_text(
            json.dumps(_clean_json(result), separators=(",", ":"), allow_nan=False), encoding="utf-8"
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--dashboard-out", type=Path, default=DEFAULT_DASHBOARD)
    args = parser.parse_args()
    print(write(compare(args.tables, args.report_out), args.report_out, args.dashboard_out))


if __name__ == "__main__":
    main()
