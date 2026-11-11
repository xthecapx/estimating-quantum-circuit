# Adapted from QWARD for the thesis experiment namespace and paths.
"""Offline proofs for the manual Rigetti pilot. No AWS credentials or tasks."""

import copy
import csv
import json
import shutil

import pytest
from qiskit import QuantumCircuit

pytest.importorskip("braket.devices")
pytest.importorskip("qiskit_braket_provider")

from experiments import aws_campaign as campaign
from experiments import aws_pilot_data as data
from experiments import campaign_matrix


@pytest.fixture(autouse=True)
def forbid_aws(monkeypatch):
    import boto3

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline tests must not create an AWS session")

    monkeypatch.setattr(boto3, "Session", forbidden)


@pytest.fixture(scope="module")
def prepared_template(tmp_path_factory):
    path = tmp_path_factory.mktemp("aws-pilot") / "run"
    campaign.prepare(path, bucket="test-results", shots=1024)
    return path


@pytest.fixture
def run(tmp_path, prepared_template):
    path = tmp_path / "run"
    shutil.copytree(prepared_template, path)
    return path


class FakeAWS:
    """Track cloud-side tasks independently of the local journal."""

    arn = "arn:aws:braket:us-west-1:123456789012:quantum-task/test"

    def __init__(self):
        self.requests = []
        self.state = "COMPLETED"
        self.lose_response = False
        self.properties = {
            "action": {
                "braket.ir.openqasm.program": {
                    "supportedOperations": ["rx", "ry", "rz", "cnot", "x", "h", "i"]
                }
            },
            "service": {"shotsRange": [1, 10000], "executionWindows": []},
            "paradigm": {"qubitCount": 108, "connectivity": {"fullyConnected": False}},
            "standardized": {
                "oneQubitProperties": {
                    "7": {
                        "T1": {"value": 0.00002, "unit": "s"},
                        "T2": {"value": 18000, "unit": "ns"},
                        "oneQubitFidelity": [
                            {"fidelity": 0.98, "fidelityType": {"name": "READOUT"}}
                        ],
                    }
                },
                "twoQubitProperties": {"7-8": {"twoQubitGateFidelity": [{"fidelity": 0.97}]}},
            },
        }

    def identity(self):
        return {"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/test"}

    def device(self, arn):
        return {
            "deviceArn": arn,
            "deviceName": "Cepheus-1-108Q",
            "deviceStatus": "ONLINE",
            "deviceType": "QPU",
            "deviceCapabilities": json.dumps(self.properties),
        }

    def check_bucket(self, bucket):
        assert bucket == "test-results"

    def create(self, request):
        self.requests.append(copy.deepcopy(request))
        if self.lose_response:
            raise TimeoutError("Task accepted, response lost")
        return self.arn

    def task(self, arn):
        request = self.requests[0]
        return {
            "quantumTaskArn": arn,
            "status": self.state,
            "deviceArn": request["deviceArn"],
            "shots": request["shots"],
            "tags": request["tags"],
            "outputS3Bucket": request["outputS3Bucket"],
            "outputS3Directory": request["outputS3KeyPrefix"] + "/task",
            "failureReason": "test failure" if self.state == "FAILED" else None,
        }

    def result(self, metadata):
        request = self.requests[0]
        return json.dumps(
            {
                "taskMetadata": {
                    "id": self.arn,
                    "deviceId": request["deviceArn"],
                    "shots": request["shots"],
                },
                "additionalMetadata": {
                    "action": json.loads(request["action"]),
                    "rigettiMetadata": {"compiledProgram": "native program preserved"},
                },
                "measuredQubits": [0, 1, 2],
                "measurements": [[1, 0, 1]] * request["shots"],
            }
        )


def test_prepare_is_offline_and_frozen(run):
    prepared, journal = campaign.load(run)
    assert journal["status"] == "prepared"
    assert prepared["local_check"]["counts"] == {"101": 1024}
    assert prepared["local_check"]["max_probability_error"] < 1e-8
    assert prepared["task_budget"] == 1
    request = campaign.read_json(run / "request.json")
    assert request["clientToken"] == prepared["run_id"]
    assert json.loads(request["action"]) == campaign.read_json(run / "action.json")
    with pytest.raises(ValueError, match="already exists"):
        campaign.prepare(run, bucket="test-results")


def test_submission_recovery_and_export(run, tmp_path):
    aws = FakeAWS()
    campaign.preflight(run, aws)
    assert not aws.requests
    assert campaign.submit(run, aws)["tasks_submitted"] == 1
    assert campaign.submit(run, aws)["tasks_submitted"] == 0
    frozen_request = campaign.read_json(run / "request.json")
    assert aws.requests == [frozen_request]
    assert campaign.recover(run, aws)["success_rate"] == 1
    assert campaign.recover(run, aws)["status"] == "completed"
    assert len(aws.requests) == 1
    raw = campaign.read_json(run / "raw_result.json")
    assert raw["additionalMetadata"]["rigettiMetadata"]["compiledProgram"]
    result = campaign.read_json(run / "result.json")
    assert result["targets"]["fidelity"]["available"]
    assert 0.99 < result["success_interval_95_wilson"][0] < 1
    report = campaign.export(run, tmp_path / "empty-ibm")
    assert report["rows"] == 1


