# Adapted from QWARD for the thesis experiment namespace and paths.
"""One-task, local Rigetti pilot: prepare -> preflight -> submit -> recover -> export.

Only the explicit ``submit`` command creates a paid quantum task. All submission
inputs are frozen on disk; recovery never recompiles or resubmits. See
docs/aws_rigetti_pilot.md for commands and artifact definitions.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from qiskit import qpy

from experiments import aws_pilot_data as data
from experiments.campaign_matrix import PAPERS
from experiments.ibm_campaign import json_value, package_versions
from qward.metrics.circuit_error_prediction import record_hash

DEVICE_ARN = "arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1-108Q"
REGION = "us-west-1"
SCHEMA = "aws-pilot-1.0"
PACKAGES = ("qiskit", "qiskit-braket-provider", "amazon-braket-sdk", "qiskit-qward", "boto3")


def now():
    """UTC observation time, not provider calibration time."""
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    """Durable atomic JSON replacement; reject non-finite metrics."""
    path = Path(path)
    content = json.dumps(value, indent=2, allow_nan=False, default=json_value) + "\n"
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path):
    """Read a saved artifact."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_hash(path):
    """Hash the exact bytes that will be used later."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def locked(record):
    """Prevent two local processes from mutating the same run simultaneously."""
    with (Path(record) / ".lock").open("a", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another command is using this run") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def load(record):
    """Verify immutable preparation before any cloud operation."""
    record = Path(record)
    journal = read_json(record / "journal.json")
    prepared = read_json(record / "prepared.json")
    if prepared["schema_version"] != SCHEMA or record_hash(prepared) != journal["prepared_hash"]:
        raise ValueError("Prepared record integrity/schema check failed")
    for filename, digest in prepared["artifact_hashes"].items():
        if file_hash(record / filename) != digest:
            raise ValueError(f"Artifact integrity check failed: {filename}")
    return prepared, journal


def prepare(
    record, *, bucket, prefix="qward/pilot", algorithm="bv", config_id="BV3-ALT", shots=1024
):
    """Prepare one execution entirely offline, including local Braket verification."""
    from braket.device_schema import GateModelParameters
    from braket.device_schema.rigetti import RigettiDeviceParameters

    if not 1 <= shots <= 1024:
        raise ValueError("The initial pilot is bounded to 1..1024 shots per task")
    if not bucket or bucket.startswith("s3://") or "/" in bucket:
        raise ValueError("Supply the existing S3 bucket name, without s3:// or a path")
    prefix = prefix.strip("/")
    if not prefix or any(part in {".", ".."} for part in prefix.split("/")):
        raise ValueError("Supply a nonempty S3 prefix without path traversal")
    record = Path(record)
    if record.exists():
        raise ValueError("Run directory already exists; use a new directory for a new execution")
    logical, compiled, action, payload = data.build_pilot(algorithm, config_id, shots)
    record.mkdir(parents=True, exist_ok=False)
    run_id = str(uuid4())
    for name, circuit in (("logical.qpy", logical), ("submitted.qpy", compiled)):
        with (record / name).open("wb") as stream:
            qpy.dump(circuit, stream)
            stream.flush()
            os.fsync(stream.fileno())
    write_json(record / "action.json", action)
    request = {
        "deviceArn": DEVICE_ARN,
        "action": json.dumps(action, sort_keys=True),
        "deviceParameters": RigettiDeviceParameters(
            paradigmParameters=GateModelParameters(
                qubitCount=compiled.num_qubits, disableQubitRewiring=False
            )
        ).json(),
        "shots": shots,
        "outputS3Bucket": bucket,
        "outputS3KeyPrefix": f"{prefix}/{run_id}",
        "clientToken": run_id,
        "tags": {"qward-run-id": run_id, "qward-config": config_id},
    }
    write_json(record / "request.json", request)
    prepared = {
        **payload,
        "schema_version": SCHEMA,
        "run_id": run_id,
        "prepared_at": now(),
        "device_arn": DEVICE_ARN,
        "region": REGION,
        "shots": shots,
        "task_budget": 1,
        "package_versions": package_versions(PACKAGES),
        "cost_estimate_usd": 0.30 + shots * 0.000425,
        "price_reference": "https://aws.amazon.com/braket/pricing/",
        "price_checked_on": "2026-11-10",
        "artifact_hashes": {
            name: file_hash(record / name)
            for name in ("logical.qpy", "submitted.qpy", "action.json", "request.json")
        },
    }
    # Round-trip numpy scalars before canonical hashing.
    write_json(record / "prepared.json", prepared)
    prepared = read_json(record / "prepared.json")
    write_json(
        record / "journal.json",
        {
            "prepared_hash": record_hash(prepared),
            "status": "prepared",
            "task_arn": None,
        },
    )
    return {
        "record": str(record),
        "status": "prepared",
        "tasks_submitted": 0,
        "cost_estimate_usd": prepared["cost_estimate_usd"],
        "local_check": payload["local_check"],
    }


class AWSClient:
    """Small boto3 boundary: explicit credentials chain, no managed compute or bucket creation."""

    def __init__(self, profile=None):
        import boto3
        from botocore.config import Config

        self.session = boto3.Session(profile_name=profile, region_name=REGION)
        # Persist ambiguous attempts rather than repeatedly submitting on HTTP errors.
        self.braket = self.session.client(
            "braket", config=Config(retries={"total_max_attempts": 1})
        )
        self.s3 = self.session.client("s3")

    def identity(self):
        """Return identity, never credential values."""
        response = self.session.client("sts").get_caller_identity()
        return {k: response[k] for k in ("Account", "Arn")}

    def device(self, arn):
        """Get full raw properties without needing SDK schema support."""
        return self.braket.get_device(deviceArn=arn)

    def check_bucket(self, bucket):
        """Verify access and same-region location; never create a bucket."""
        self.s3.head_bucket(Bucket=bucket)
        location = self.s3.get_bucket_location(Bucket=bucket)["LocationConstraint"]
        if (location or "us-east-1") != REGION:
            raise ValueError(f"Use an S3 bucket in {REGION}")

    def create(self, request):
        """The only method that creates a paid task."""
        return self.braket.create_quantum_task(**request)["quantumTaskArn"]

    def task(self, arn):
        """Read task state and provenance."""
        return self.braket.get_quantum_task(quantumTaskArn=arn)

    def result(self, metadata):
        """Download the exact result payload from the task's S3 location."""
        response = self.s3.get_object(
            Bucket=metadata["outputS3Bucket"],
            Key=metadata["outputS3Directory"].rstrip("/") + "/results.json",
        )
        return response["Body"].read().decode("utf-8")


