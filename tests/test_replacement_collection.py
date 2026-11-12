"""Replacement observations fill original collection slots without rewriting raw data."""

import json
from copy import deepcopy

import pytest

from experiments.dataset_export import collection_identity
from experiments.ibm_campaign import record_hash


@pytest.fixture
def linked(tmp_path):
    original = {
        "logical_circuit_hash": "same",
        "shots": 1024,
        "runtime_options": {},
        "reference": {"1": 1},
    }
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts/prepared.json").write_text(json.dumps(original))
    source = {
        "campaign_id": "window-3",
        "window": 3,
        "algorithm": "BV",
        "config_id": "BV3-ALT",
        "backend_name": "ibm_kingston",
        "prepared_hash": record_hash(original),
        "artifact_directory": "artifacts",
        "submission_journal": [{"job_id": "failed", "run_index": 1}],
        "individual_results": [],
    }
    source_path = tmp_path / "original.json"
    source_path.write_text(json.dumps(source))
    journal = {**source, "campaign_id": "replacement-r1"}
    prepared = {
        **original,
        "payload": {
            "replacement_of": {
                "record_path": "experiments/bv/data/qpu/v2/original.json",
                "campaign_id": "window-3",
                "prepared_hash": source["prepared_hash"],
                "job_id": "failed",
                "run_index": 1,
            }
        },
    }
    return source_path, source, journal, prepared


def test_replacement_uses_original_period_and_second_repetition(linked):
    path, _, journal, prepared = linked
    before = path.read_bytes(), deepcopy(journal), deepcopy(prepared)
    assert collection_identity(
        path.with_name("replacement.json"), journal, prepared, {"run_index": 0}
    ) == ("window-3", 3, 1, "failed")
    assert before == (path.read_bytes(), journal, prepared)
    assert journal["campaign_id"] == "replacement-r1"


@pytest.mark.parametrize("change", ["successful", "hash", "backend", "protocol", "missing"])
def test_replacement_rejects_invalid_links(linked, change):
    path, source, journal, prepared = linked
    if change == "successful":
        source["individual_results"] = [{"job_id": "failed"}]
    elif change == "hash":
        prepared["payload"]["replacement_of"]["prepared_hash"] = "changed"
    elif change == "backend":
        journal["backend_name"] = "other"
    elif change == "protocol":
        prepared["shots"] = 512
    else:
        source["submission_journal"] = []
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError):
        collection_identity(path.with_name("replacement.json"), journal, prepared, {"run_index": 0})


def test_ordinary_record_keeps_its_identity(tmp_path):
    assert collection_identity(
        tmp_path / "record.json",
        {"campaign_id": "normal", "window": 2},
        {"payload": {}},
        {"run_index": 1},
    ) == ("normal", 2, 1, None)
