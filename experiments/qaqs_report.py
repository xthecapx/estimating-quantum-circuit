"""Report writer for the QAQS evaluation: one ``report.md`` plus flat CSV tables.

Every table is derived from the scope snapshots produced by ``qaqs_kfold``; nothing is
recomputed here. Results that need data not yet exported are printed as
``WAITING FOR DATA``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from experiments.ml_dataset import CAMPAIGN_ROLES, COMPOSITE_ANCHOR
from experiments.qaqs_kfold import STABLE_SELECTION_FREQUENCY, WAITING_FOR_DATA
from experiments.qaqs_models import H1_R2_THRESHOLD, PROSPECTIVE_DIR, SCHEMA_VERSION, _clean_json

HEADLINE_TARGET = "success"


def _fmt(v: Any, nd: int = 3) -> str:
    return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.{nd}f}"


def _ci(m: Mapping[str, Any] | None, lo: str = "r2CiLow", hi: str = "r2CiHigh") -> str:
    if not m or m.get(lo) is None or m.get(hi) is None:
        return ""
    return f" [{m[lo]:.2f}, {m[hi]:.2f}]"


def _r2(m: Mapping[str, Any] | None, sd: bool = False) -> str:
    if not m or m.get("r2") is None:
        return "—"
    spread = f" ± {m['r2Sd']:.3f}" if sd and m.get("r2Sd") is not None else ""
    return f"{m['r2']:.3f}{spread}{_ci(m)}"


def _procedure(tdata: Mapping[str, Any]) -> dict[str, Any]:
    board = tdata.get("leaderboard") or []
    return board[0]["cv"] if board else {}


def _regime(tdata: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    return next((r for r in tdata["h3"]["regimes"] if r["regime"] == key), None)


# --------------------------------------------------------------------- flat rows


def collect_rows(snapshots: Mapping[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Flatten the snapshots into the CSV tables (one list of rows per file)."""
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scope, snap in snapshots.items():
        for tkey, t in snap["targets"].items():
            base = {"scope": scope, "target": tkey}
            proc, diag = _procedure(t), t.get("diagnostics") or {}
            gain = diag.get("footprintGainOverSize") or {}
            rows["h1_summary.csv"].append(
                {
                    **base,
                    "scored_jobs": t.get("scoredJobs"),
                    "headline_rule": diag.get("headlineRule"),
                    "r2": proc.get("r2"),
                    "r2_sd": proc.get("r2Sd"),
                    "r2_ci_low": proc.get("r2CiLow"),
                    "r2_ci_high": proc.get("r2CiHigh"),
                    "mae": proc.get("mae"),
                    "h1_verdict": proc.get("h1Verdict"),
                    "noise_ceiling_r2": (diag.get("noiseCeiling") or {}).get("looReplicateR2"),
                    "config_mean_r2": (diag.get("configMean") or {}).get("r2"),
                    "config_mean_r2_ci_low": (diag.get("configMean") or {}).get("r2CiLow"),
                    "config_mean_r2_ci_high": (diag.get("configMean") or {}).get("r2CiHigh"),
                    "size_baseline_r2": (diag.get("sizeBaseline") or {}).get("r2"),
                    "gain_over_size": gain.get("diff"),
                    "gain_over_size_ci_low": gain.get("ciLow"),
                    "gain_over_size_ci_high": gain.get("ciHigh"),
                    "floor_share": diag.get("floorShare"),
                    "deployed_model": t.get("bestModel"),
                    "footprint_size": t.get("footprintCount"),
                }
            )
            for name, sub in (diag.get("subsets") or {}).items():
                rows["h1_subsets.csv"].append(
                    {**base, "subset": name, "jobs": sub.get("jobs"), "configs": sub.get("configs"),
                     "r2": sub.get("r2"), "r2_ci_low": sub.get("r2CiLow"), "r2_ci_high": sub.get("r2CiHigh"),
                     "mae": sub.get("mae")}
                )
            for item in diag.get("perAlgorithm") or []:
                rows["per_algorithm.csv"].append({**base, **item})
            for regime, board in (
                ("circuit_only", t.get("leaderboard", [])),
                ("circuit_chip", t.get("chipLeaderboard", [])),
                ("mixed_submit", t.get("mixedLeaderboard", [])),
                ("analytical", t.get("baselines", [])),
            ):
                for entry in board:
                    cv = entry["cv"] or {}
                    rows["leaderboard.csv"].append(
                        {**base, "regime": regime, "model": entry["model"], "kind": entry["kind"],
                         "r2": cv.get("r2"), "r2_sd": cv.get("r2Sd"), "r2_ci_low": cv.get("r2CiLow"),
                         "r2_ci_high": cv.get("r2CiHigh"), "mae": cv.get("mae"), "rmse": cv.get("rmse"),
                         "spearman_rho": cv.get("spearmanRho"), "h1_verdict": cv.get("h1Verdict"),
                         "selection_counts": json.dumps(entry["selectionCounts"]) if entry.get("selectionCounts") else None}
                    )
            for item in t.get("footprint", []):
                rows["footprint.csv"].append({**base, **item})
            for ab in t.get("footprintAblation", []):
                rows["footprint_ablation.csv"].append(
                    {**base, "k": ab["k"], "selection_cv_r2": ab["cvR2"], "selection_cv_r2_se": ab.get("cvR2Se"),
                     "cv_mae": ab["cvMae"], "selected": ab["selected"], "features": ";".join(ab["features"])}
                )
            for item in t.get("h2", []):
                rows["h2_scalability.csv"].append({**base, **item})
            temporal = {r["regime"]: r for r in ((t["h3"].get("temporal") or {}).get("regimes") or [])}
            for item in t["h3"]["regimes"]:
                ho = (temporal.get(item["regime"]) or {}).get("holdout") or {}
                rows["h3_regimes.csv"].append(
                    {**base, "regime": item["regime"], "label": item["label"], "features": item["featureCount"],
                     "unseen_circuit_r2": item["cv"].get("r2"), "unseen_circuit_r2_sd": item["cv"].get("r2Sd"),
                     "unseen_circuit_mae": item["cv"].get("mae"), "calibration_cycle_r2": ho.get("r2"),
                     "calibration_cycle_r2_ci_low": ho.get("r2CiLow"), "calibration_cycle_r2_ci_high": ho.get("r2CiHigh"),
                     "calibration_cycle_mae": ho.get("mae")}
                )
            if scope == "pooled":
                for item in t["h3"].get("transferMatrix", []):
                    rows["h3_cross_chip_transfer.csv"].append({"target": tkey, **item})
                for item in (t["h3"].get("providerTransfer") or {}).get("rows", []):
                    rows["h3_provider_transfer.csv"].append({"target": tkey, **item})
            for item in t.get("h4", []):
                rows["h4_regimes.csv"].append(
                    {**base, **{k: v for k, v in item.items() if k not in ("byFamily", "r2PerDraw")},
                     **{f"{fam}_r2": (m or {}).get("r2") for fam, m in (item.get("byFamily") or {}).items()}}
                )
            for item in t.get("h4Contrasts", []):
                rows["h4_contrasts.csv"].append({**base, **item})
            for _, minfo in sorted(t.get("savedModels", {}).items()):
                rows["_models"].append(minfo)
    return rows


