"""Execution-cost model: physical decomposition, leakage-free evaluation, and outputs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments import qaqs_cost as C
from experiments.ml_dataset import is_validation_campaign

ROOT = Path(__file__).resolve().parents[1]


def _synthetic(n=120, seed=3):
    rng = np.random.default_rng(seed)
    dur = rng.uniform(2e-6, 40e-6, n)
    tw = (rng.uniform(size=n) < 0.15).astype(float)
    shots = np.full(n, 1024.0)
    per_shot = 258e-6 + 1.02 * dur + tw * 4 * dur
    circuit = shots * per_shot
    billed = 1.70 + 0.03 * tw + circuit + rng.normal(0, 5e-4, n)
    frame = pd.DataFrame(
        {
            "shots": shots, "duration_s": dur, "twirling": tw, "dynamic": 0.0, "dynamical_decoupling": tw,
            "circuit_seconds": circuit, C.TARGET: billed, "billed_whole_seconds": np.ceil(billed),
            "config_id": [f"c{i // 3}" for i in range(n)],
        }
    )
    for col in C.CIRCUIT_FEATURES:
        frame[col] = dur * 1e6 * rng.uniform(0.9, 1.1, n)
    return frame


def test_physical_model_recovers_overhead_and_per_shot_terms():
    frame = _synthetic()
    model = C.PhysicalCostModel().fit(frame, frame[C.TARGET].to_numpy())
    t = model.terms()
    assert abs(t["overheadSeconds"] - 1.70) < 0.005
    assert abs(t["perShotSeconds"] - 258e-6) < 5e-6
    assert abs(t["durationSlope"] - 1.02) < 0.05


def test_shots_scale_the_prediction_linearly():
    frame = _synthetic()
    model = C.PhysicalCostModel().fit(frame, frame[C.TARGET].to_numpy())
    row = frame.iloc[[0]].copy()
    base = model.predict(row)[0]
    row["shots"] = 2048.0
    doubled = model.predict(row)[0]
    circuit = base - model.terms()["overheadSeconds"] - model.terms()["twirlingOverheadSeconds"] * row["twirling"].iloc[0]
    assert abs((doubled - base) - circuit) < 1e-9


def test_grouped_kfold_holds_out_whole_configurations():
    frame = _synthetic()
    folds = C.assign_folds(frame, 5, 11)
    assert (frame.groupby("config_id").apply(lambda g: folds[g.index].nunique()) == 1).all()


def _exported(columns):
    """Columns read straight from the export, independently of the loader under test."""
    tables = ROOT / "experiments" / "dataset_out"
    parts = json.loads((tables / "dataset_manifest.json").read_text())["parts"]
    return pd.concat([pd.read_csv(tables / p["file"], usecols=columns) for p in parts], ignore_index=True)


def test_cost_frame_reads_only_jobs_with_resource_units_and_keeps_validation_flag():
    data = C.cost_frame(ROOT / "experiments" / "dataset_out")
    raw = _exported(["meta.job_id", "meta.campaign_id", "meta.backend_name", "g.cost_rus"])
    billed = raw[raw["g.cost_rus"].notna()]
    assert len(billed) > 0  # the export must have usage reports for this test to mean anything
    assert data["cost_rus"].notna().all() and len(data) == len(billed)
    assert set(data["job_id"]) == set(billed["meta.job_id"])
    validation = billed[billed["meta.campaign_id"].map(is_validation_campaign)]
    assert set(data.loc[data["validation"], "backend"]) == set(validation["meta.backend_name"])
    assert int(data["validation"].sum()) == len(validation)
    np.testing.assert_allclose(data[C.TARGET], data["cost_rus"] * 60)
    # 1 RU = 1 minute; IBM bills whole seconds rounded up.
    assert (np.ceil(data[C.TARGET] - 1e-9) == data["billed_whole_seconds"]).all()


def test_label_only_columns_are_not_model_inputs():
    for leaked in ("circuit_seconds", C.TARGET, "cost_rus", "billed_whole_seconds", "backend"):
        assert leaked not in C.FEATURES


def _two_chips(n=160, seed=5):
    """Two chips whose per-shot constants differ by 8 µs, as real chips do."""
    frame = _synthetic(n, seed)
    frame["backend"] = np.where(np.arange(n) % 2 == 0, "chip_a", "chip_b")
    shift = np.where(frame["backend"] == "chip_b", 8e-6, 0.0) * frame["shots"]
    frame["circuit_seconds"] += shift
    frame[C.TARGET] += shift
    frame["billed_whole_seconds"] = np.ceil(frame[C.TARGET])
    return frame


def test_each_chip_gets_its_own_per_shot_constant():
    frame = _two_chips()
    model = C.PhysicalCostModel().fit(frame, frame[C.TARGET].to_numpy())
    terms = model.terms()
    by_chip = terms["perShotSecondsByChip"]
    assert abs(by_chip["chip_a"] - 258e-6) < 1e-6
    assert abs(by_chip["chip_b"] - 266e-6) < 1e-6
    assert abs(terms["perShotChipSpreadSeconds"] - 8e-6) < 1e-6
    # The single constant older readers use is the job-weighted average of the chips.
    assert abs(terms["perShotSeconds"] - 262e-6) < 1e-6
    for chip, shift in (("chip_a", 0.0), ("chip_b", 8e-6 * 1024)):
        rows = frame[frame["backend"] == chip]
        assert abs(np.mean(model.predict(rows) - rows[C.TARGET])) < 5e-4


def test_unseen_chip_uses_the_flagged_training_average():
    frame = _two_chips()
    model = C.PhysicalCostModel().fit(frame, frame[C.TARGET].to_numpy())
    row = frame.iloc[[0]].copy()
    known = model.predict_circuit_seconds(row)[0]
    row["backend"] = "chip_never_seen"
    assert model.unseen_chip(row).all() and not model.unseen_chip(frame).any()
    fallback = model.predict_circuit_seconds(row)[0]
    # chip_a sits 4 µs per shot below the average of the two training chips.
    assert abs((fallback - known) - 4e-6 * 1024) < 1e-6


def test_model_without_a_chip_column_keeps_one_constant():
    frame = _synthetic()
    model = C.PhysicalCostModel().fit(frame, frame[C.TARGET].to_numpy())
    assert model.terms()["perShotSecondsByChip"] == {}
    assert not model.unseen_chip(frame).any()


def test_residual_is_not_applied_at_unseen_shot_counts():
    frame = _two_chips()
    model = C.HybridCostModel().fit(frame, frame[C.TARGET].to_numpy())
    row = frame.iloc[[0]].copy()
    assert model.residual_applied(row).all()
    row["shots"] = 4096.0
    assert not model.residual_applied(row).any()
    np.testing.assert_allclose(model.predict(row), model.physical_.predict(row))


def test_whole_second_accuracy_reports_its_base_rate_and_boundary_subset():
    y = np.array([1.90, 1.95, 1.995, 2.005, 2.50])
    whole = np.ceil(y)
    pred = y + np.array([0.0, 0.0, 0.0, -0.01, 0.0])  # one near-boundary job crosses 2 s
    scores = C.evaluate(y, pred, whole, majority=2.0)
    assert list(scores)[:2] == ["n", "maeMilliseconds"]  # MAE leads
    assert scores["billedSecondsAccuracy"] == 0.8
    assert scores["majorityBaselineAccuracy"] == 0.6
    assert scores["nearBoundaryJobs"] == 2
    assert scores["nearBoundaryAccuracy"] == 0.5
    assert scores["nearBoundaryMajorityAccuracy"] == 0.5
    assert C.majority_bill([2, 2, 3]) == 2.0


def _raw_jobs(n, backend, provider, with_ru):
    frame = pd.DataFrame(
        {
            "meta.job_id": [f"{backend}-{i}" for i in range(n)],
            "meta.config_id": [f"{backend}-c{i // 2}" for i in range(n)],
            "meta.algorithm": "GHZ",
            "meta.backend_name": backend,
            "meta.provider": provider,
            "meta.campaign_id": "campaign",
            "meta.shots": 1024,
        }
    )
    if with_ru:
        frame["g.cost_rus"] = 0.033
        frame["g.billed_seconds"] = 2
        frame["g.circuit_execution_seconds"] = 0.27
    return frame


def test_provider_without_usage_reports_waits_for_data_instead_of_raising(tmp_path, monkeypatch):
    billed = _raw_jobs(4, "chip_a", "provider_a", with_ru=True)
    unbilled = _raw_jobs(3, "chip_b", "provider_b", with_ru=False)
    mixed = pd.concat([billed, unbilled], ignore_index=True)
    coverage = {row["provider"]: row for row in C.cost_coverage(mixed)}
    assert coverage["provider_a"]["status"] == "modelled" and coverage["provider_a"]["withRu"] == 4
    assert coverage["provider_b"]["status"] == C.WAITING and coverage["provider_b"]["withRu"] == 0
    assert set(C.cost_frame(frame=mixed)["provider"]) == {"provider_a"}

    # No usage column at all: an empty frame and a report, never an exception.
    assert C.cost_frame(frame=unbilled).empty

    class Bundle:
        frame = unbilled

    monkeypatch.setattr(C, "load_ml_dataset", lambda *args, **kwargs: Bundle)
    dashboard = tmp_path / "cost.json"
    result = C.run(tmp_path, tmp_path / "report", dashboard)
    assert result["status"] == C.WAITING
    assert C.WAITING in (tmp_path / "report" / "report.md").read_text()
    assert not dashboard.exists()