def preflight(record, client):
    """Read-only AWS checks and a full property snapshot; never submit."""
    prepared, _ = load(record)
    request = read_json(Path(record) / "request.json")
    identity = client.identity()
    client.check_bucket(request["outputS3Bucket"])
    device = client.device(prepared["device_arn"])
    snapshot = {
        "captured_at": now(),
        "identity": identity,
        "raw": device,
        "profile": data.profile_summary(device),
    }
    write_json(Path(record) / "preflight.json", snapshot)
    if device["deviceArn"] != prepared["device_arn"] or device.get("deviceType") != "QPU":
        raise ValueError("Device identity/type does not match the Rigetti plan")
    if device["deviceStatus"] != "ONLINE":
        raise ValueError("Device is not ONLINE; snapshot saved, nothing submitted")
    props = json.loads(device["deviceCapabilities"])
    action = (props.get("action") or {}).get("braket.ir.openqasm.program")
    if not action:
        raise ValueError("Device does not advertise OpenQASM support")
    unsupported = set(prepared["braket_operations"]) - {
        op.lower() for op in action.get("supportedOperations", [])
    }
    if unsupported:
        raise ValueError(f"Device does not support submitted operations: {sorted(unsupported)}")
    minimum, maximum = props["service"]["shotsRange"]
    if not minimum <= prepared["shots"] <= maximum:
        raise ValueError("Shots are outside the live device's supported range")
    if prepared["logical_features"]["num_qubits"] > props["paradigm"]["qubitCount"]:
        raise ValueError("Circuit exceeds live device qubit capacity")
    return snapshot


