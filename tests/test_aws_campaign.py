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


def test_template_bucket_rejected_before_creating_record(tmp_path):
    path = tmp_path / "pilot"
    with pytest.raises(ValueError, match="actual S3 bucket"):
        campaign.prepare(path, bucket="YOUR_US_EAST_1_BUCKET")
    assert not path.exists()


def test_missing_bucket_does_not_freeze_paid_sr8_request(tmp_path, monkeypatch):
    from botocore.exceptions import ClientError
    from types import SimpleNamespace
    from experiments import braket_study as study

    def missing_bucket(**kwargs):
        raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")

    client = object.__new__(campaign.AWSClient)
    client.region = "us-east-1"
    client.s3 = SimpleNamespace(head_bucket=missing_bucket)
    monkeypatch.setattr(campaign, "AWSClient", lambda profile, region: client)
    with pytest.raises(ValueError, match="S3 404.*us-east-1"):
        study.ionq_chip_pilot(tmp_path, "typo-results", submit=True)
    assert not (tmp_path / study.IONQ_CHIP_PILOT["key"]).exists()


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


def test_bucket_free_profile_capture_only_reads_device(tmp_path):
    class ReadOnlyDevice:
        def device(self, arn):
            return FakeAWS().device(arn)

    out = tmp_path / "profile"
    result = campaign.capture_profile(out, ReadOnlyDevice())
    assert result["tasks_submitted"] == 0
    snapshot = json.loads((out / "device_profile.json").read_text())
    assert snapshot["raw"]["deviceArn"] == campaign.DEVICE_ARN
    assert snapshot["profile"]["coverage"]["qubits_with_standardized_properties"] == 1
    with pytest.raises(FileExistsError):
        campaign.capture_profile(out, ReadOnlyDevice())


def test_boto_client_advertises_schema_without_enabling_submit_retries(monkeypatch):
    import boto3

    configs = {}

    class Session:
        def __init__(self, **kwargs):
            assert kwargs == {"profile_name": "default", "region_name": "us-west-1"}

        def client(self, name, **kwargs):
            configs[name] = kwargs.get("config")
            return object()

    monkeypatch.setattr(boto3, "Session", Session)
    campaign.AWSClient("default")
    assert "BraketSchemas/" in configs["braket"].user_agent_extra
    assert configs["braket"].retries["total_max_attempts"] == 1


def test_default_chain_loads_repo_env_without_overriding_shell(monkeypatch):
    import boto3
    import dotenv
    from pathlib import Path

    loaded = []
    sessions = []
    monkeypatch.setattr(
        dotenv, "load_dotenv", lambda path, override: loaded.append((path, override))
    )

    class Session:
        def __init__(self, **kwargs):
            sessions.append(kwargs)

        def client(self, *args, **kwargs):
            return object()

    monkeypatch.setattr(boto3, "Session", Session)
    campaign.AWSClient()
    assert loaded == [(Path(campaign.__file__).resolve().parents[1] / ".env", False)]
    assert sessions == [{"profile_name": None, "region_name": "us-west-1"}]
    loaded.clear()
    campaign.AWSClient("default")
    assert not loaded


@pytest.mark.parametrize("region", ["us-west-1", "us-east-1"])
def test_bucket_region_uses_head_response_without_extra_permission(region):
    from types import SimpleNamespace

    client = object.__new__(campaign.AWSClient)
    client.s3 = SimpleNamespace(
        head_bucket=lambda **kwargs: {
            "ResponseMetadata": {"HTTPHeaders": {"x-amz-bucket-region": region}}
        }
    )
    if region == "us-west-1":
        client.check_bucket("test-bucket")
    else:
        with pytest.raises(ValueError, match="us-west-1"):
            client.check_bucket("test-bucket")


