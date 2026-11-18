"""Summarize which chip fields were actually returned for the SR8 hardware pilot."""

from pathlib import Path

from experiments import aws_campaign as aws
from experiments.campaign_matrix import PAPERS


def braket_fields(record):
    prepared = aws.read_json(record / "prepared.json")
    raw = aws.read_json(record / "raw_result.json")
    extra = raw.get("additionalMetadata") or {}
    snapshots = {}
    for filename in ("profile_at_submission.json", "profile_at_retrieval.json"):
        snapshot = aws.read_json(record / filename)
        if "raw" not in snapshot:
            snapshots[filename] = snapshot
            continue
        profile = snapshot["profile"]
        provider = profile.get("provider") or {}
        paradigm = profile.get("paradigm") or {}
        standardized = profile.get("standardized") or {}
        snapshots[filename] = {
            "standardized_fields": {
                name: sorted(
                    {field for item in (standardized.get(name) or {}).values() for field in item}
                )
                for name in ("oneQubitProperties", "twoQubitProperties")
            },
            "captured_at": snapshot["captured_at"],
            "device_service_updated_at": (profile.get("service") or {}).get("updatedAt"),
            "qubit_count": paradigm.get("qubitCount"),
            "fully_connected": (paradigm.get("connectivity") or {}).get("fullyConnected"),
            "native_gate_set": paradigm.get("nativeGateSet"),
            "provider_fields": sorted(provider),
            "provider_fidelity": provider.get("fidelity"),
            "provider_timing": provider.get("timing"),
            **profile["coverage"],
        }
    return {
        "device": prepared["device_arn"],
        "config": prepared["config_id"],
        "shots": prepared["shots"],
        "snapshots": snapshots,
        "result_metadata_fields": {
            key: sorted(value) if isinstance(value, dict) else None
            for key, value in extra.items()
            if key != "action"
        },
        "raw_measurement_fields": [
            key
            for key in ("measuredQubits", "measurements", "measurementProbabilities")
            if raw.get(key) is not None
        ],
    }


def write_inventory(record):
    """Use one archived submission per IBM chip to document field coverage."""
    rigetti = PAPERS / "data/aws_pilot/bv3-alt-r1"
    chips = {}
    for journal_path in sorted((PAPERS / "qft/data/qpu/v2").glob("SR8_IBM_*.json")):
        journal = aws.read_json(journal_path)
        chip = journal["backend_name"]
        if chip in chips or not journal.get("individual_results"):
            continue
        artifact = journal_path.parent / journal["artifact_directory"] / "prepared.json"
        prepared = aws.read_json(artifact)
        snapshot = prepared["calibration_snapshot"]
        chips[chip] = {
            "source_relative_to_experiments": str(artifact.relative_to(PAPERS)),
            "config": prepared["config_id"],
            "shots": prepared["shots"],
            "calibrated_at": snapshot.get("calibrated_at"),
            "collected_at": snapshot.get("collected_at"),
            "physical_layout": prepared.get("physical_layout"),
            "qubit_fields": sorted({k for q in snapshot["qubits"].values() for k in q}),
            "hardware_at_submission": prepared["payload"]["features"]["hardware_at_submission"],
        }
    report = {
        "ionq": braket_fields(record),
        "archived_rigetti": braket_fields(rigetti),
        "archived_ibm_sr8_examples": chips,
        "interpretation": [
            "The Rigetti BV3-ALT record supports a field-coverage comparison. IBM SR8 records also support a same-circuit outcome comparison.",
            "Device-wide fidelity and timing, per-qubit/per-edge benchmarks, and IBM instruction errors have different scopes. Preserve provider definitions and units.",
            "Braket snapshots describe the times of observation. Service updatedAt describes the device record. Execution-time calibration and physical layout require explicit provider evidence.",
            "Missing provider fields are null. See raw_result.json and both full device snapshots for unmodified provider details.",
        ],
    }
    out = Path(record) / "chip_inventory.json"
    aws.write_json(out, report)
    return out
