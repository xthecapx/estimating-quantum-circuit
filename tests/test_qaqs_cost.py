"""Execution-cost model: physical decomposition, leakage-free evaluation, and outputs."""

from pathlib import Path

import numpy as np
import pandas as pd

from experiments import qaqs_cost as C

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


def test_cost_frame_reads_only_jobs_with_resource_units_and_keeps_validation_flag():
    data = C.cost_frame(ROOT / "experiments" / "dataset_out")
    assert data["cost_rus"].notna().all() and len(data) == 2257
    assert set(data.loc[data["validation"], "backend"]) == {"ibm_fez", "ibm_kingston", "ibm_marrakesh"}
    assert int(data["validation"].sum()) == 252
    np.testing.assert_allclose(data[C.TARGET], data["cost_rus"] * 60)
    # 1 RU = 1 minute; IBM bills whole seconds rounded up.
    assert (np.ceil(data[C.TARGET] - 1e-9) == data["billed_whole_seconds"]).all()


def test_label_only_columns_are_not_model_inputs():
    for leaked in ("circuit_seconds", C.TARGET, "cost_rus", "billed_whole_seconds", "backend"):
        assert leaked not in C.FEATURES