def test_lost_response_requires_reconciliation_without_resubmission(run):
    aws = FakeAWS()
    aws.lose_response = True
    with pytest.raises(TimeoutError):
        campaign.submit(run, aws)
    assert campaign.read_json(run / "journal.json")["status"] == "submission_unknown"
    with pytest.raises(ValueError, match="Ambiguous"):
        campaign.submit(run, aws)
    assert campaign.recover(run, aws, task_arn=aws.arn)["status"] == "completed"
    assert len(aws.requests) == 1


def test_process_crash_after_aws_accepts_is_not_resubmitted(run, monkeypatch):
    aws = FakeAWS()
    create = aws.create

    def interrupted(request):
        create(request)
        raise KeyboardInterrupt

    monkeypatch.setattr(aws, "create", interrupted)
    with pytest.raises(KeyboardInterrupt):
        campaign.submit(run, aws)
    assert campaign.read_json(run / "journal.json")["status"] == "submitting"
    with pytest.raises(ValueError, match="Ambiguous"):
        campaign.submit(run, aws)
    assert campaign.recover(run, aws, task_arn=aws.arn)["status"] == "completed"


@pytest.mark.parametrize("state", ["QUEUED", "RUNNING", "FAILED", "CANCELLED"])
def test_pending_and_terminal_tasks_never_create_replacements(run, state):
    aws = FakeAWS()
    campaign.submit(run, aws)
    aws.state = state
    result = campaign.recover(run, aws)
    assert result["status"].upper() == state
    assert campaign.submit(run, aws)["tasks_submitted"] == 0
    assert not (run / "result.json").exists()
    assert len(aws.requests) == 1


def test_integrity_and_budget_checks_precede_submission(run, tmp_path):
    (run / "action.json").write_text("{}")
    aws = FakeAWS()
    with pytest.raises(ValueError, match="integrity"):
        campaign.submit(run, aws)
    assert not aws.requests
    with pytest.raises(ValueError, match="bounded"):
        campaign.prepare(tmp_path / "too-many", bucket="test-results", shots=1025)


def test_recovery_cannot_submit_prepared_record(run):
    aws = FakeAWS()
    with pytest.raises(ValueError, match="No submitted"):
        campaign.recover(run, aws, task_arn=aws.arn)
    assert not aws.requests


def test_concurrent_submission_lock(run):
    with campaign.locked(run):
        with pytest.raises(ValueError, match="Another command"):
            campaign.submit(run, FakeAWS())


@pytest.mark.parametrize(
    "field,value",
    [
        ("shots", 3),
        ("deviceArn", "other-device"),
        ("tags", {}),
        ("outputS3Bucket", "another-bucket"),
    ],
)
def test_recovery_rejects_unrelated_tasks(run, monkeypatch, field, value):
    aws = FakeAWS()
    campaign.submit(run, aws)
    metadata = aws.task(aws.arn)
    metadata[field] = value
    monkeypatch.setattr(aws, "task", lambda arn: metadata)
    with pytest.raises(ValueError, match="provenance"):
        campaign.recover(run, aws)
    assert not (run / "result.json").exists()


def test_bad_counts_preserve_raw_result_for_diagnosis(run, monkeypatch):
    aws = FakeAWS()
    campaign.submit(run, aws)
    raw = json.loads(aws.result(None))
    raw["measuredQubits"] = [1, 2, 3]
    monkeypatch.setattr(aws, "result", lambda meta: json.dumps(raw))
    with pytest.raises(ValueError, match="mapping"):
        campaign.recover(run, aws)
    assert (run / "raw_result.json").exists()
    assert not (run / "result.json").exists()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda props: props["service"].update(shotsRange=[1, 100]),
        lambda props: props["paradigm"].update(qubitCount=2),
        lambda props: props.update(action={}),
        lambda props: props["action"]["braket.ir.openqasm.program"].update(supportedOperations=[]),
    ],
)
def test_live_capability_failures_submit_nothing(run, mutate):
    aws = FakeAWS()
    mutate(aws.properties)
    with pytest.raises(ValueError):
        campaign.submit(run, aws)
    assert not aws.requests
    assert campaign.read_json(run / "journal.json")["status"] == "prepared"
    assert (run / "preflight.json").exists()


def test_offline_device_submits_nothing(run, monkeypatch):
    aws = FakeAWS()
    device = aws.device(campaign.DEVICE_ARN)
    device["deviceStatus"] = "OFFLINE"
    monkeypatch.setattr(aws, "device", lambda arn: device)
    with pytest.raises(ValueError, match="ONLINE"):
        campaign.submit(run, aws)
    assert not aws.requests