def test_rigetti_uppercase_seconds_are_normalized():
    aws = FakeAWS()
    aws.properties["standardized"]["oneQubitProperties"]["7"]["T1"] = {"value": 3e-5, "unit": "S"}
    summary = data.profile_summary(aws.device(campaign.DEVICE_ARN))
    assert summary["coherence_us"]["7"]["T1"]["value_us"] == pytest.approx(30)


def test_dual_device_git_checkpoint_and_budget(tmp_path, monkeypatch, capsys):
    import subprocess
    from experiments import braket_study as study
    from experiments import dataset_features
    from experiments.ml_dataset import load_ml_dataset, TARGETS
    import pandas as pd

    assert study.estimate(study.plan()) == study.Decimal("195.6016")
    with pytest.raises(ValueError, match="costs"):
        study.check_budget(study.plan(), "179")
    with pytest.raises(ValueError, match="costs"):
        study.check_budget(study.plan(), "201")
    rows = [
        r
        for r in study.plan()
        if (r["config"], r["stage"]) in (("GHZ3", "development-1"), ("IV3-011", "validation"))
    ]
    monkeypatch.setattr(study, "plan", lambda: rows)
    monkeypatch.setattr(dataset_features, "quantum_specific", lambda c: {"available": False})
    checkout = tmp_path / "professor"
    root = checkout / "experiments" / "data" / study.CAMPAIGN
    buckets = dict.fromkeys(study.DEVICES, "test-results")
    study.prepare(root, buckets)
    study.prepare(root, buckets)

    class RegionalFake(FakeAWS):
        def __init__(self, vendor):
            super().__init__()
            self.vendor = vendor
            self.by_arn = {}

        def create(self, request):
            super().create(request)
            region = study.DEVICES[self.vendor].split(":")[3]
            self.arn = f"arn:aws:braket:{region}:123456789012:quantum-task/{request['clientToken']}"
            self.by_arn[self.arn] = request
            return self.arn

        def task(self, arn):
            metadata = super().task(arn)
            request = self.by_arn[arn]
            metadata.update(
                tags=request["tags"], outputS3Directory=request["outputS3KeyPrefix"] + "/task"
            )
            return metadata

        def result(self, metadata):
            arn = metadata["quantumTaskArn"]
            request = self.by_arn[arn]
            result = json.loads(super().result(metadata))
            result["taskMetadata"]["id"] = arn
            result["additionalMetadata"]["action"] = json.loads(request["action"])
            if self.vendor == "ionq":
                del result["measurements"]
                result["measurementProbabilities"] = {"011": 0.63, "101": 0.37}
            return json.dumps(result)

    connections = {v: RegionalFake(v) for v in study.DEVICES}
    ionq_device = connections["ionq"].device
    statuses = iter(["OFFLINE", "ONLINE", "PAUSED"])

    def device(arn):
        return {
            **ionq_device(arn),
            "deviceName": "Forte-1",
            "deviceStatus": next(statuses, "ONLINE"),
        }

    def wait(seconds):
        assert seconds == 60
        assert len(connections["rigetti"].requests) == 1
        assert not connections["ionq"].requests

    monkeypatch.setattr(connections["ionq"], "device", device)
    monkeypatch.setattr(study, "clients", lambda profile: connections)
    monkeypatch.setattr(study.time, "sleep", wait)
    args = ["--run-dir", str(root)]
    stage = ["--stage", "development-1"]
    study.main([*args, "preflight", *stage])
    study.main(
        [
            *args,
            "submit",
            *stage,
            "--available-usd",
            "200",
            "--first-per-device",
            "--wait-for-devices",
        ]
    )
    alerts = capsys.readouterr().out
    assert "Forte-1 is OFFLINE" in alerts and "Forte-1 is PAUSED" in alerts
    study.submit_stage(root, connections, "development-1", 200, first_per_device=True)
    for vendor, client in connections.items():
        assert len(client.requests) == 1
        params = json.loads(client.requests[0]["deviceParameters"])
        assert vendor in params["braketSchemaHeader"]["name"]
        assert "errorMitigation" not in params
    assert study.recover_stage(root, connections, "development-1") == {
        "completed": 2,
        "prepared": 1,
    }
    study.submit_stage(root, connections, "development-1", 200)
    assert study.recover_stage(root, connections, "development-1") == {"completed": 3}
    with pytest.raises(ValueError, match="Freeze"):
        study.submit_stage(root, connections, "validation", 200)
    predictions = pd.DataFrame(
        [{"vendor": v, "config": "IV3-011", **dict.fromkeys(TARGETS, 0.5)} for v in study.DEVICES]
    )
    study.freeze_predictions(root, predictions, "fixture-model")
    study.submit_stage(root, connections, "validation", 200)
    assert study.recover_stage(root, connections, "validation") == {"completed": 3}
    # Commit exactly the paths the notebook names, then rebuild from a clean clone.
    for filename in (".gitignore", ".gitattributes"):
        shutil.copy(study.PAPERS.parent / filename, checkout / filename)
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(
        [
            "git",
            "add",
            "--",
            ".gitignore",
            ".gitattributes",
            f"experiments/data/{study.CAMPAIGN}",
            f":(glob)experiments/*/data/qpu/aws/{study.CAMPAIGN}/**",
        ],
        cwd=checkout,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "checkpoint",
        ],
        cwd=checkout,
        check=True,
    )
    clone = tmp_path / "analyst"
    subprocess.run(
        ["git", "clone", "-c", "core.autocrlf=true", "-q", str(checkout), str(clone)], check=True
    )
    offline = clone / root.relative_to(checkout)
    df = study.export_csv(offline)
    csv = study.dataset_path(offline)
    assert (
        csv.relative_to(clone).as_posix() == f"experiments/dataset_out/{study.CAMPAIGN}/dataset.csv"
    )
    assert all(
        path.is_relative_to(clone / "experiments" / r["algorithm"] / "data/qpu/aws")
        for r, path, _, _ in study.records(offline)
    )
    study.export_csv(root)
    assert csv.read_bytes() == study.dataset_path(root).read_bytes()
    assert df["meta.job_id"].nunique() == 6
    assert df.loc[df["meta.provider"] == "ionq", "meta.shots"].tolist() == [100, 100]
    study.export_csv(offline)
    assert len(load_ml_dataset(csv.parent).frame) == 3
    assert len(load_ml_dataset(csv.parent, include_validation=True).frame) == 6


