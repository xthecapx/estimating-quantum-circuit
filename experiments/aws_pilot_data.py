# Adapted from QWARD for the thesis experiment namespace and paths.
"""Offline circuit preparation and result decoding for the Rigetti pilot.

Use the IBM campaign's circuit factories and target metrics so comparisons have
the same definitions. Nothing in this module accesses an AWS account.
"""

from collections import Counter
import json
import math

from qiskit import transpile

from experiments import campaign_matrix, dataset_features
from qward.metrics.circuit_error_prediction import circuit_hash

ALGORITHMS = ("bv", "ghz", "qft", "pe", "grover", "rv")
BASIS_GATES = ["rx", "ry", "rz", "cx", "x", "h", "id"]


def measurement_map(circuit):
    """Return classical-bit -> logical-qubit mapping for terminal measurements.

    Reject dynamic circuits, unused classical bits, and repeated measurements.
    Never infer a mapping from expected outcomes or observed success.
    """
    mapping = {}
    seen_measure = False
    for item in circuit.data:
        name = item.operation.name
        if name == "barrier":
            continue
        if name in {"reset", "if_else", "while_loop", "for_loop", "switch_case"}:
            raise ValueError("The Rigetti pilot supports static circuits only")
        if name == "measure":
            seen_measure = True
            q = circuit.find_bit(item.qubits[0]).index
            c = circuit.find_bit(item.clbits[0]).index
            if c in mapping or q in mapping.values():
                raise ValueError("Repeated measurement is unsupported")
            mapping[c] = q
        elif seen_measure:
            raise ValueError("All measurements must be terminal")
    if not mapping or sorted(mapping) != list(range(circuit.num_clbits)):
        raise ValueError("Every classical bit must have exactly one measurement")
    return [mapping[c] for c in range(circuit.num_clbits)]


def normalize_counts(raw_counts, measured_qubits, clbit_to_qubit, shots):
    """Decode Braket columns into Qiskit classical-bit order, preserving shots."""
    if len(set(measured_qubits)) != len(measured_qubits):
        raise ValueError("Duplicate measured qubits in result")
    if set(measured_qubits) != set(clbit_to_qubit):
        raise ValueError("Result measured qubits differ from frozen measurement mapping")
    columns = [measured_qubits.index(q) for q in reversed(clbit_to_qubit)]
    counts = Counter()
    for label, count in raw_counts.items():
        if len(label) != len(measured_qubits) or set(label) - {"0", "1"}:
            raise ValueError("Invalid measurement width or non-binary outcome")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("Counts must be nonnegative integers")
        counts["".join(label[i] for i in columns)] += count
    if sum(counts.values()) != shots:
        raise ValueError("Returned shot count differs from the frozen request")
    return dict(counts)


def decode_result(raw, prepared):
    """Decode the original Rigetti result.json, retaining raw data separately."""
    rows = raw.get("measurements")
    measured = raw.get("measuredQubits")
    if not isinstance(rows, list) or not isinstance(measured, list):
        raise ValueError("Rigetti result is missing measurements/measuredQubits")
    raw_counts = Counter()
    for row in rows:
        if len(row) != len(measured) or any(
            not isinstance(b, int) or isinstance(b, bool) or b not in (0, 1) for b in row
        ):
            raise ValueError("Invalid raw measurement row")
        raw_counts["".join(map(str, row))] += 1
    return normalize_counts(raw_counts, measured, prepared["clbit_to_qubit"], prepared["shots"])


def translate(circuit, optimization_level=3, seed=11):
    """Compile to portable gates, then freeze Braket's exact OpenQASM action.

    No physical layout is chosen locally. Rigetti performs hardware compilation
    and rewiring. The intermediate Qiskit circuit is explicitly not native ISA.
    """
    from braket.circuits.serialization import IRType
    from qiskit_braket_provider.providers.adapter import to_braket

    measurement_map(circuit)
    compiled = transpile(
        circuit,
        basis_gates=BASIS_GATES,
        optimization_level=optimization_level,
        seed_transpiler=seed,
    )
    # Retain barriers during optimization, as IBM does. In particular, removing
    # them first can cancel an entire random-volumetric mirror experiment.
    compiled.data = [i for i in compiled.data if i.operation.name != "barrier"]
    # Optimization can remove terminal SWAPs by permuting measurements. Freeze
    # the submitted mapping, not the original circuit's qubit numbering.
    mapping = measurement_map(compiled)
    braket_circuit = to_braket(
        compiled, basis_gates=BASIS_GATES, optimization_level=0, seed_transpiler=seed
    )
    translated_mapping = [
        int(i.target[0]) for i in braket_circuit.instructions if i.operator.name == "Measure"
    ]
    if translated_mapping != mapping:
        raise ValueError("Braket adapter changed the compiled measurement mapping")
    action = json.loads(braket_circuit.to_ir(IRType.OPENQASM).json())
    return compiled, braket_circuit, action


