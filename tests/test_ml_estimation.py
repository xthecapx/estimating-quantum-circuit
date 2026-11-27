"""Tests for provider-agnostic QAQS ML estimation, footprint curation, and dashboard bundling."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from experiments.footprint_analysis import (
    compute_feature_contributions,
    curate_footprint_vif,
    select_best_footprint,
)
from experiments.ml_dataset import infer_provider, load_ml_dataset, split_temporal_and_cv
from experiments.ml_estimation import build_models, build_scopes, run_pipeline


def _synthetic_multichip_tables(tmp_path: Path) -> Path:
    rng = np.random.default_rng(7)
    rows = []
    algos = [
        "QFT",
        "PHASE-ESTIMATION",
        "GROVER",
        "BERNSTEIN-VAZIRANI",
        "VTP",
        "GHZ",
        "RANDOM-VOLUMETRIC",
        "SHOR",
    ]
    # Three providers; each chip has two collection windows under different calibrations.
    chips = [
        ("ibm_fez", "w0", "2026-11-01T10:00:00Z"),
        ("ibm_fez", "w1", "2026-11-05T10:00:00Z"),
        ("ankaa_3", "rigetti-w0", "2026-11-08T10:00:00Z"),
        ("ankaa_3", "rigetti-w1", "2026-11-10T10:00:00Z"),
        ("ionq_aria", "ionq-w0", "2026-11-11T10:00:00Z"),
        ("ionq_aria", "ionq-w1", "2026-11-12T10:00:00Z"),
    ]
    idx = 0
    for backend, campaign, ts in chips:
        for algo in algos:
            for size in (3, 5, 7, 9):
                depth = size * 8 + int(rng.integers(0, 12))
                g2 = size * 3 + int(rng.integers(0, 8))
                if algo == "SHOR":  # the composite anchor is far larger than the core circuits
                    depth, g2 = depth * 8, g2 * 8
                comm = float(rng.uniform(0.1, 0.95))
                n_single = int(rng.integers(5, 45))
                noise_base = 0.015 if "ibm" in backend else (0.025 if "ankaa" in backend else 0.008)
                noise_base *= 1.0 if campaign.endswith("0") else 1.15  # the later window is noisier
                chance = 0.25 if algo == "SHOR" else 0.02
                dsr = float(np.clip(np.exp(-noise_base * g2) - 0.1 * comm + rng.normal(0, 0.02), 0.02, 0.99))
                hf = float(np.clip(dsr * 0.95 + 0.03, 0.02, 0.99))
                tvd = float(np.clip(1.0 - hf + rng.normal(0, 0.01), 0.01, 0.98))
                succ = float(np.clip(dsr * 0.9 + 0.05, 0.01, 0.99))
                if algo == "SHOR":  # the composite anchor sits at its chance level
                    succ, dsr = float(np.clip(chance + rng.normal(0, 0.01), 0.0, 1.0)), 0.0
                rows.append(
                    {
                        "meta.backend_name": backend,
                        "meta.campaign_id": campaign,
                        "meta.window": 0 if campaign.endswith("0") else 1,
                        "meta.algorithm": algo,
                        "meta.config_id": f"{algo[:3]}-{size}",
                        "meta.job_id": f"job-{idx}",
                        "meta.run_id": f"run-{idx}",
                        "meta.run_index": 0,
                        "meta.shots": 1024,
                        "a.num_qubits": size,
                        "a.num_clbits": size,
                        "a.depth": depth,
                        "a.size": depth * 2,
                        "a.ComplexityMetrics.gate_based_metrics.two_qubit_count": g2,
                        "a.StructuralMetrics.volume": size * depth,
                        "a.BehavioralMetrics.program_communication": comm,
                        "a.ElementMetrics.no_gates": depth * 2 + n_single,
                        "a.quantum_specific.available": size <= 8,
                        "a.quantum_specific.coherence": float(rng.uniform(0.1, 0.9)) if size <= 8 else np.nan,
                        "b.active_qubits": size,
                        "b.depth": depth + 4,
                        "b.size": (depth + 4) * 2,
                        "b.two_qubit_depth": g2 // 2,
                        "b.two_qubit_gates": g2,
                        "b.BehavioralMetrics.measurement": size,
                        "c.calibrated_at": ts,
                        "c.two_qubit_gate_error.median": noise_base * (1 + 0.02 * size),
                        "c.readout_error.median": noise_base * 1.1,
                        "c.t1_us.median": 120.0 if "ionq" not in backend else 100000.0,
                        "c.t2_us.median": 85.0 if "ionq" not in backend else 50000.0,
                        "d.two_qubit_gate_error.median": noise_base * 1.05,
                        "d.readout_error.median": noise_base * 1.1,
                        "d.t1_us.median": 118.0 if "ionq" not in backend else 100000.0,
                        "d.t2_us.median": 84.0 if "ionq" not in backend else 50000.0,
                        "d.changed_since_prepare": bool(idx % 3 == 0),
                        "e.m1_error": float(np.clip(1.0 - succ + 0.04, 0, 1)),
                        "e.m1_mixture_error": float(np.clip(1.0 - succ + 0.03, 0, 1)),
                        "e.m2_error": float(np.clip(1.0 - succ + 0.02, 0, 1)),
                        "e.m1_tvd": float(np.clip(tvd + 0.05, 0, 1)),
                        "e.m1_mixture_tvd": float(np.clip(tvd + 0.04, 0, 1)),
                        "e.m2_tvd": float(np.clip(tvd + 0.02, 0, 1)),
                        "f.fidelity.dsr": dsr,
                        "f.fidelity.hellinger_fidelity": hf,
                        "f.fidelity.tvd": tvd,
                        "f.fidelity.success_rate": succ,
                        "f.fidelity.chance_baseline": chance,
                        "f.fidelity.chance_corrected_success": float(max(0.0, (succ - chance) / (1 - chance))),
                        "g.finished_at": ts,
                    }
                )
                idx += 1

    tables = tmp_path / "tables"
    tables.mkdir(parents=True)
    df = pd.DataFrame(rows)
    part_path = tables / "dataset-000.csv"
    df.to_csv(part_path, index=False)
    manifest = {
        "schema_version": "1.0",
        "rows": len(df),
        "parts": [{"file": "dataset-000.csv", "rows": len(df), "bytes": part_path.stat().st_size}],
    }
    (tables / "dataset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tables


def test_provider_inference_supports_ibm_rigetti_ionq() -> None:
    assert infer_provider("ibm_fez") == ("ibm", "superconducting")
    assert infer_provider("ibm_kingston") == ("ibm", "superconducting")
    assert infer_provider("ankaa_3") == ("rigetti", "superconducting")
    assert infer_provider("ionq_aria") == ("ionq", "trapped_ion")
    assert infer_provider("forte_enterprise") == ("ionq", "trapped_ion")
    assert infer_provider("custom_qpu", explicit_provider="ionq") == ("ionq", "trapped_ion")


def test_combined_training_respects_braket_split_and_provenance(tmp_path: Path) -> None:
    tables = _synthetic_multichip_tables(tmp_path)
    base = load_ml_dataset(tables)
    part = Path("braket-repetitions-v1/dataset.csv")
    (tables / part.parent).mkdir()
    jobs = base.frame.iloc[:4].copy()
    jobs["meta.provider"] = "ionq"
    jobs["meta.backend_name"] = "Forte-1"
    jobs["meta.campaign_id"] = "ionq-development-v1"
    jobs["meta.job_id"] = ["train-job", "test-job", "validation-job", "pilot-job"]
    jobs["meta.split"] = ["train", "test", "validation", "pilot"]
    jobs.to_csv(tables / part, index=False)

    combined = load_ml_dataset(tables, include_braket_training=True)
    assert len(combined.frame) == len(base.frame) + 1
    assert combined.frame.loc[combined.frame["meta.backend_name"] == "Forte-1", "meta.job_id"].tolist() == ["train-job"]
    assert set(combined.frame["meta.provider"]) == {"ibm", "rigetti", "ionq"}
    assert combined.inputs == {**base.inputs, str(part): hashlib.sha256((tables / part).read_bytes()).hexdigest()}


def test_multichip_loader_vif_and_end_to_end_pipeline(tmp_path: Path) -> None:
    """The whole pipeline runs on three providers with no chip or provider named in code."""
    tables = _synthetic_multichip_tables(tmp_path)
    bundle = load_ml_dataset(tables)
    assert set(bundle.frame["meta.provider"].unique()) == {"ibm", "rigetti", "ionq"}
    assert "a.quantum_specific_present" in bundle.circuit_features
    assert "c.two_qubit_gate_error.median" in bundle.hardware_submit_features
    assert "cal.two_qubit_gate_error" in bundle.device_calibration_features
    # device calibration is one value per calibration snapshot: blind to the circuit
    per_snapshot = bundle.frame.groupby("meta.calibration_snapshot")["cal.two_qubit_gate_error"].nunique()
    assert (per_snapshot == 1).all()
    assert bundle.frame.groupby("meta.calibration_snapshot")["c.two_qubit_gate_error.median"].nunique().max() > 1

    is_holdout, periods = split_temporal_and_cv(bundle.frame)
    assert is_holdout.any() and periods
    for _, sub in bundle.frame.groupby("meta.backend_name"):
        held = is_holdout.loc[sub.index]
        assert held.any() and not held.all()  # every chip: latest window held out, earliest trains
        assert sub.loc[held, "g.finished_at"].min() > sub.loc[~held, "g.finished_at"].max()

    selected, stats_df = curate_footprint_vif(
        bundle.frame, bundle.circuit_features, "f.fidelity.dsr", max_vif=10.0, max_features=8
    )
    assert 3 <= len(selected) <= 8
    selected_vifs = stats_df.loc[stats_df["selected"], "vif"].dropna()
    assert (selected_vifs <= 10.05).all()

    xgb = build_models()["XGBoost"]
    xgb.fit(bundle.frame[selected], bundle.frame["f.fidelity.dsr"].to_numpy())
    vif_map = dict(zip(stats_df["feature"], stats_df["vif"]))
    contrib = compute_feature_contributions(
        xgb, bundle.frame, bundle.frame["f.fidelity.dsr"], selected, stats_df, vif_map
    )
    assert len(contrib) == len(selected)
    assert all("shapMeanAbs" in r and "permutationImportance" in r for r in contrib)

    assert [name for name, _ in build_scopes(bundle.frame)] == ["ankaa_3", "ibm_fez", "ionq_aria", "pooled"]

    report_out = tmp_path / "reports"
    dash_out = tmp_path / "dash_est"
    snapshots = run_pipeline(tables=tables, report_out=report_out, dashboard_out=dash_out, n_repeats=1, n_jobs=1)
    assert set(snapshots) == {"ibm_fez", "ankaa_3", "ionq_aria", "pooled"}
    pooled = snapshots["pooled"]
    assert set(pooled["providersIncluded"]) == {"ibm", "rigetti", "ionq"}
    assert snapshots["ankaa_3"]["provider"] == "rigetti" and snapshots["ionq_aria"]["modality"] == "trapped_ion"
    assert set(pooled["targets"]) == {"dsr", "hellinger", "tvd", "success", "success_adj"}

    success = pooled["targets"]["success"]
    xfer = success["h3"]["transferMatrix"]
    pairs = {(c["sourceProvider"], c["targetProvider"]) for c in xfer}
    assert ("ibm", "rigetti") in pairs and ("ibm", "ionq") in pairs
    # leave-one-provider-out runs as soon as a second provider is in the export
    lopo = success["h3"]["providerTransfer"]
    assert lopo["status"] == "ok"
    assert {r["heldOutProvider"] for r in lopo["rows"]} == {"ibm", "rigetti", "ionq"}
    assert all(r["heldOutProvider"] not in r["trainProviders"] for r in lopo["rows"])

    # the composite anchor is scored apart from the headline on raw targets, with it on success_adj
    assert success["scoredJobs"] < pooled["targets"]["success_adj"]["scoredJobs"] == pooled["jobs"]
    diag = success["diagnostics"]
    assert {"headline", "core", "compositeAnchor", "allJobs"} <= set(diag["subsets"])
    assert diag["sizeBaseline"]["r2"] is not None
    assert {r["algorithm"] for r in diag["perAlgorithm"]} >= {"QFT", "SHOR"}
    regimes = {r["regime"] for r in success["h3"]["regimes"]}
    assert {"circuit_only", "size_baseline", "hardware_only", "layout_only", "mixed_submit", "circuit_chip"} <= regimes
    chip = snapshots["ibm_fez"]["targets"]["success"]
    assert chip["h3"]["temporal"]["ordering"]["strict"] is True
    cycle = {r["regime"] for r in chip["h3"]["temporal"]["regimes"]}
    assert cycle >= {"circuit_only", "layout_only", "mixed_submit", "size_baseline"}
    # one training snapshot: device calibration is constant there, so that regime cannot be fitted
    assert chip["h3"]["temporal"]["trainCalibrationSnapshots"] == 1 and "hardware_only" not in cycle
    assert {"forward", "reverse"} == {r["direction"] for r in success["h4"]}
    assert all({"diff", "ciLow", "ciHigh", "verdict"} <= set(c) for c in success["h4Contrasts"])

    for name in ("report.md", "best_predictors.json", "h1_summary.csv", "per_algorithm.csv", "h3_regimes.csv",
                 "h3_provider_transfer.csv", "h4_contrasts.csv", "footprint_ablation.csv"):
        assert (report_out / name).is_file(), name
    text = (report_out / "report.md").read_text(encoding="utf-8")
    assert "Cross-provider transfer" in text and "Gain over size" in text
    manifest = json.loads((report_out / "models" / "models_manifest.json").read_text(encoding="utf-8"))
    assert {m["regime"] for m in manifest["models"]} == {"circuit_only", "mixed_submit", "circuit_chip"}
    assert success["modelRoles"] == {"circuit_only": "unseen_chip_fallback", "circuit_chip": "candidate"}
    assert chip["modelRoles"] == {"circuit_only": "best"}
    best = joblib.load(report_out / success["savedModels"]["circuit_chip"]["path"])
    assert [c for c in best["features"] if c.startswith("chip.")] == ["chip.ankaa_3", "chip.ibm_fez", "chip.ionq_aria"]
    assert "stableFootprint" in json.loads((report_out / "best_predictors.json").read_text(encoding="utf-8"))

    dsr_target = pooled["targets"]["dsr"]
    assert "circuit_only" in dsr_target["savedModels"] and "mixed_submit" in dsr_target["savedModels"]
    saved_bundle = joblib.load(report_out / dsr_target["savedModels"]["circuit_only"]["path"])
    preds = np.clip(saved_bundle["pipeline"].predict(bundle.frame[saved_bundle["features"]].head(10)), 0.0, 1.0)
    assert preds.shape == (10,)
    assert np.all(np.isfinite(preds)) and np.all((preds >= 0.0) & (preds <= 1.0))
    assert (dash_out / "pooled.json").is_file()


def test_single_provider_marks_provider_transfer_as_waiting_for_data(tmp_path: Path) -> None:
    from experiments.qaqs_kfold import WAITING_FOR_DATA, provider_transfer

    tables = _synthetic_multichip_tables(tmp_path)
    bundle = load_ml_dataset(tables, backends=["ibm_fez"])
    out = provider_transfer(bundle, "success")
    assert out == {"status": WAITING_FOR_DATA, "providers": ["ibm"], "rows": []}


def test_provider_specific_inputs_are_skipped_not_fatal(tmp_path: Path) -> None:
    """A provider without analytical baselines, chance levels or calibration still evaluates."""
    from experiments.qaqs_kfold import WAITING_FOR_DATA, analyze_scope_kfold, assign_config_folds

    tables = _synthetic_multichip_tables(tmp_path)
    csv = tables / "dataset-000.csv"
    frame = pd.read_csv(csv)
    frame = frame[frame["meta.backend_name"] == "ionq_aria"]
    drop = [c for c in frame.columns if c.startswith(("c.", "d.", "e.")) or "chance" in c]
    frame.drop(columns=drop).to_csv(csv, index=False)
    manifest = json.loads((tables / "dataset_manifest.json").read_text())
    for part in manifest["parts"]:
        part.pop("bytes", None)
        part.pop("rows", None)
    (tables / "dataset_manifest.json").write_text(json.dumps(manifest))
    bundle = load_ml_dataset(tables)
    assert bundle.hardware_submit_features == [] and bundle.device_calibration_features == []
    folds = assign_config_folds(bundle.frame, n_splits=4, n_repeats=1, seed=3)
    snap = analyze_scope_kfold(bundle, "ionq_aria", bundle.frame, folds, n_jobs=1)
    assert snap["skippedTargets"]["success_adj"].startswith(WAITING_FOR_DATA)
    success = snap["targets"]["success"]
    assert success["leaderboard"][0]["cv"]["r2"] is not None
    assert {r["regime"] for r in success["h3"]["regimes"]} == {"circuit_only", "size_baseline", "circuit_window"}
    assert success["baselines"] == [] and success["selectedHardwareFeatures"] == []
    assert all(r["variant"] == "footprint" for r in success["h2"])


def test_select_best_footprint_prunes_noise_and_runs_ablation(tmp_path: Path) -> None:
    tables = _synthetic_multichip_tables(tmp_path)
    bundle = load_ml_dataset(tables)
    df = bundle.frame.copy()
    rng = np.random.default_rng(123)
    df["a.synthetic_pure_noise"] = rng.normal(size=len(df))
    candidates = bundle.circuit_features + ["a.synthetic_pure_noise"]
    models = build_models(random_state=11)

    best_feats, items, ablation = select_best_footprint(
        df,
        df,
        candidates,
        "f.fidelity.dsr",
        contrib_model=models["XGBoost"],
        ablation_model=models["LightGBM"],
        groups=df["meta.config_id"],
        min_features=3,
        max_selected=6,
    )
    assert 3 <= len(best_feats) <= 6
    # The ranking puts real signal first. The size rule (tolerance on a noisy CV score)
    # may still admit a noise-level feature at the tail, which is why the report only
    # claims features selected in >= 80% of folds.
    assert "a.synthetic_pure_noise" not in best_feats[:3]
    assert best_feats[0] == "b.two_qubit_depth"
    assert any(item["selected"] for item in items)
    assert all("rank" in item and "selected" in item for item in items)
    assert ablation and any(row["selected"] for row in ablation)


def test_dashboard_build_validates_estimation_snapshots(tmp_path: Path) -> None:
    build_path = Path(__file__).resolve().parents[1] / "dashboard" / "build.py"
    spec = importlib.util.spec_from_file_location("dashboard_build", build_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    tables = _synthetic_multichip_tables(tmp_path)
    manifest_bytes = (tables / "dataset_manifest.json").read_bytes()
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    part_digest = hashlib.sha256((tables / "dataset-000.csv").read_bytes()).hexdigest()

    est_dir = mod.PROJECT / "experiments" / "estimation"
    # Only verify helper hash matching cleanly against temporary estimation snapshot dir
    temp_snap_dir = tmp_path / "snap"
    temp_snap_dir.mkdir()
    snap_file = temp_snap_dir / "mock.json"
    snap_file.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "backend": "ankaa_3",
                "manifestHash": digest,
                "inputs": {"dataset-000.csv": part_digest},
                "targets": {},
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "public_data"
    out_dir.mkdir()
    old_project = mod.PROJECT
    try:
        mock_proj = tmp_path / "proj"
        (mock_proj / "experiments" / "estimation").mkdir(parents=True)
        (mock_proj / "experiments" / "estimation" / "mock.json").write_text(
            snap_file.read_text(encoding="utf-8"), encoding="utf-8"
        )
        mod.PROJECT = mock_proj
        reports = mod._collect_validated_reports(
            "experiments/estimation", "estimation", tables, out_dir, digest
        )
        assert "ankaa_3" in reports
        assert (out_dir / reports["ankaa_3"]).is_file()
    finally:
        mod.PROJECT = old_project


def test_footprint_selection_ignores_holdout_labels() -> None:
    """Selection must not change when holdout targets are scrambled (no label leakage)."""
    rng = np.random.default_rng(5)
    n = 160
    X = pd.DataFrame({f"a.f{i}": rng.normal(size=n) for i in range(6)})
    X["b.signal"] = rng.normal(size=n)
    y = np.clip(0.5 + 0.3 * X["b.signal"].to_numpy() + rng.normal(0, 0.05, n), 0, 1)
    df = X.assign(y=y, cfg=[f"c{i % 40}" for i in range(n)])
    train, hold = df.iloc[:110].copy(), df.iloc[110:].copy()
    models = build_models(random_state=11)
    kwargs = dict(
        contrib_model=models["XGBoost"],
        ablation_model=models["LightGBM"],
        groups=train["cfg"],
        min_features=2,
        max_selected=4,
    )
    cols = list(X.columns)
    a, _, _ = select_best_footprint(train, hold, cols, "y", **kwargs)
    scrambled = hold.copy()
    scrambled["y"] = rng.permutation(scrambled["y"].to_numpy())
    b, _, _ = select_best_footprint(train, scrambled, cols, "y", **kwargs)
    assert a == b


def test_h1_verdict_requires_ci_to_clear_threshold() -> None:
    from experiments.qaqs_models import h1_verdict

    assert h1_verdict(0.85, (0.82, 0.88)) == "pass"
    assert h1_verdict(0.81, (0.70, 0.90)) == "inconclusive"
    assert h1_verdict(0.60, (0.50, 0.70)) == "fail"
    assert h1_verdict(None, None) == "inconclusive"


def test_hardware_regime_excludes_circuit_dependent_columns() -> None:
    from experiments.qaqs_models import _is_device_only_hw

    for col in ("c.num_used_qubits", "c.duration_s", "c.calibration_coverage", "c.idle_over_t1.median"):
        assert not _is_device_only_hw(col)
    for col in ("c.t1_us.median", "c.two_qubit_gate_error.median", "c.readout_error.median"):
        assert _is_device_only_hw(col)
    assert not _is_device_only_hw("cal.idle_over_t1")  # idle time is a property of the circuit


def test_chip_indicators_are_one_hot_and_zero_for_an_unknown_chip() -> None:
    from experiments.ml_dataset import add_chip_indicators, chip_indicator_columns

    train = pd.DataFrame({"meta.backend_name": ["a", "b", "a"]})
    cols = chip_indicator_columns(train)
    assert cols == ["chip.a", "chip.b"]
    assert add_chip_indicators(train, cols)[cols].to_numpy().tolist() == [[1, 0], [0, 1], [1, 0]]
    new = add_chip_indicators(pd.DataFrame({"meta.backend_name": ["c"]}), cols)
    assert new[cols].to_numpy().tolist() == [[0, 0]]


def test_campaign_roles_keep_exploratory_and_validation_out_of_training() -> None:
    from experiments.ml_dataset import campaign_role

    assert campaign_role("kingston-full-oracle-growth-v1-2026-11-11") == "train"
    assert campaign_role("marrakesh-validation-v1-2026-11-16") == "validation"
    assert campaign_role("fez-ghz-bv-transfer-v1-2026-11-23") == "exploratory"
    assert campaign_role("ankaa-3-dataset-v1-2027-01-10") == "train"  # a new provider needs no entry

    root = Path(__file__).resolve().parents[1]
    tables = root / "experiments" / "dataset_out"
    train = load_ml_dataset(tables).frame
    assert set(train["meta.campaign_role"]) == {"train"}
    everything = load_ml_dataset(tables, include_validation=True).frame
    assert set(everything["meta.campaign_role"]) == {"train", "validation", "exploratory"}
    assert len(load_ml_dataset(tables, roles=["exploratory"]).frame) == 20
    # with the exploratory window out of training, the calibration-cycle split is temporal again
    from experiments.ml_dataset import temporal_ordering

    for _, sub in train.groupby("meta.backend_name"):
        held, _ = split_temporal_and_cv(sub)
        assert temporal_ordering(sub, held)["strict"] is True


def test_footprint_size_stays_within_tolerance_of_the_best() -> None:
    """The chosen footprint is the smallest one within the tolerance of the best score."""
    rng = np.random.default_rng(3)
    n = 240
    X = pd.DataFrame({"b.signal": rng.normal(size=n), "b.weak": rng.normal(size=n), "a.noise": rng.normal(size=n)})
    y = np.clip(0.5 + 0.25 * X["b.signal"] + 0.004 * X["b.weak"] + rng.normal(0, 0.06, n), 0, 1)
    df = X.assign(y=y, cfg=[f"c{i % 60}" for i in range(n)])
    models = build_models(random_state=11)
    feats, _, curve = select_best_footprint(
        df, df.iloc[0:0], list(X.columns), "y", contrib_model=models["XGBoost"],
        ablation_model=models["LightGBM"], groups=df["cfg"], min_features=1, max_selected=3,
    )
    assert feats[0] == "b.signal"
    chosen = next(r for r in curve if r["selected"])
    best = max((r for r in curve if r["cvR2"] is not None), key=lambda r: r["cvR2"])
    assert chosen["k"] <= best["k"]
    assert chosen["cvR2"] >= best["cvR2"] - 0.0015 and "cvR2Se" in chosen


def test_paired_bootstrap_separates_a_real_gain_from_noise() -> None:
    from experiments.qaqs_models import cluster_bootstrap_r2_diff

    rng = np.random.default_rng(1)
    y = rng.uniform(0, 1, 300)
    groups = np.repeat(np.arange(60), 5)
    good, bad = y + rng.normal(0, 0.05, 300), y + rng.normal(0, 0.25, 300)
    twin = good + rng.normal(0, 0.002, 300)
    gain = cluster_bootstrap_r2_diff(y, good, bad, groups)
    assert gain["ciLow"] > 0 and gain["diff"] > 0
    same = cluster_bootstrap_r2_diff(y, good, twin, groups)
    assert same["ciLow"] < 0 < same["ciHigh"]


def test_noise_ceiling_is_the_replicate_agreement() -> None:
    from experiments.qaqs_kfold import noise_ceiling

    rng = np.random.default_rng(2)
    level = np.repeat(rng.uniform(0.1, 0.9, 50), 6)
    frame = pd.DataFrame({"meta.backend_name": "chip", "meta.config_id": np.repeat(np.arange(50), 6)})
    frame["quiet"] = level + rng.normal(0, 0.01, 300)
    frame["noisy"] = level + rng.normal(0, 0.20, 300)
    assert noise_ceiling(frame, "quiet")["looReplicateR2"] > 0.98
    assert noise_ceiling(frame, "noisy")["looReplicateR2"] < 0.6


def test_hurdle_model_handles_a_floor_point_mass() -> None:
    from experiments.qaqs_models import build_hurdle

    rng = np.random.default_rng(4)
    x = rng.uniform(0, 1, 400)
    y = np.where(x < 0.3, 0.0, np.clip(x + rng.normal(0, 0.03, 400), 0, 1))
    X = pd.DataFrame({"x": x, "z": rng.normal(size=400)})
    pred = build_hurdle().fit(X.iloc[:300], y[:300]).predict(X.iloc[300:])
    assert np.abs(pred[x[300:] < 0.25]).max() < 0.1
    assert np.corrcoef(pred, y[300:])[0, 1] > 0.95
    plain = build_hurdle().fit(X.iloc[:300], np.clip(x[:300], 0.05, 1))  # nothing at the floor
    assert plain[-1].two_stage_ is False


def test_temporal_ordering_flags_overlap() -> None:
    from experiments.ml_dataset import temporal_ordering

    frame = pd.DataFrame(
        {"g.finished_at": ["2026-11-01T00:00:00Z", "2026-11-03T00:00:00Z", "2026-11-02T00:00:00Z"]}
    )
    late = pd.Series([False, True, False])
    assert temporal_ordering(frame, late)["strict"] is True  # holdout is the latest job
    overlap = pd.Series([False, False, True])  # holdout (Nov 2) precedes train job (Nov 3)
    res = temporal_ordering(frame, overlap)
    assert res["strict"] is False and res["holdoutJobsBeforeTrainEnd"] == 1
    frame2 = pd.DataFrame({"g.finished_at": ["2026-11-01T00:00:00Z", "2026-11-02T00:00:00Z"]})
    assert temporal_ordering(frame2, pd.Series([False, True]))["strict"] is True


def test_h4_is_scored_in_both_directions_with_paired_contrasts() -> None:
    from experiments.qaqs_kfold import _h4_kfold

    rng = np.random.default_rng(0)
    rows = []
    for algo, n_cfg in (("RANDOM-VOLUMETRIC", 15), ("QFT", 20), ("GROVER", 20)):
        for c in range(n_cfg):
            x = rng.uniform(0, 1)
            for _ in range(3):
                rows.append({"meta.algorithm": algo, "meta.config_id": f"{algo}-{c}", "x": x,
                             "y": float(np.clip(1 - 0.8 * x + rng.normal(0, 0.03), 0, 1))})
    df = pd.DataFrame(rows)
    cfgs = df["meta.config_id"].drop_duplicates().reset_index(drop=True)
    fold_of = df["meta.config_id"].map(dict(zip(cfgs, cfgs.index % 5)))
    out = _h4_kfold(df, "y", [{"footprint": ["x"]}] * 5, fold_of, random_state=11, n_matched_draws=2)
    regimes = {r["regime"]: r for r in out["rows"]}
    assert set(regimes) == {
        "random_only", "paradigm_only", "combined", "paradigm_matched", "reverse_paradigm", "reverse_random_cv"
    }
    assert regimes["paradigm_only"]["nTest"] == 120 and regimes["reverse_paradigm"]["nTest"] == 45
    assert regimes["paradigm_matched"]["nTrain"] <= regimes["paradigm_only"]["nTrain"]
    assert len(regimes["paradigm_matched"]["r2PerDraw"]) == 2
    assert {(c["a"], c["b"]) for c in out["contrasts"]} >= {("paradigm_matched", "random_only")}
    # same relation in every algorithm here, so no regime can be shown to win
    assert all(c["verdict"] in {"a_better", "b_better", "no_difference_shown"} for c in out["contrasts"])


def test_config_folds_are_shared_across_chips_and_cover_every_config(tmp_path: Path) -> None:
    from experiments.qaqs_kfold import assign_config_folds

    bundle = load_ml_dataset(_synthetic_multichip_tables(tmp_path))
    table = assign_config_folds(bundle.frame, n_splits=4, n_repeats=2, seed=3)
    assert set(table.index) == set(bundle.frame["meta.config_id"].astype(str))
    assert list(table.columns) == ["r0", "r1"]
    for col in table.columns:
        assert set(table[col]) <= {0, 1, 2, 3} and (table[col] >= 0).all()
        # each algorithm's configs are spread over folds, not lumped into one
        algo = bundle.frame.groupby("meta.config_id")["meta.algorithm"].first()
        per_algo = table[col].groupby(algo.reindex(table.index).to_numpy()).nunique()
        assert (per_algo >= 2).all()
    assert not table["r0"].equals(table["r1"])  # repeats reshuffle


def test_kfold_procedure_scores_unseen_configs_only(tmp_path: Path) -> None:
    from experiments.qaqs_kfold import _nested_fold

    bundle = load_ml_dataset(_synthetic_multichip_tables(tmp_path))
    frame = bundle.frame[bundle.frame["meta.backend_name"] == "ibm_fez"]
    cfgs = sorted(frame["meta.config_id"].unique())
    test = frame[frame["meta.config_id"].isin(cfgs[::4])]
    train = frame.drop(test.index)
    res = _nested_fold(
        train, test, "f.fidelity.dsr", bundle.circuit_features, bundle.hardware_submit_features, 11,
        device_pool=bundle.device_calibration_features, hurdle=True,
    )
    assert set(res["testIndex"]) == set(test.index)
    assert {"circuit_only", "size_baseline", "hardware_only", "layout_only", "hurdle"} <= set(res["regimes"])
    assert all(c.startswith("cal.") for c in res["device"])
    reg = res["regimes"]["circuit_only"]
    assert reg["selected"] in reg["perModel"]
    assert all(len(m["pred"]) == len(test) for m in reg["perModel"].values() if "pred" in m)


def test_summarize_repeats_reports_spread() -> None:
    from experiments.qaqs_kfold import summarize_repeats

    rng = np.random.default_rng(0)
    y = pd.Series(rng.uniform(0, 1, 60))
    groups = pd.Series([f"c{i // 3}" for i in range(60)])
    preds = [pd.Series(np.clip(y + rng.normal(0, s, 60), 0, 1)) for s in (0.05, 0.10)]
    out = summarize_repeats(y, groups, preds)
    assert out["nRepeats"] == 2 and len(out["r2PerRepeat"]) == 2
    assert out["r2Sd"] > 0
    assert out["h1Verdict"] in {"pass", "fail", "inconclusive"}


def test_prospective_row_matches_export_columns(tmp_path: Path) -> None:
    """Pre-registration features must equal the exporter's for the same prepared record."""
    import glob

    from experiments.qaqs_prospective import prepared_row

    root = Path(__file__).resolve().parents[1]
    record = sorted(glob.glob(str(root / "experiments/ghz/data/qpu/v2/GHZ8_IBM_ibm_kingston_20261111*.json")))[0]
    journal = json.loads(Path(record).read_text(encoding="utf-8"))
    prepared = json.loads(
        (Path(record).parent / journal["artifact_directory"] / "prepared.json").read_text(encoding="utf-8")
    )
    row = prepared_row(prepared)
    exported = load_ml_dataset(root / "experiments" / "dataset_out").frame
    exported = exported[exported["meta.record_path"].astype(str).str.endswith(Path(record).name)].iloc[0]
    for col in ("b.ComplexityMetrics.standardized_metrics.circuit_volume", "c.t1_us.median", "e.m2_error"):
        assert float(row[col]) == float(exported[col])


