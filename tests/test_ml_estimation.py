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
from experiments.ml_estimation import build_models, run_pipeline


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
    ]
    chips = [
        ("ibm_fez", "w0", "2026-11-01T10:00:00Z"),
        ("ibm_fez", "w1", "2026-11-05T10:00:00Z"),
        ("ankaa_3", "rigetti-w1", "2026-11-10T10:00:00Z"),
        ("ionq_aria", "ionq-w1", "2026-11-12T10:00:00Z"),
    ]
    idx = 0
    for backend, campaign, ts in chips:
        for algo in algos:
            for size in (3, 5, 7, 9):
                depth = size * 8 + int(rng.integers(0, 12))
                g2 = size * 3 + int(rng.integers(0, 8))
                comm = float(rng.uniform(0.1, 0.95))
                n_single = int(rng.integers(5, 45))
                noise_base = 0.015 if "ibm" in backend else (0.025 if "ankaa" in backend else 0.008)
                dsr = float(np.clip(np.exp(-noise_base * g2) - 0.1 * comm + rng.normal(0, 0.02), 0.02, 0.99))
                hf = float(np.clip(dsr * 0.95 + 0.03, 0.02, 0.99))
                tvd = float(np.clip(1.0 - hf + rng.normal(0, 0.01), 0.01, 0.98))
                succ = float(np.clip(dsr * 0.9 + 0.05, 0.01, 0.99))
                rows.append(
                    {
                        "meta.backend_name": backend,
                        "meta.campaign_id": campaign,
                        "meta.window": 1 if campaign != "w0" else 0,
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
                        "c.two_qubit_gate_error.median": noise_base,
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


def test_multichip_loader_vif_and_end_to_end_pipeline(tmp_path: Path) -> None:
    tables = _synthetic_multichip_tables(tmp_path)
    bundle = load_ml_dataset(tables)
    assert set(bundle.frame["meta.provider"].unique()) == {"ibm", "rigetti", "ionq"}
    assert "a.quantum_specific_present" in bundle.circuit_features
    assert "c.two_qubit_gate_error.median" in bundle.hardware_submit_features

    is_holdout, periods = split_temporal_and_cv(bundle.frame)
    assert is_holdout.any()
    assert periods

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
        xgb,
        bundle.frame,
        bundle.frame["f.fidelity.dsr"],
        selected,
        stats_df,
        vif_map,
    )
    assert len(contrib) == len(selected)
    assert all("shapMeanAbs" in r and "permutationImportance" in r for r in contrib)

    report_out = tmp_path / "reports"
    dash_out = tmp_path / "dash_est"
    snapshots = run_pipeline(
        tables=tables,
        report_out=report_out,
        dashboard_out=dash_out,
    )
    assert set(snapshots) == {"ibm_fez", "ankaa_3", "ionq_aria", "pooled"}
    pooled = snapshots["pooled"]
    assert set(pooled["providersIncluded"]) == {"ibm", "rigetti", "ionq"}
    xfer = pooled["targets"]["dsr"]["h3"]["transferMatrix"]
    pairs = {(c["sourceProvider"], c["targetProvider"]) for c in xfer}
    assert ("ibm", "rigetti") in pairs
    assert ("ibm", "ionq") in pairs
    assert (report_out / "report.md").is_file()
    assert (report_out / "best_predictors.json").is_file()
    assert (report_out / "footprint_ablation.csv").is_file()
    manifest_file = report_out / "models" / "models_manifest.json"
    assert manifest_file.is_file()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["models"]

    best_pred_doc = json.loads((report_out / "best_predictors.json").read_text(encoding="utf-8"))
    assert best_pred_doc["globalCorePreRuntimePredictors"]

    dsr_target = pooled["targets"]["dsr"]
    assert "circuit_only" in dsr_target["savedModels"]
    assert "mixed_submit" in dsr_target["savedModels"]
    model_rel = dsr_target["savedModels"]["circuit_only"]["path"]
    saved_bundle = joblib.load(report_out / model_rel)
    preds = np.clip(
        saved_bundle["pipeline"].predict(bundle.frame[saved_bundle["features"]].head(10)),
        0.0,
        1.0,
    )
    assert preds.shape == (10,)
    assert np.all(np.isfinite(preds)) and np.all((preds >= 0.0) & (preds <= 1.0))
    assert (dash_out / "pooled.json").is_file()


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
    assert "a.synthetic_pure_noise" not in best_feats
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
