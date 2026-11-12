"""Offline proof: reconciled client failures resume without duplicate jobs."""

import json
from pathlib import Path

import pytest

from experiments import ibm_campaign as C
from tests.test_ibm_campaign import _experiment, _plan, fez, runtime
from experiments.ghz.ghz_ibm import GHZIBMExperiment


def partial_campaign(tmp_path, monkeypatch, fez, runtime):
    campaign = _experiment(GHZIBMExperiment, tmp_path, monkeypatch).campaign()
    prepared = campaign.prepare_plan(
        _plan(tmp_path, items=[{"config": "GHZ3"}], runs=3), runtime.service(fez)
    )
    path = Path(prepared["manifest_path"])
    manifest = json.loads(path.read_text())
    record_path = C.manifest_record_path(path, manifest["items"][0])
    loaded = campaign.store.load(record_path)
    sampler = runtime.SamplerV2(mode=fez, options=loaded[1]["runtime_options"])
    job_id = campaign.store.submit_job(
        record_path, loaded, sampler, run_index=0, calibration={}, batch_id="original"
    )
    journal = json.loads(record_path.read_text())
    journal["status"] = "submission_rejected"
    journal["submission_journal"].append(
        {
            "run_index": 1,
            "job_id": None,
            "status": "submission_rejected",
            "reconciliation": {"confirmed_before_send": True},
        }
    )
    C.write_json(record_path, journal)
    manifest["status"] = "resume_ready"
    manifest["batch_id"] = "original"
    manifest["items"][0]["job_ids"] = [job_id]
    C.write_json(path, manifest)
    return campaign, path, record_path


def test_resume_preserves_ids_and_rejected_attempts(tmp_path, monkeypatch, fez, runtime):
    campaign, path, record_path = partial_campaign(tmp_path, monkeypatch, fez, runtime)
    frozen = campaign.store.load(record_path)[1]
    result = campaign.submit_manifest(path, fez)
    assert len(runtime.submitted) == 3
    assert result["items"][0]["job_ids"] == ["job-0", "job-1", "job-2"]
    assert result["previous_batches"] == [{"batch_id": "original", "job_ids": ["job-0"]}]
    journal, after, _ = campaign.store.load(record_path)
    assert after == frozen
    assert journal["submission_journal"][1]["status"] == "submission_rejected"
    assert campaign.store.submitted_runs()[(frozen["campaign_id"], frozen["window"])] == 3
    with pytest.raises(ValueError, match="fresh prepared"):
        campaign.submit_manifest(path, fez)
    assert len(runtime.submitted) == 3
    recovered = campaign.store.recover(record_path, runtime.service(fez))
    assert recovered["status"] == "completed"
    assert len(recovered["individual_results"]) == 3


@pytest.mark.parametrize("corruption", ["unknown", "ids", "duplicate", "backend"])
def test_resume_blocks_uncertain_or_inconsistent_state(
    tmp_path, monkeypatch, fez, runtime, corruption
):
    campaign, path, record_path = partial_campaign(tmp_path, monkeypatch, fez, runtime)
    journal = json.loads(record_path.read_text())
    manifest = json.loads(path.read_text())
    if corruption == "unknown":
        journal["submission_journal"][1]["status"] = "submission_unknown"
    elif corruption == "ids":
        manifest["items"][0]["job_ids"] = []
    elif corruption == "duplicate":
        journal["submission_journal"].append(journal["submission_journal"][0].copy())
    else:
        manifest["backend_name"] = "different"
    C.write_json(record_path, journal)
    C.write_json(path, manifest)
    with pytest.raises(ValueError):
        campaign.submit_manifest(path, fez)
    assert len(runtime.submitted) == 1


def test_gate_twirling_uses_explicit_server_side_sampler():
    import qiskit_ibm_runtime
    from qiskit_ibm_runtime.server_side import SamplerV2

    assert C.sampler_class({"twirling": {"enable_gates": True}}) is SamplerV2
    assert C.sampler_class({"twirling": {"enable_gates": False}}) is qiskit_ibm_runtime.SamplerV2


def test_resumed_usage_includes_original_batch(tmp_path, monkeypatch, fez, runtime):
    from types import SimpleNamespace
    import qiskit_ibm_runtime

    campaign, path, _ = partial_campaign(tmp_path, monkeypatch, fez, runtime)
    campaign.submit_manifest(path, fez)
    seen = []

    def from_id(batch_id, *, service):
        seen.append(batch_id)
        return SimpleNamespace(usage=lambda: 2 if batch_id == "original" else 7)

    monkeypatch.setattr(qiskit_ibm_runtime, "Batch", SimpleNamespace(from_id=from_id))
    result = campaign.usage([path], SimpleNamespace(usage=lambda: {}))
    assert seen == ["original", "batch-1"]
    assert result["total_batch_usage_seconds"] == 9