def test_ionq_raw_frequency_mapping_and_fractional_rejection():
    prepared = {"device_arn": campaign.IONQ_ARN, "shots": 100, "clbit_to_qubit": [2, 1, 0]}
    raw = {"measurementProbabilities": {"001": 0.07, "010": 0.93}, "measuredQubits": [2, 0, 1]}
    assert data.decode_result(raw, prepared) == {"010": 7, "100": 93}
    raw["measurementProbabilities"] = {"001": 0.071, "010": 0.929}
    with pytest.raises(ValueError, match="integer shot counts"):
        data.decode_result(raw, prepared)


def test_ionq_check_counts_once_toward_full_campaign(tmp_path, monkeypatch):
    from experiments import braket_study as study, dataset_features

    row = next(r for r in study.plan() if r["key"] == study.IONQ_CHECK_KEY)
    monkeypatch.setattr(study, "plan", lambda: [row])
    monkeypatch.setattr(dataset_features, "quantum_specific", lambda c: {"available": False})
    client = FakeAWS()
    client.arn = client.arn.replace("us-west-1", "us-east-1")

    def connect(profile, region):
        assert region == "us-east-1"
        return client

    monkeypatch.setattr(campaign, "AWSClient", connect)
    root = tmp_path / "experiments/data" / study.CAMPAIGN
    bucket = "test-results"
    study.ionq_check(root, bucket)
    assert client.requests == []
    path = study.task_directory(root, row)
    prepared, _ = campaign.load(path)
    assert prepared["local_check"]["counts"] == {"011001": 100}

    def raw_result(meta):
        request = client.requests[0]
        return json.dumps(
            {
                "taskMetadata": {"id": client.arn, "deviceId": campaign.IONQ_ARN, "shots": 100},
                "additionalMetadata": {"action": json.loads(request["action"])},
                "measuredQubits": prepared["clbit_to_qubit"],
                "measurementProbabilities": {"100110": 1.0},
            }
        )

    monkeypatch.setattr(client, "result", raw_result)
    first = study.ionq_check(root, bucket, submit=True)
    assert json.loads(first["f.counts_json"]) == {"011001": 100}
    assert len(client.requests) == 1
    study.prepare(root, {"rigetti": "professor-west", "ionq": "professor-east"})
    study.submit_stage(root, {"ionq": client}, row["stage"], 200)
    assert study.ionq_check(root, bucket, submit=True) == first
    assert len(client.requests) == 1
    assert study.export_csv(root)["meta.job_id"].tolist() == [client.arn]