def verify_locally(braket_circuit, action, mapping, reference, shots):
    """Check exact output probabilities and execute the frozen QASM locally."""
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator
    from braket.ir.openqasm import Program

    unitary = Circuit([i for i in braket_circuit.instructions if i.operator.name != "Measure"])
    unitary.probability(target=mapping)
    probabilities = LocalSimulator().run(unitary, shots=0).result().values[0]
    actual = {format(i, f"0{len(mapping)}b")[::-1]: float(p) for i, p in enumerate(probabilities)}
    expected = {key.replace(" ", ""): p for key, p in reference.items()}
    error = max(abs(actual.get(k, 0) - expected.get(k, 0)) for k in actual.keys() | expected.keys())
    if error > 1e-8:
        raise ValueError(f"Braket conversion changed the ideal distribution: max error {error}")
    sampled = LocalSimulator().run(Program(**action), shots=shots).result()
    counts = normalize_counts(
        dict(sampled.measurement_counts), list(sampled.measured_qubits), mapping, shots
    )
    return {"max_probability_error": error, "shots": shots, "counts": counts}


def build_pilot(algorithm, config_id, shots):
    """Reuse window-0 configs and freeze all evaluation inputs for recovery."""
    if algorithm not in ALGORITHMS or config_id not in campaign_matrix.PILOT[algorithm]:
        raise ValueError("Select a supported window-0 pilot configuration")
    runner = campaign_matrix.load_runner(algorithm)  # Factory only; no IBM service.
    config = runner.get_config(config_id)
    logical = runner.create_circuit(config)
    logical_mapping = measurement_map(logical)
    reference = runner.get_reference(config)
    success_set = dataset_features.success_labels(logical, runner.create_success_criteria(config))
    compiled, braket_circuit, action = translate(logical)
    mapping = measurement_map(compiled)
    local_check = verify_locally(braket_circuit, action, mapping, reference, shots)
    payload = {
        "algorithm": algorithm,
        "algorithm_name": runner.algorithm_name,
        "config_id": config_id,
        "config": runner.get_config_description(config),
        "logical_circuit_hash": circuit_hash(logical),
        "clbit_to_qubit": mapping,
        "logical_clbit_to_qubit": logical_mapping,
        "reference": reference,
        "success_set": success_set,
        "optimization_level": 3,
        "seed_transpiler": 11,
        "compiler_policy": "Qiskit portable basis opt=3; adapter opt=0; Rigetti rewiring enabled",
        "native_isa_available": False,
        "physical_mapping": None,
        "logical_features": dataset_features.logical_features(
            logical, include_quantum_specific=False
        ),
        "submitted_qiskit_features": dataset_features.isa_features(compiled),
        "braket_operations": sorted(
            {
                i.operator.name.lower()
                for i in braket_circuit.instructions
                if i.operator.name != "Measure"
            }
        ),
        "local_check": local_check,
    }
    return logical, compiled, action, payload


def evaluate(counts, prepared, logical):
    """Use the same target metric definitions as the IBM dataset."""
    targets = dataset_features.targets(
        counts, logical, prepared["reference"], success_set=prepared["success_set"]
    )
    successes = sum(counts.get(k.replace(" ", ""), 0) for k in prepared["success_set"])
    n = sum(counts.values())
    p, z = successes / n, 1.959963984540054
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return {
        "counts": counts,
        "shots": n,
        "success_rate": p,
        "success_interval_95_wilson": [max(0, center - half), min(1, center + half)],
        "targets": targets,
    }


def profile_summary(device):
    """Preserve detailed calibration, with explicit units and missingness.

    The complete GetDevice response is also saved. Do not interpret observation
    time as calibration time, or fidelity benchmarks as IBM instruction errors.
    """
    props = json.loads(device["deviceCapabilities"])
    standardized = props.get("standardized") or {}
    one = standardized.get("oneQubitProperties") or {}
    two = standardized.get("twoQubitProperties") or {}
    durations = {}
    unit_scale = {"s": 1e6, "ms": 1e3, "us": 1, "µs": 1, "ns": 1e-3}
    for qubit, values in one.items():
        durations[qubit] = {}
        for field in ("T1", "T2"):
            entry = values.get(field) or {}
            value, unit = entry.get("value"), entry.get("unit")
            supported = value is not None and unit in unit_scale
            durations[qubit][field] = {
                "value_us": value * unit_scale[unit] if supported else None,
                "reason": None if supported else "missing_value_or_unsupported_unit",
            }
    return {
        "device_arn": device["deviceArn"],
        "name": device.get("deviceName"),
        "status": device["deviceStatus"],
        "calibrated_at": None,
        "calibrated_at_reason": "No provider timestamp normalized; inspect raw properties",
        "paradigm": props.get("paradigm"),
        "service": props.get("service"),
        "standardized": standardized,
        "provider": props.get("provider"),
        "coherence_us": durations,
        "coverage": {
            "qubits_with_standardized_properties": len(one),
            "edges_with_standardized_properties": len(two),
        },
    }
