// Definitions follow the QWARD metric implementations used to create the training tables.
// Logical (a.*) and compiled (b.*) fields use the same calculation on different circuits.
const definitions: Record<string, [name: string, meaning: string]> = {
  "BehavioralMetrics.liveness": ["Qubit liveness", "The fraction of qubit–layer positions where a qubit takes part in an operation. Barriers do not count as activity."],
  "BehavioralMetrics.measurement": ["Measurement and reset layers", "The fraction of circuit layers containing at least one measurement or reset. Several measurements in one layer count once."],
  "BehavioralMetrics.parallelism": ["Gate parallelism", "Average gates per layer, scaled from one gate at a time to one per qubit. Values closer to one indicate more gates scheduled together."],
  "BehavioralMetrics.critical_depth": ["Critical-path two-qubit fraction", "The share of all two-qubit operations on a longest dependency path. Those operations must occur in sequence."],
  "ComplexityMetrics.entanglement_metrics.entangling_width": ["Entangling width", "An estimate of how many qubits two-qubit gates could connect. QWARD uses the smaller of the circuit width and one plus the two-qubit gate count."],
  "ComplexityMetrics.entanglement_metrics.entangling_gate_density": ["Entangling gate density", "The number of recognized two-qubit gates divided by circuit size. It describes how often the circuit uses that class of gate."],
  "ComplexityMetrics.gate_based_metrics.multi_qubit_ratio": ["Multi-qubit gate ratio", "The share of circuit operations remaining after single-qubit gates and noncomputational operations are removed from the numerator."],
  "ComplexityMetrics.standardized_metrics.gate_density": ["Gate density", "Total recorded operations divided by width × depth. This gives the average operation count per qubit per layer."],
  "ComplexityMetrics.standardized_metrics.circuit_volume": ["Circuit volume", "Circuit width multiplied by depth. It counts the qubit–layer positions across the circuit."],
  "ComplexityMetrics.derived_metrics.square_ratio": ["Width–depth balance", "The smaller of width and depth divided by the larger. A value of one means the circuit is as wide as it is deep."],
  "ElementMetrics.percent_qm": ["Measured qubit fraction", "The fraction of circuit qubits that are measured at least once."],
  "ElementMetrics.percent_single_gates": ["Single-qubit gate fraction", "The count of single-qubit gates divided by the total gate count."],
  "QiskitMetrics.instruction_metrics.num_nonlocal_gates": ["Nonlocal gate count", "The number of gates acting on two or more qubits."],
  "StructuralMetrics.difficulty": ["Halstead difficulty", "Half the number of distinct operator types multiplied by the average number of uses per distinct operand."],
  "StructuralMetrics.effort": ["Halstead effort", "Halstead difficulty multiplied by Halstead volume. Volume combines the total operator and operand occurrences with the logarithm of the vocabulary size."],
  "StructuralMetrics.total_operands": ["Operand occurrences", "The total references to qubits, classical bits and recognized symbolic parameters in the instructions. Repeated references each count."],
  "StructuralMetrics.vocabulary": ["Halstead vocabulary", "The number of distinct operator types plus distinct operands. Using the same operation or operand again leaves the vocabulary size unchanged."],
  "StructuralMetrics.loc_phi6_num_gate_types": ["Distinct gate types", "The number of different gate names in the circuit, excluding measurement, reset and barrier instructions."],
  "quantum_specific.coherence": ["Quantum coherence", "An estimate of the coherence the ideal circuit can create from a diagonal input state. QWARD optimizes the sum of the magnitudes of off-diagonal output density-matrix entries."],
  "quantum_specific.magic": ["Magic proxy", "QWARD optimizes a proxy over diagonal input states by summing the absolute imaginary parts of off-diagonal entries in the ideal output density matrix."],
  "quantum_specific.entanglement_ratio": ["Entanglement ratio", "The fraction of gate operations involving two or more qubits, after excluding measurement, barrier and reset instructions."],
};

export function footprintMetric(feature: string, label: string) {
  const entry = definitions[feature.slice(feature.indexOf(".") + 1)];
  return { name: entry?.[0] ?? label, meaning: entry?.[1] ?? "A definition for this metric is unavailable in this dashboard version." };
}