def submit(record, client):
    """Submit once, saving intent before calling AWS and ARN before anything else."""
    record = Path(record)
    with locked(record):
        _, journal = load(record)
        if journal["task_arn"]:
            return {
                "status": journal["status"],
                "task_arn": journal["task_arn"],
                "tasks_submitted": 0,
            }
        if journal["status"] != "prepared":
            raise ValueError(
                "Ambiguous prior submission: reconcile via recover --task-arn; do not resubmit"
            )
        snapshot = preflight(record, client)
        write_json(record / "profile_at_submission.json", snapshot)
        journal.update(
            status="submitting",
            submission_started_at=now(),
            account_id=snapshot["identity"]["Account"],
        )
        write_json(record / "journal.json", journal)
        try:
            arn = client.create(read_json(record / "request.json"))
        except Exception as exc:
            journal.update(status="submission_unknown", error=str(exc))
            write_json(record / "journal.json", journal)
            raise
        journal.update(status="submitted", task_arn=arn, submitted_at=now())
        write_json(record / "journal.json", journal)
        return {"status": "submitted", "task_arn": arn, "tasks_submitted": 1}


def validate_task(metadata, prepared, request, account_id):
    """Reject recovery of an unrelated task, including unknown-submission reconciliation."""
    arn = metadata["quantumTaskArn"]
    if arn.split(":")[3:5] != [prepared["region"], account_id]:
        raise ValueError("Task account or region differs from submission identity")
    if (
        metadata["deviceArn"] != prepared["device_arn"]
        or metadata["shots"] != prepared["shots"]
        or metadata.get("tags", {}).get("qward-run-id") != prepared["run_id"]
        or metadata["outputS3Bucket"] != request["outputS3Bucket"]
    ):
        raise ValueError("Task provenance differs from the frozen request")