@pytest.mark.parametrize("change_source", [False, True])
def test_result_action_allows_omitted_empty_inputs_but_rejects_changed_program(
    run, monkeypatch, change_source
):
    aws = FakeAWS()
    campaign.submit(run, aws)
    raw = json.loads(aws.result(None))
    raw["additionalMetadata"]["action"].pop("inputs", None)
    if change_source:
        raw["additionalMetadata"]["action"]["source"] = "other program"
    monkeypatch.setattr(aws, "result", lambda metadata: json.dumps(raw))
    if change_source:
        with pytest.raises(ValueError, match="OpenQASM"):
            campaign.recover(run, aws)
        assert (run / "raw_result.json").exists()
    else:
        assert campaign.recover(run, aws)["status"] == "completed"


def test_profile_preserves_details_and_normalizes_units():
    aws = FakeAWS()
    summary = data.profile_summary(aws.device(campaign.DEVICE_ARN))
    assert summary["coherence_us"]["7"]["T1"]["value_us"] == 20
    assert summary["coherence_us"]["7"]["T2"]["value_us"] == 18
    assert summary["standardized"] == aws.properties["standardized"]
    assert summary["calibrated_at"] is None
    aws.properties["standardized"]["oneQubitProperties"]["7"]["T1"]["unit"] = "unknown"
    assert (
        data.profile_summary(aws.device(campaign.DEVICE_ARN))["coherence_us"]["7"]["T1"]["value_us"]
        is None
    )
    aws.properties.pop("standardized")
    assert (
        data.profile_summary(aws.device(campaign.DEVICE_ARN))["coverage"][
            "edges_with_standardized_properties"
        ]
        == 0
    )


def test_asymmetric_mapping_and_unmeasured_ancilla():
    circuit = QuantumCircuit(4, 3)
    circuit.x(0)
    circuit.x(3)  # Unmeasured ancilla must never enter the count label.
    circuit.measure(2, 0)
    circuit.measure(1, 1)
    circuit.measure(0, 2)
    compiled, braket_circuit, action = data.translate(circuit)
    mapping = data.measurement_map(compiled)
    assert mapping == [2, 1, 0]
    checked = data.verify_locally(braket_circuit, action, mapping, {"100": 1.0}, 64)
    assert checked["counts"] == {"100": 64}
    assert data.normalize_counts({"100": 5}, [0, 1, 2], mapping, 5) == {"100": 5}


@pytest.mark.parametrize(
    "counts,qubits,shots",
    [({"0100": 3}, [0, 1, 2], 3), ({"010": 3}, [0, 1, 2], 4), ({"010": 3}, [0, 0, 2], 3)],
)
def test_invalid_result_shapes_fail_closed(counts, qubits, shots):
    with pytest.raises(ValueError):
        data.normalize_counts(counts, qubits, [0, 1, 2], shots)


@pytest.mark.parametrize(
    "algorithm,config_id",
    [(key, config) for key in data.ALGORITHMS for config in campaign_matrix.PILOT[key]],
)
def test_all_supported_pilot_circuits_preserve_ideal_distribution(algorithm, config_id):
    runner = campaign_matrix.load_runner(algorithm)
    config = runner.get_config(config_id)
    circuit = runner.create_circuit(config)
    compiled, braket_circuit, action = data.translate(circuit)
    checked = data.verify_locally(
        braket_circuit, action, data.measurement_map(compiled), runner.get_reference(config), 32
    )
    assert checked["max_probability_error"] < 1e-8


def test_export_matches_logical_circuits_and_preserves_ibm_repetitions(run, tmp_path):
    aws = FakeAWS()
    campaign.submit(run, aws)
    campaign.recover(run, aws)
    prepared, _ = campaign.load(run)
    root = tmp_path / "ibm"
    v2 = root / "bv" / "data" / "qpu" / "v2"
    artifacts = v2 / "artifacts" / "test"
    artifacts.mkdir(parents=True)
    frozen = {
        k: prepared[k]
        for k in ("logical_circuit_hash", "shots", "optimization_level", "seed_transpiler")
    }
    campaign.write_json(artifacts / "prepared.json", frozen)
    journal = {
        "config_id": "BV3-ALT",
        "artifact_directory": "artifacts/test",
        "window": 0,
        "campaign_id": "ibm-pilot",
        "backend_name": "ibm_fez",
        "individual_results": [
            {"job_id": f"ibm-{i}", "counts": {"101": 1000, "000": 24}} for i in range(2)
        ],
    }
    campaign.write_json(v2 / "record.json", journal)
    report = campaign.export(run, root)
    assert report["ibm_matches"] == 2
    with (run / "comparison.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert {row["job_id"] for row in rows} == {aws.arn, "ibm-0", "ibm-1"}
    frozen["logical_circuit_hash"] = "different"
    campaign.write_json(artifacts / "prepared.json", frozen)
    report = campaign.export(run, root)
    assert report["ibm_matches"] == 0
    assert report["skipped"][0]["reason"] == "logical_circuit_hash_mismatch"