def stable_footprint(snapshots: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Features selected in >= 80% of folds, counted over scope x target."""
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "freq": [], "where": []})
    total = 0
    for scope, snap in snapshots.items():
        for tkey, t in snap["targets"].items():
            total += 1
            meta = {i["feature"]: i for i in t.get("footprint", [])}
            for row in t.get("stableFootprintFeatures", []):
                st = stats[row["feature"]]
                st["count"] += 1
                st["freq"].append(row["selectionFrequency"])
                st["where"].append(f"{scope}/{tkey}")
                st["category"] = (meta.get(row["feature"]) or {}).get("category", "")
                st["label"] = (meta.get(row["feature"]) or {}).get("label", row["feature"])
    out = [
        {"feature": f, "label": st.get("label", f), "category": st.get("category", ""),
         "stableIn": st["count"], "of": total, "meanSelectionFrequency": float(np.mean(st["freq"])),
         "where": st["where"]}
        for f, st in stats.items()
    ]
    return sorted(out, key=lambda r: (-r["stableIn"], -r["meanSelectionFrequency"], r["feature"]))


# ------------------------------------------------------------------------ report


def _section_h1(snapshots: Mapping[str, dict[str, Any]]) -> list[str]:
    out = [
        "## H1 · Does the footprint predict execution quality?",
        "",
        f"Unseen-circuit validation. PASS needs the whole 95% interval at or above {H1_R2_THRESHOLD:.2f}.",
        "",
        f"- **Scored jobs.** `{COMPOSITE_ANCHOR}` sits at its chance level, so telling it apart from the other "
        "algorithms earns R² without predicting anything. Raw targets are scored without it; "
        "`success_adj` (chance-corrected success) scores every job.",
        "- **Ceiling.** R² of predicting a job from the other repeats of the same circuit on the same chip. "
        "The footprint is identical across repeats, so no pre-runtime model can beat it at job level.",
        "- **Config-mean R².** Observed and predicted averaged over the repeats of a circuit: the score with "
        "repeat-to-repeat noise removed.",
        "- **Size baseline.** Same model class on four counts only (two-qubit gates, depth, width, "
        "measurements). **Gain** is footprint minus baseline, paired bootstrap over configurations.",
        "",
    ]
    for scope, snap in snapshots.items():
        out += [
            f"### `{scope}` · {snap['jobs']} jobs, {snap['split']['totalConfigs']} configurations",
            "",
            "| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |",
            "|---|---:|:---:|---:|---:|---:|---:|---:|",
        ]
        for tkey, t in snap["targets"].items():
            proc, d = _procedure(t), t.get("diagnostics") or {}
            gain = d.get("footprintGainOverSize")
            gain_s = f"{gain['diff']:+.3f}{_ci(gain, 'ciLow', 'ciHigh')}" if gain else "—"
            out.append(
                f"| {t['label']} (`{tkey}`) | {_r2(proc, sd=True)} | {str(proc.get('h1Verdict', 'inconclusive')).upper()} "
                f"| {_fmt(proc.get('mae'), 4)} | {_fmt((d.get('noiseCeiling') or {}).get('looReplicateR2'))} "
                f"| {_r2(d.get('configMean'))} | {_fmt((d.get('sizeBaseline') or {}).get('r2'))} | {gain_s} |"
            )
        for tkey, reason in (snap.get("skippedTargets") or {}).items():
            out.append(f"| `{tkey}` | {reason} | | | | | | |")
        out.append("")
    out += [
        "### What each group of circuits contributes",
        "",
        "R² of the same out-of-fold predictions on subsets. `all jobs` includes the composite anchor and is "
        "shown only to expose how much it inflates the score.",
        "",
        "| Scope | Target | Headline | Core 6 | Random volumetric | Composite anchor | All jobs |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for scope, snap in snapshots.items():
        for tkey, t in snap["targets"].items():
            sub = (t.get("diagnostics") or {}).get("subsets") or {}
            cells = " | ".join(
                _fmt((sub.get(k) or {}).get("r2"))
                for k in ("headline", "core", "randomControl", "compositeAnchor", "allJobs")
            )
            out.append(f"| `{scope}` | `{tkey}` | {cells} |")
    out += [
        "",
        f"### Per algorithm (`{HEADLINE_TARGET}`)",
        "",
        "R² inside one algorithm is a harder test: the spread to explain is only that algorithm's own.",
        "",
        "| Scope | Algorithm | Configs | Observed mean ± sd | R² [95% CI] | MAE | Ceiling |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for scope, snap in snapshots.items():
        t = snap["targets"].get(HEADLINE_TARGET)
        for row in ((t or {}).get("diagnostics") or {}).get("perAlgorithm") or []:
            out.append(
                f"| `{scope}` | {row['algorithm']} | {row['configs']} | {row['observedMean']:.2f} ± {row['observedSd']:.2f} "
                f"| {_r2(row)} | {_fmt(row.get('mae'), 4)} | {_fmt(row.get('ceiling'))} |"
            )
    out.append("")
    hurdle_rows = []
    for scope, snap in snapshots.items():
        for tkey, t in snap["targets"].items():
            h = _regime(t, "hurdle")
            if h:
                d = t.get("diagnostics") or {}
                hurdle_rows.append(
                    f"| `{scope}` | `{tkey}` | {d.get('floorShare', 0) * 100:.1f}% | {_fmt(_procedure(t).get('r2'))} "
                    f"| {_fmt(h['cv'].get('r2'))} | {_fmt(_procedure(t).get('mae'), 4)} | {_fmt(h['cv'].get('mae'), 4)} |"
                )
    if hurdle_rows:
        out += [
            "### Targets with a point mass at the floor",
            "",
            "Two-stage model (is the job above the floor, then how far) on the same footprint and folds.",
            "",
            "| Scope | Target | Jobs at floor | Procedure R² | Two-stage R² | Procedure MAE | Two-stage MAE |",
            "|---|---|---:|---:|---:|---:|---:|",
            *hurdle_rows,
            "",
        ]
    return out


def _section_h2(snapshots: Mapping[str, dict[str, Any]]) -> list[str]:
    out = [
        f"## H2 · Generalization to unseen configurations (`{HEADLINE_TARGET}`)",
        "",
        "The held-out circuits are larger than any trained one, or from an algorithm absent from training. "
        "Footprint chosen on each protocol's own training set. `M2 prior alone` is the analytical estimate "
        "(uses submit-time calibration) with nothing learned; `M2 prior + residual` adds a footprint model "
        "of its error. Read the pair together: the gap is what the footprint adds.",
        "",
        "| Scope | Protocol | Task | nTrain / nTest | R² [95% CI] | MAE |",
        "|---|---|---|---:|---:|---:|",
    ]
    for scope, snap in snapshots.items():
        for row in (snap["targets"].get(HEADLINE_TARGET) or {}).get("h2", []):
            out.append(
                f"| `{scope}` | {row['protocol']} | {row['task']} | {row['nTrain']} / {row['nTest']} "
                f"| {_r2(row)} | {_fmt(row.get('mae'), 4)} |"
            )
    out.append("")
    return out


def _section_h3(snapshots: Mapping[str, dict[str, Any]]) -> list[str]:
    out = [
        f"## H3 · Hardware context and transfer (`{HEADLINE_TARGET}`)",
        "",
        "Two kinds of calibration input. **Device** (`cal.*`): one value per calibration snapshot, blind to "
        "the circuit. **Layout** (`c.*`): calibration of the qubits the circuit was mapped to, so it also "
        "carries circuit size.",
        "",
        "Judge calibration regimes on the **calibration-cycle** column: there the test windows are new "
        "calibration cycles. In the unseen-circuit column train and test share windows, so any input that "
        "identifies the window helps; the `collection-window id` row is the control for that.",
        "",
        "| Scope | Regime | Features | Unseen-circuit R² ± sd | Calibration-cycle R² [95% CI] | Calibration-cycle MAE |",
        "|---|---|---:|---:|---:|---:|",
    ]
    notes = []
    for scope, snap in snapshots.items():
        t = snap["targets"].get(HEADLINE_TARGET)
        if not t:
            continue
        tinfo = t["h3"].get("temporal") or {}
        temporal = {r["regime"]: r for r in (tinfo.get("regimes") or [])}
        for reg in t["h3"]["regimes"]:
            ho = (temporal.get(reg["regime"]) or {}).get("holdout") or {}
            out.append(
                f"| `{scope}` | {reg['label']} | {reg['featureCount']} | {_r2(reg['cv'], sd=True).split(' [')[0]} "
                f"| {_r2(ho)} | {_fmt(ho.get('mae'), 4)} |"
            )
        if tinfo:
            order = tinfo.get("ordering") or {}
            notes.append(
                f"- `{scope}` calibration-cycle split: {tinfo['trainJobs']} training jobs "
                f"({tinfo.get('trainCalibrationSnapshots', '?')} calibration snapshots), {tinfo['holdoutJobs']} test jobs "
                f"({tinfo.get('holdoutCalibrationSnapshots', '?')} snapshots); "
                f"{tinfo['holdoutConfigsSeenInTrain']} of {tinfo['holdoutConfigs']} test configurations also trained; "
                f"strictly later than training: {'yes' if order.get('strict') else 'NO'}."
            )
    out += ["", *notes, ""]

    pooled = (snapshots.get("pooled") or {}).get("targets", {}).get(HEADLINE_TARGET)
    out += ["### Cross-chip transfer (zero-shot)", ""]
    matrix = (pooled or {}).get("h3", {}).get("transferMatrix") or []
    if matrix:
        out += [
            "Model trained on the source chip with the footprint chosen there, scored on every job of the "
            "target chip. Diagonal cells are within-chip grouped CV.",
            "",
            "| Source | Target | Regime | Same provider | R² [95% CI] | MAE |",
            "|---|---|---|:---:|---:|---:|",
        ]
        for c in matrix:
            if c["regime"] not in ("circuit_only", "hardware_only", "mixed_submit"):
                continue
            out.append(
                f"| `{c['sourceBackend']}` | `{c['targetBackend']}` | {c['regimeLabel']} "
                f"| {'no' if c['crossProvider'] else 'yes'} | {_r2(c)} | {_fmt(c.get('mae'), 4)} |"
            )
    else:
        out.append(f"{WAITING_FOR_DATA}: needs at least two chips.")
    out += ["", "### Cross-provider transfer (leave one provider out)", ""]
    pt = (pooled or {}).get("h3", {}).get("providerTransfer") or {}
    if pt.get("rows"):
        out += [
            "| Held-out provider | Trained on | Regime | nTrain / nTest | R² [95% CI] | MAE |",
            "|---|---|---|---:|---:|---:|",
        ]
        for r in pt["rows"]:
            out.append(
                f"| `{r['heldOutProvider']}` | {', '.join(r['trainProviders'])} | {r['label']} "
                f"| {r['nTrain']} / {r['nTest']} | {_r2(r)} | {_fmt(r.get('mae'), 4)} |"
            )
    else:
        provs = ", ".join(pt.get("providers") or []) or "one provider"
        out.append(f"{WAITING_FOR_DATA}: the export holds {provs} only.")
    out.append("")
    return out


def _section_h4(snapshots: Mapping[str, dict[str, Any]]) -> list[str]:
    out = [
        f"## H4 · Paradigm circuits vs random-volumetric circuits (`{HEADLINE_TARGET}`)",
        "",
        "Forward rows test on paradigm circuits, reverse rows on random-volumetric (RV) circuits; every "
        "test configuration is predicted once by a model that never saw it. `size-matched` trains on as "
        "many paradigm rows as there are RV rows.",
        "",
        "| Scope | Regime | nTrain | nTest | R² [95% CI] | MAE |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for scope, snap in snapshots.items():
        for row in (snap["targets"].get(HEADLINE_TARGET) or {}).get("h4", []):
            out.append(
                f"| `{scope}` | {row['label']} | {row['nTrain']} | {row['nTest']} | {_r2(row)} | {_fmt(row.get('mae'), 4)} |"
            )
    out += [
        "",
        "Two intervals that overlap do not show two regimes are equal, and two that do not overlap are not "
        "the test either. The comparison is the paired difference on the same test jobs:",
        "",
        "| Scope | Question | R²(a) − R²(b) [95% CI] | Verdict |",
        "|---|---|---:|---|",
    ]
    names = {"a_better": "first is better", "b_better": "second is better", "no_difference_shown": "no difference shown"}
    for scope, snap in snapshots.items():
        for c in (snap["targets"].get(HEADLINE_TARGET) or {}).get("h4Contrasts", []):
            out.append(
                f"| `{scope}` | {c['question']} (`{c['a']}` − `{c['b']}`) "
                f"| {c['diff']:+.3f}{_ci(c, 'ciLow', 'ciHigh')} | {names[c['verdict']]} |"
            )
    out.append("")
    return out


def _section_best(snapshots: Mapping[str, dict[str, Any]]) -> list[str]:
    """The model to use, against the per-chip reference models."""
    pooled = snapshots.get("pooled")
    if not pooled:
        return []
    out = [
        "## Best model: one pooled model with chip id",
        "",
        "One model for all chips: the circuit footprint plus a one-hot chip id. Per-chip models are the "
        "reference. Unseen-circuit R² ± sd [95% CI] of each tuned procedure:",
        "",
        "| Target | Pooled + chip id | H1 | Pooled, no chip id | Per-chip models (reference) |",
        "|---|---:|:---:|---:|---|",
    ]
    chips = [s for s in snapshots if s != "pooled" and not s.startswith("provider_")]
    for tkey, t in pooled["targets"].items():
        best = (t.get("chipLeaderboard") or [{}])[0].get("cv") or {}
        ref = ", ".join(
            f"`{c}` {_fmt(_procedure(snapshots[c]['targets'].get(tkey) or {}).get('r2'))}" for c in chips
        )
        out.append(
            f"| {t['label']} (`{tkey}`) | {_r2(best, sd=True)} | {str(best.get('h1Verdict', '—')).upper()} "
            f"| {_fmt(_procedure(t).get('r2'))} | {ref} |"
        )
    out += [
        "",
        "A chip without training data gets no chip id (all zeros) and is predicted from what the known "
        "chips share. Scores on the validation run are in `model_comparison.md`.",
        "",
    ]
    return out


def _section_footprint(snapshots: Mapping[str, dict[str, Any]], stable: list[dict[str, Any]]) -> list[str]:
    out = [
        "## The footprint",
        "",
        f"A feature belongs to the footprint only if the selection procedure picks it in at least "
        f"{STABLE_SELECTION_FREQUENCY:.0%} of the outer folds. Features chosen once on the full data but "
        "rarely inside folds are listed in `footprint.csv` with their selection frequency and are not part "
        "of the claim.",
        "",
        "| Feature | Category | Stable in (scope × target) | Mean selection frequency |",
        "|---|---|---:|---:|",
    ]
    for row in stable[:20]:
        out.append(
            f"| `{row['feature']}` | {row['category']} | {row['stableIn']} / {row['of']} | {row['meanSelectionFrequency']:.2f} |"
        )
    if not stable:
        out.append("| none reached the threshold | | | |")
    out += [
        "",
        "Footprint size is the smallest k whose selection score is within 0.0015 R² of the best k. The "
        "ablation R² in `footprint_ablation.csv` is a selection score, not accuracy.",
        "",
        "| Scope | Target | k deployed | k across folds (min–median–max) | Stable features |",
        "|---|---|---:|---:|---:|",
    ]
    for scope, snap in snapshots.items():
        for tkey, t in snap["targets"].items():
            fs = t.get("footprintSizeAcrossFolds", {})
            out.append(
                f"| `{scope}` | `{tkey}` | {t['footprintCount']} | {fs.get('min', '?')}–{fs.get('median', 0):.0f}–{fs.get('max', '?')} "
                f"| {len(t.get('stableFootprintFeatures', []))} |"
            )
    out.append("")
    return out


def _section_prospective() -> list[str]:
    out = ["## Prospective validation (run of 2026-11-16)", ""]
    path = PROSPECTIVE_DIR / "validation-v1_summary.csv"
    if not path.is_file():
        return out + [f"{WAITING_FOR_DATA}: no scored prospective run in `{PROSPECTIVE_DIR.name}/`.", ""]
    s = pd.read_csv(path)
    s = s[(s["target"] == HEADLINE_TARGET) & (s["regime"] == "circuit_only") & (s["group"] != "all")]
    out += [
        "Predictions were committed on 2026-11-16, before the run, by the models of that date (in git "
        "history). The models saved by this report were trained later and are compared on the same run "
        "in `model_comparison.md`; that comparison is not pre-registered. The H1 rule applies to the "
        "`new` group of every model scope; all scopes are listed, because which source chip transfers "
        "best to an unseen chip is not known beforehand.",
        "",
        "| Chip | QPU | Model scope | Group | Configs | R² [95% CI] | MAE |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for r in s.sort_values(["backend", "scope", "group"]).to_dict("records"):
        out.append(
            f"| `{r['backend']}` | {r['qpu']} | `{r['scope']}` | {r['group']} | {int(r['configs'])} "
            f"| {_r2(r)} | {_fmt(r.get('mae'), 4)} |"
        )
    out += ["", "`new` holds 13 configurations and `extrapolation` 9 per chip, so their intervals are wide.", ""]
    return out


def write_reports(
    snapshots: Mapping[str, dict[str, Any]],
    report_dir: Path,
    dataset: Mapping[str, Any] | None = None,
) -> None:
    """Write ``report.md``, the CSV tables, ``best_predictors.json`` and the model manifest."""
    report_dir.mkdir(parents=True, exist_ok=True)
    models_dir = report_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    rows = collect_rows(snapshots)
    stable = stable_footprint(snapshots)
    any_snap = next(iter(snapshots.values()))
    sp = any_snap["split"]
    dataset = dataset or {}

    lines = ["# QAQS quality-estimation report", ""]
    if dataset:
        roles = dataset.get("campaignRoles") or {}
        lines += [
            f"Dataset `{str(dataset.get('manifestHash', ''))[:12]}` · chips: {', '.join(dataset.get('chips', []))} "
            f"· providers: {', '.join(dataset.get('providers', []))}.",
            "",
            "| Campaign role | Jobs | Use |",
            "|---|---:|---|",
            f"| train | {roles.get('train', 0)} | everything in this report |",
            f"| validation | {roles.get('validation', 0)} | prospective validation only; never trained on |",
            f"| exploratory | {roles.get('exploratory', 0)} | one-off studies; never trained on |",
            "",
        ]
        assert set(roles) <= set(CAMPAIGN_ROLES)
    lines += [f"Scopes: {', '.join(f'`{s}`' for s in snapshots)}.", ""]
    lines += _section_best(snapshots)

    lines += [
        "## Verdicts",
        "",
        "| Scope | " + " | ".join(f"`{k}`" for k in any_snap["targets"]) + " |",
        "|---|" + "---|" * len(any_snap["targets"]),
    ]
    for scope, snap in snapshots.items():
        cells = []
        for tkey in any_snap["targets"]:
            proc = _procedure(snap["targets"].get(tkey) or {})
            cells.append(f"{str(proc.get('h1Verdict', '—')).upper()} ({_fmt(proc.get('r2'), 2)})" if proc else "—")
        lines.append(f"| `{scope}` | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Validation tests",
        "",
        "| Test | Question | Method |",
        "|---|---|---|",
        "| **Unseen-circuit validation** | Does QAQS predict circuits it has never seen? "
        f"| Repeated grouped K-fold by circuit configuration ({sp['nSplits']} folds × {sp['nRepeats']} repeats, "
        f"{sp['totalConfigs']} configurations, folds shared across chips). Footprint selection, tuning and "
        "model choice happen inside each training fold. |",
        "| **Calibration-cycle validation** | Does QAQS predict a later calibration cycle? "
        "| Per chip: train on the earlier collection windows, test on the latest ones (mostly the same circuits). |",
        "| **Prospective validation** | Does QAQS predict a run that did not exist at training time? "
        "| Frozen models, predictions committed before the results exist. |",
        "",
        "R² is the mean over repeats ± sd between repeats; intervals are 95% cluster bootstraps that "
        "resample configurations.",
        "",
    ]
    lines += _section_h1(snapshots)
    lines += _section_h2(snapshots)
    lines += _section_h3(snapshots)
    lines += _section_h4(snapshots)
    lines += _section_footprint(snapshots, stable)
    lines += _section_prospective()

    if rows["_models"]:
        lines += [
            "## Saved models",
            "",
            "Fitted on every training-role job with the procedure scored above. `circuit_chip` in the pooled "
            "scope is the best model; per-chip models are kept as reference.",
            "",
            "| Scope | Target | Regime | Model | Features | Procedure R² | MAE | Artifact |",
            "|---|---|---|---|---:|---:|---:|---|",
        ]
        for m in rows["_models"]:
            lines.append(
                f"| `{m['scope']}` | `{m['target']}` | `{m['regime']}` | {m['model']} | {m['featureCount']} "
                f"| {_fmt(m.get('r2'))} | {_fmt(m.get('mae'), 4)} | `{m['path']}` |"
            )
        lines.append("")

    for name, data in rows.items():
        if not name.startswith("_"):
            pd.DataFrame(data).to_csv(report_dir / name, index=False)
    by_scope_target = {
        scope: {
            tkey: {
                "circuit_only": t.get("selectedFootprintFeatures", []),
                "stable": [r["feature"] for r in t.get("stableFootprintFeatures", [])],
                "layout_calibration": t.get("selectedHardwareFeatures", []),
                "device_calibration": t.get("selectedDeviceFeatures", []),
            }
            for tkey, t in snap["targets"].items()
        }
        for scope, snap in snapshots.items()
    }
    (report_dir / "best_predictors.json").write_text(
        json.dumps(
            _clean_json(
                {
                    "schemaVersion": SCHEMA_VERSION,
                    "stableSelectionFrequency": STABLE_SELECTION_FREQUENCY,
                    "stableFootprint": stable,
                    "byScopeTarget": by_scope_target,
                }
            ),
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    (models_dir / "models_manifest.json").write_text(
        json.dumps(
            _clean_json(
                {
                    "schemaVersion": SCHEMA_VERSION,
                    "models": rows["_models"],
                }
            ),
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    (report_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