def recover(record, client, task_arn=None):
    """Check once and retrieve completed results. Re-run for queued/running tasks."""
    record = Path(record)
    with locked(record):
        prepared, journal = load(record)
        arn = journal["task_arn"] or task_arn
        if not arn or journal["status"] == "prepared":
            raise ValueError("No submitted task to recover")
        if task_arn and journal["task_arn"] and task_arn != journal["task_arn"]:
            raise ValueError("Task ARN differs from the saved task")
        if journal["status"] == "completed":
            return {"status": "completed", "task_arn": arn, "result": str(record / "result.json")}
        metadata = client.task(arn)
        request = read_json(record / "request.json")
        validate_task(metadata, prepared, request, journal["account_id"])
        if metadata["quantumTaskArn"] != arn:
            raise ValueError("Returned task ARN differs from requested task")
        write_json(record / "task_metadata.json", metadata)
        journal.update(task_arn=arn, task_status=metadata["status"], checked_at=now())
        journal["status"] = "submitted"
        write_json(record / "journal.json", journal)
        if metadata["status"] in {"FAILED", "CANCELLED"}:
            journal.update(status=metadata["status"].lower(), error=metadata.get("failureReason"))
            write_json(record / "journal.json", journal)
            return journal
        if metadata["status"] != "COMPLETED":
            return {"status": metadata["status"], "task_arn": arn, "tasks_submitted": 0}
        raw_text = client.result(metadata)
        # Preserve the exact provider response even if decoding/evaluation fails.
        raw_path = record / "raw_result.json"
        with raw_path.open("w", encoding="utf-8") as stream:
            stream.write(raw_text)
            stream.flush()
            os.fsync(stream.fileno())
        raw = json.loads(raw_text)
        task = raw["taskMetadata"]
        if (
            task["id"] != arn
            or task["deviceId"] != prepared["device_arn"]
            or task["shots"] != prepared["shots"]
        ):
            raise ValueError("Result identity differs from requested task")
        returned_action = raw["additionalMetadata"]["action"]
        frozen_action = json.loads(request["action"])
        if (
            returned_action.get("source") != frozen_action["source"]
            or returned_action.get("braketSchemaHeader") != frozen_action["braketSchemaHeader"]
            or (returned_action.get("inputs") or {}) != (frozen_action.get("inputs") or {})
        ):
            raise ValueError("Returned action differs from the frozen OpenQASM program")
        counts = data.decode_result(raw, prepared)
        with (record / "logical.qpy").open("rb") as stream:
            logical = qpy.load(stream)[0]
        result = data.evaluate(counts, prepared, logical)
        result.update(task_arn=arn, recovered_at=now(), raw_result_sha256=file_hash(raw_path))
        write_json(record / "result.json", result)
        # This snapshot is observed at retrieval, not necessarily at execution.
        try:
            device = client.device(prepared["device_arn"])
            snapshot = {
                "captured_at": now(),
                "raw": device,
                "profile": data.profile_summary(device),
            }
        except Exception as exc:
            snapshot = {"captured_at": now(), "available": False, "error": str(exc)}
        write_json(record / "profile_at_retrieval.json", snapshot)
        journal.update(
            status="completed", completed_at=now(), result_hash=file_hash(record / "result.json")
        )
        write_json(record / "journal.json", journal)
        return {
            "status": "completed",
            "task_arn": arn,
            "success_rate": result["success_rate"],
            "result": str(record / "result.json"),
        }


def export(record, ibm_root=PAPERS):
    """Export a comparable row per task and matched IBM repetitions, without changing v2."""
    from experiments.dataset_export import flatten

    record = Path(record)
    prepared, journal = load(record)
    if journal["status"] != "completed":
        raise ValueError("Recover a completed task before exporting")
    if file_hash(record / "result.json") != journal["result_hash"]:
        raise ValueError("Result integrity check failed")
    result = read_json(record / "result.json")
    rows = []

    def add_row(provider, device, job_id, counts, when, *, settings):
        with (record / "logical.qpy").open("rb") as stream:
            logical = qpy.load(stream)[0]
        evaluated = data.evaluate(counts, prepared, logical)
        row = {
            "provider": provider,
            "backend": device,
            "job_id": job_id,
            "config_id": prepared["config_id"],
            "execution_finished_at": when,
            "logical_circuit_hash": prepared["logical_circuit_hash"],
            "optimization_level": prepared["optimization_level"],
            "seed_transpiler": prepared["seed_transpiler"],
            **settings,
        }
        flatten(evaluated, "result", row)
        rows.append(row)

    add_row(
        "aws",
        prepared["device_arn"],
        journal["task_arn"],
        result["counts"],
        read_json(record / "task_metadata.json").get("endedAt"),
        settings={
            "compiler_policy": prepared["compiler_policy"],
            "collected_at": result["recovered_at"],
        },
    )
    skipped = []
    from experiments.campaign_matrix import RUNNERS

    directory = Path(ibm_root) / RUNNERS[prepared["algorithm"]]["dir"] / "data" / "qpu" / "v2"
    for path in sorted(directory.glob("*.json")):
        other = read_json(path)
        if other.get("config_id") != prepared["config_id"] or not other.get("artifact_directory"):
            continue
        frozen = read_json(path.parent / other["artifact_directory"] / "prepared.json")
        reason = None
        if frozen.get("logical_circuit_hash") != prepared["logical_circuit_hash"]:
            reason = "logical_circuit_hash_mismatch"
        elif frozen.get("shots") != prepared["shots"]:
            reason = "shots_mismatch"
        elif frozen.get("optimization_level") != prepared["optimization_level"]:
            reason = "optimization_level_mismatch"
        elif frozen.get("seed_transpiler") != prepared["seed_transpiler"]:
            reason = "seed_transpiler_mismatch"
        if reason:
            skipped.append({"record": str(path), "reason": reason})
            continue
        entries = {entry.get("job_id"): entry for entry in other.get("submission_journal", [])}
        for item in other.get("individual_results", []):
            counts = item.get("counts", {})
            if sum(counts.values()) != prepared["shots"]:
                skipped.append({"record": str(path), "reason": "incomplete_counts"})
                continue
            entry = entries.get(item["job_id"], {})
            stamps = (entry.get("execution_metrics") or {}).get("timestamps") or {}
            add_row(
                "ibm",
                other["backend_name"],
                item["job_id"],
                counts,
                stamps.get("finished"),
                settings={
                    "compiler_policy": "IBM backend-targeted transpilation",
                    "record_path": str(path),
                    "window": other["window"],
                    "campaign_id": other["campaign_id"],
                    "collected_at": entry.get("collected_at"),
                },
            )
    columns = sorted({key for row in rows for key in row})
    with (record / "comparison.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "rows": len(rows),
        "ibm_matches": len(rows) - 1,
        "skipped": skipped,
        "interpretation": "Descriptive comparison; compiler/device/date differ. One AWS repetition.",
        "native_isa_comparable": False,
    }
    write_json(record / "comparison_report.json", report)
    return report


