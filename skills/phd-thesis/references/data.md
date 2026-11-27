# Data

Snapshot: 2026-11-26 (export of 2,681 rows). Rerun `scripts/data_summary.py` for current numbers.

## The rule for old data

The user regenerated the complete dataset on the latest IBM Heron chips. **All new claims use `THESIS/experiments/dataset_out/` only.**

Older data is *prior evidence*. Cite it through its publications and DataPort DOIs, and never pool it with or train on the new data. This covers:

- `qiskit-qward/qward/examples/papers/*/data/` (IBM Sherbrooke, Brisbane-era runs, Rigetti Ankaa-3)
- `dsr-quantum-validation/data/` and `on-limitation-metrics/data/` (snapshots of the DataPort set)

## Main dataset: `experiments/dataset_out/`

| File | Contents | Key |
|---|---|---|
| `dataset-NNN.csv` | One row per completed QPU job, split into parts of at most 20 MB. Every part repeats the header | `meta.run_id` |
| `dataset_manifest.json` | Ordered parts with row counts and byte sizes. Read the parts in this order | — |
| `references.csv` | Accepted labels and ideal probabilities | `run_id` |
| `calibrations.csv` | Per-run qubit properties, gate operations, measurement maps | `run_id` |
| `schema.json` | Every column with its group, dtype, and non-null count | — |
| `export_report.json` | Skipped records, errors, and warnings from the export | — |

Keep the parts, references, and calibrations from the same export together. Never mix files from different exports.

### Column groups (493 columns)

| Prefix | Meaning | Use in models |
|---|---|---|
| `meta.*` | Identity: algorithm, config, backend, campaign, window, run, job, shots | Grouping only |
| `config.*` | Configuration parameters (qubits, secret, period, ...) | Not a feature |
| `a.*` | Logical circuit metrics (QWARD) | Footprint candidates |
| `b.*` | Transpiled ISA circuit metrics (QWARD, counts, 2Q depth) | Footprint candidates |
| `c.*` | Calibration of the qubits the circuit uses, at submission | "Layout calibration". Carries circuit size |
| `d.*` | Hardware at execution time | Not pre-runtime: do not use as a feature |
| `e.*`, `e_exec.*` | Analytical baselines (M1, M2) at submission or execution | M2 prior for H2 |
| `f.*` | Targets: `f.fidelity.{success_rate,dsr,hellinger_fidelity,tvd,chance_corrected_success,...}`, counts, residuals | Labels only |
| `g.*` | Provenance: seeds, timestamps, queue time, `g.cost_rus`, package versions | Cost target is `g.cost_rus * 60` seconds |

`cal.*` (device calibration) is derived in `experiments/ml_dataset.py`: the median per chip and calibration snapshot, blind to the circuit. Empty means *not computed*, never zero. Each group has `<prefix>.available` and `<prefix>.reason`. The full column documentation is in `docs/ibm_fez_dataset_schema.md`.

### Coverage

| Algorithm | ibm_fez | ibm_kingston | ibm_marrakesh |
|---|---:|---:|---:|
| Bernstein–Vazirani | 284 | 248 | 14 |
| GHZ | 116 | 98 | 8 |
| Grover | 208 | 180 | 6 |
| Phase estimation | 146 | 138 | 12 |
| QFT | 188 | 180 | 18 |
| Random volumetric | 116 | 108 | 18 |
| Shor | 88 | 119 | 2 |
| vTP | 194 | 186 | 6 |

All jobs use 1,024 shots, optimization level 3, and transpiler seed 11. Fez and Kingston share 189 configurations, with about six repetitions each.

### Campaign roles

Every campaign has exactly one role, defined in `experiments/ml_dataset.py` (`campaign_role`):

| Role | Rule | Rows | Use |
|---|---|---:|---|
| `train` | Default for any campaign | 2,409 | Model fitting, footprint selection, tuning |
| `validation` | ID contains `-validation-v` | 252 | Prospective validation only. **Never train on it** |
| `exploratory` | Listed in `EXPLORATORY_CAMPAIGNS` | 20 | One-off studies, such as `fez-ghz-bv-transfer-v1-2026-11-23` |

`load_ml_dataset()` returns only `train` rows unless you pass `include_validation=True` or `roles=`. Marrakesh exists only in validation and is the unseen-QPU test. The abandoned campaign `kingston-validation-v1-2026-11-17` has no QPU results. See `docs/validation-v1-kingston-2026-11-17-abandoned.md`.

### Loading

```python
from pathlib import Path
from experiments.ml_dataset import load_ml_dataset

bundle = load_ml_dataset(Path("experiments/dataset_out"))          # train role only
frame = bundle.frame                                                # pandas DataFrame
bundle.circuit_features, bundle.hardware_submit_features           # feature registries
everything = load_ml_dataset(Path("experiments/dataset_out"), include_validation=True)
```

The frame carries `meta.campaign_role`; assert it equals `{"train"}` when the task says "data we can train on".

The loader validates part sizes against the manifest. Run from the repository root with `PYTHONPATH=.`, or use `python scripts/run.py`. For quick column reads without the loader, use `pandas.read_csv(..., usecols=[...])` over the manifest parts. The full frame is about 290 MB.

### Analysis pitfalls

- **Repeats are not independent.** Each configuration ran about six times per chip (one or two per window). Per-job p-values are far too small. Compute intervals by resampling whole configurations (`meta.config_id`), as the QAQS report does, or aggregate to one value per configuration first.
- **Use the transpiled counts.** The logical `a.*` gate counts miss composite gates: `a.ComplexityMetrics.gate_based_metrics.two_qubit_count` is 0 for every Grover and random-volumetric circuit. For size use `b.two_qubit_gates`, `b.*` depth, and width.
- **Size confounds everything.** Two-qubit count, depth, and width grow together within a sweep, so a correlation with one of them is not that metric's own effect. Compare against the size baseline when claiming a metric matters.
- **Shor sits at chance.** Its success rate has little room to fall. Raw targets in the QAQS report exclude it, and `f.fidelity.chance_corrected_success` (`success_adj`) is the target that scores every job.
- **Dynamic circuits.** vTP S configs have mid-circuit control flow, so the `e.*` baselines (including the M2 prior) and QuantumSpecific metrics are empty for them. Check `<prefix>.available` before averaging.

## Other data in this repository

| Path | Contents |
|---|---|
| `experiments/<algo>/data/qpu/v2/` | Raw job records and artifacts: the export's source. Do not edit by hand |
| `experiments/<algo>/plans/` | Submitted plans per window and date |
| `experiments/data/aws_pilot/` | Braket pilots: `bv3-alt-r1` (Rigetti) and `ionq-sr8-r1` (IonQ). Not in the export yet |
| `experiments/data/quantum_specific_cache/` | Cache for QWARD QuantumSpecific metrics |
| `report/{fez,kingston,marrakesh-validation}/decay/` | Decay analyses |
| `report/ml_estimation/` | Model report, CSVs, `models/*.joblib`, `cost/`, `prospective/` |
| `dashboard/experiments/` | Hash-stamped JSON snapshots that the dashboard ships |
| `migration-manifest.json` | Original QWARD source paths and hashes for migrated code |

## Data identity

Keep original job, task, and run IDs. One raw job can appear in the export and the dashboard; that is one observation, not two. Join on IDs and report backend, calibration and execution times, shots, transpiler policy, accepted outcome set, and reference distribution. Do not infer a cohort from directory presence. Select explicitly by campaign or role.