def test_unseen_qpu_uses_every_training_chip_and_is_labelled(tmp_path: Path) -> None:
    import experiments.qaqs_prospective as qp

    trained = qp.trained_chips()
    assert trained == {"ibm_fez", "ibm_kingston"}
    assert "ibm_marrakesh" not in trained  # the unseen QPU must never enter training before scoring


def test_validation_campaigns_never_reach_training(tmp_path: Path) -> None:
    """A prospective-validation campaign in the export is invisible to training loaders."""
    from experiments.ml_dataset import is_validation_campaign

    assert is_validation_campaign("marrakesh-validation-v1-2026-11-16")
    assert not is_validation_campaign("kingston-full-oracle-growth-v1-2026-11-11")
    tables = _synthetic_multichip_tables(tmp_path)
    csv = tables / "dataset-000.csv"
    frame = pd.read_csv(csv)
    extra = frame.head(5).copy()
    extra["meta.campaign_id"] = "ibm_fez-validation-v1-2026-11-16"
    extra["meta.job_id"] = [f"val-{i}" for i in range(len(extra))]
    pd.concat([frame, extra]).to_csv(csv, index=False)
    manifest = json.loads((tables / "dataset_manifest.json").read_text())
    for part in manifest["parts"]:
        part.pop("bytes", None)
        part.pop("rows", None)
    (tables / "dataset_manifest.json").write_text(json.dumps(manifest))
    training = load_ml_dataset(tables).frame
    everything = load_ml_dataset(tables, include_validation=True).frame
    assert not training["meta.campaign_id"].map(is_validation_campaign).any()
    assert len(everything) == len(training) + 5