def main(argv=None):
    """CLI with explicit paid submission and otherwise offline/read-only stages."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="Offline: freeze and locally verify one task")
    prep.add_argument("--out", type=Path, required=True)
    prep.add_argument("--bucket", required=True, help="Existing Braket result bucket in us-west-1")
    prep.add_argument("--prefix", default="qward/pilot")
    prep.add_argument("--algorithm", choices=data.ALGORITHMS, default="bv")
    prep.add_argument("--config", default="BV3-ALT")
    prep.add_argument("--shots", type=int, default=1024)
    for name, help_text in (
        ("preflight", "Read-only AWS identity, bucket, device, and calibration checks"),
        ("submit", "PAID: submit the one frozen task; return its ARN without polling"),
        ("recover", "Read-only: check/retrieve an existing task once"),
        ("export", "Offline: write comparison.csv against matching IBM repetitions"),
    ):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--record", type=Path, required=True)
        if name != "export":
            sub.add_argument(
                "--profile", help="AWS credential profile; default credential chain otherwise"
            )
        if name == "recover":
            sub.add_argument(
                "--task-arn", help="Reconcile an uncertain submission with its verified ARN"
            )
        if name == "export":
            sub.add_argument("--ibm-root", type=Path, default=PAPERS)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(
                args.out,
                bucket=args.bucket,
                prefix=args.prefix,
                algorithm=args.algorithm,
                config_id=args.config,
                shots=args.shots,
            )
        elif args.command == "export":
            with locked(args.record):
                result = export(args.record, args.ibm_root)
        else:
            client = AWSClient(args.profile)
            if args.command == "preflight":
                with locked(args.record):
                    snapshot = preflight(args.record, client)
                result = {
                    "status": "ready",
                    "device": snapshot["profile"]["name"],
                    "account": snapshot["identity"]["Account"],
                    "profile_coverage": snapshot["profile"]["coverage"],
                    "execution_windows": snapshot["profile"]["service"].get("executionWindows"),
                    "tasks_submitted": 0,
                }
            elif args.command == "submit":
                result = submit(args.record, client)
            else:
                result = recover(args.record, client, args.task_arn)
    except Exception as exc:
        parser.exit(1, f"{type(exc).__name__}: {exc}\n")
    print(json.dumps(result, indent=2, default=json_value, allow_nan=False))
    if result.get("status") in {"failed", "cancelled"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