def test_standalone_sr8_chip_inventory(tmp_path, monkeypatch):
    from experiments import braket_study as study, dataset_features

    client = FakeAWS()
    client.arn = client.arn.replace("us-west-1", "us-east-1")
    client.properties["provider"] = {"fidelity": {"2Q": {"mean": 0.98}}, "timing": {"T2": 1.0}}
    client.properties["standardized"] = {}
    monkeypatch.setattr(campaign, "AWSClient", lambda profile, region: client)
    monkeypatch.setattr(dataset_features, "quantum_specific", lambda c: {"available": False})
    row = study.IONQ_CHIP_PILOT
    record = tmp_path / row["key"]
    study.main(["--run-dir", str(tmp_path), "ionq-chip-pilot", "--bucket", "test-results"])
    prepared, _ = campaign.load(record)
    assert prepared["reference"] == {"01100110": pytest.approx(1.0)}
    assert prepared["local_check"]["counts"] == {"01100110": 100}

    def result(meta):
        request = client.requests[0]
        return json.dumps(
            {
                "taskMetadata": {"id": client.arn, "deviceId": campaign.IONQ_ARN, "shots": 100},
                "additionalMetadata": {"action": json.loads(request["action"]), "ionqMetadata": {}},
                "measuredQubits": prepared["clbit_to_qubit"],
                "measurementProbabilities": {"01100110": 0.7, "00000000": 0.3},
            }
        )

    get_device = client.device
    waits = []

    def device(arn):
        snapshot = get_device(arn)
        if len(waits) < 2:
            snapshot["deviceStatus"] = ("PAUSED", "OFFLINE")[len(waits)]
        return snapshot

    def wait(seconds):
        assert not client.requests
        assert campaign.load(record)[1]["status"] == "prepared"
        waits.append(seconds)

    monkeypatch.setattr(client, "device", device)
    monkeypatch.setattr(study.time, "sleep", wait)
    monkeypatch.setattr(client, "result", result)
    for _ in range(2):
        exported = study.ionq_chip_pilot(tmp_path, "test-results", submit=True)
        assert exported["meta.campaign_id"] == "ionq-sr8-chip-pilot"
    assert waits == [60, 60]
    assert len(client.requests) == 1
    assert (
        client.requests[0]["shots"] == 100 and client.requests[0]["deviceArn"] == campaign.IONQ_ARN
    )
    report = campaign.read_json(record / "chip_inventory.json")
    profile = report["ionq"]["snapshots"]["profile_at_submission.json"]
    assert profile["qubits_with_standardized_properties"] == 0
    assert profile["provider_fidelity"] == client.properties["provider"]["fidelity"]
    assert report["archived_rigetti"]["config"] == "BV3-ALT"
    assert report["archived_ibm_sr8_examples"]["ibm_fez"]["config"] == "SR8"
    assert not (tmp_path / "manifest.json").exists()
    assert row["key"] not in {r["key"] for r in study.plan()}
