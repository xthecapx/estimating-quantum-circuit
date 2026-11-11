# Local AWS Rigetti pilot plan

Prepared 2026-11-10. Scope: plan the first recoverable Rigetti comparison run,
then expand to the compatible portion of the existing IBM pilot. No QPU tasks
have been submitted as part of this planning work.

## Recommendation

Use the existing AWS execution stack and algorithm definitions. Add a small local
Braket campaign entry point with prepare, submit, recover, and export stages.
Keep IBM orchestration intact; do not generalize IBM Batch mechanics into AWS.
The initial milestone is one completed `BV3-ALT` task at 1,024 shots, with a
preserved device snapshot, reproducible circuit artifacts, and an IBM comparison.

Here, “pilot” means window 0 in `campaign_matrix.py`, not the separate calibration
histogram pilot. The IBM pilot is 15 configurations, two executions each (30 jobs).
The first Rigetti milestone deliberately uses one execution of one configuration.

AWS currently lists Rigetti `Cepheus-1-108Q` in `us-west-1`, with device ARN
`arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1-108Q`.
Resolve and verify this device at preflight rather than relying on the repository's
mixed Ankaa-3/Cepheus defaults. [AWS device list](https://docs.aws.amazon.com/braket/latest/developerguide/braket-devices.html)

## Existing pieces and gaps

- `aws_experiment_base.py` and the GHZ, BV, QFT, PE, Grover, and random-volumetric
  AWS runners already supply circuit construction, expected outcomes, and evaluation.
- `executor.py` already supplies Braket submission, retrieval, circuit preparation,
  and count conversion. `setup.py` pins an AWS extra; use it separately from qBraid.
- `ibm_campaign.py` supplies the useful lifecycle pattern: immutable preparation,
  submission journal, recovery, and execution budgets. Its service, Sampler, Batch,
  and backend assumptions are IBM-specific.
- AWS currently writes `data/qpu/aws` results; `dataset_export.py` discovers v2
  journals in `data/qpu/v2`. Existing AWS files do not automatically enter that export.
- `BackendCalibration._extract_aws()` reduces properties to device medians. It
  labels retrieval time as calibration time, silently catches extraction failures,
  and assumes limited unit/schema variants. Preserve raw properties before normalization.
- AWS optimization currently omits `seed_transpiler`; use the IBM pilot's seed 11.
- AWS count extraction reverses raw strings, while the later width correction can
  choose a marginalization based on which gives higher expected-outcome success.
  The pilot must use recorded measurement mappings, never success-based selection.
- The GHZ AWS evaluation override accepts three arguments, while the base calls it
  with four. Fix and regression-test this before including GHZ in the expanded pilot.

## Implementation sequence

### 1. Read-only device preflight and profile capture

Use the normal AWS credential chain, including profiles and temporary credentials.
Accept explicit AWS profile, region, device ARN, and S3 result location. Validate
identity, device status, execution windows, supported operations, shot limits, and
result-storage configuration before preparing a paid submission. Display the exact
device and bounded workload.

Save the complete `GetDevice`/`AwsDevice.properties` payload with capture time,
device ARN, schema headers, and a content hash. Extract without discarding:

| Profile component | Treatment |
| --- | --- |
| Topology, qubit IDs, native gates, supported actions | Preserve directly |
| Per-qubit T1/T2 and readout/1Q fidelity | Preserve values, units, benchmark types, and uncertainty where supplied |
| Per-edge 2Q fidelity | Preserve edge IDs, gate names, benchmark types, and uncertainty |
| Calibration/update time | Use supplied time only; distinguish from `captured_at` |
| Durations, pulse parameters, asymmetric readout errors | Optional; report availability and missingness |

Braket exposes topology and calibration through GetDevice. Its standardized schemas
include per-qubit and per-edge calibration structures, but the schema does not prove
every field is populated on this device. Actual coverage is a preflight deliverable.
[AWS devices](https://docs.aws.amazon.com/braket/latest/developerguide/braket-devices.html),
[Braket calibration schema](https://amazon-braket-schemas-python.readthedocs.io/en/latest/_apidoc/braket.device_schema.standardized_gate_model_qpu_device_properties_v1.html)

Normalize units explicitly and retain missing values with reasons. Do not equate
Rigetti RB-derived infidelity with an IBM instruction error without recording the
different definitions. Do not infer operational status solely from calibration entries.

### 2. Prepare and verify the first circuit locally

Freeze `BV3-ALT`, 1,024 shots, one execution, optimization level 3, and transpiler
seed 11. Reuse the configuration and circuit builder and compare its logical circuit
against the selected IBM record. Persist logical and submitted QPY/program artifacts,
hashes, config, expected outcomes, measurement mapping, package versions, compiler
settings, and logical/submitted circuit metrics.

Exercise the Qiskit-to-Braket conversion locally, including an asymmetric basis-state
probe, a nontrivial classical measurement permutation, and BV's unmeasured ancilla.
Require shot conservation and correct outcome width. A mismatch must fail explicitly;
do not select bits using observed agreement with expected outcomes.

Use ordinary Braket compilation for the first pilot and record that choice. Qiskit
optimization level 3 does not make the two providers' compiled circuits equivalent.
Braket may rewire and compile again; submitted circuit depth is not necessarily final
hardware depth. Preserve returned Rigetti `compiledProgram` and other task metadata.
Only join calibration to used physical qubits if the final mapping is verified.
[Provider compilation guide](https://qiskit-braket-provider.readthedocs.io/en/stable/how_tos/4_how_to_verbatim_circuits.html),
[Rigetti result schema](https://amazon-braket-schemas-python.readthedocs.io/en/stable/_apidoc/braket.task_result.rigetti_metadata_v1.html)

### 3. Add durable local submission and recovery

Implement a narrow `aws_campaign.py` entry point. Persist prepared metadata and
submission intent before network submission; persist the task ARN immediately after
creation, before polling or evaluation. Use a stable Braket idempotency token if the
chosen submission layer supports forwarding it; otherwise reconcile uncertain
submission by task metadata/tags and never blindly resubmit.

The prepared artifact must be the one submitted, without an unrecorded second local
transpilation. Enforce a one-task budget for the initial plan. `recover` only retrieves
an existing ARN and cannot create a task. A polling timeout means pending, not failed.
Test interruption after submission, successful recovery, terminal failure, and repeated
recovery without duplicate records. Keep raw results even if evaluation fails.

Snapshot the device immediately before submission and again at retrieval. Label both
by observation time: neither is guaranteed to describe the calibration at execution
if a task waits in a queue. Keep provider timestamps and task execution timestamps
separately, and report uncertainty rather than inventing execution-time calibration.

### 4. Export and compare

Add AWS support to the v2 journal/export contract with explicit cloud provider,
hardware vendor, device ARN, region, task ARN, compiler stages, and profile coverage.
Retain existing IBM record compatibility. AWS has no IBM Batch ID or IBM usage fields;
leave those unavailable. Keep provider-specific compiled artifacts separately and
avoid presenting submitted Qiskit metrics as verified native ISA metrics.

Match IBM rows by algorithm/config, logical circuit identity, shots, and recorded
compiler policy, retaining device, execution date, and repetition identity. Report
raw counts, success rate with a binomial interval, existing DSR variants, logical
metrics, submitted/native metrics where available, and calibration coverage. Compare
individual IBM repetitions as well as their spread. One Rigetti task establishes an
end-to-end descriptive comparison, not a vendor ranking or drift estimate.

### 5. Expand only after the first result validates

Reuse these existing window-0 configurations:

| Algorithm | Configurations |
| --- | --- |
| GHZ | GHZ3, GHZ10 |
| BV | BV3-ALT, BV8-ONES |
| QFT | SR3, SP6-P4 |
| Phase estimation | PE-T3, PE-S6 |
| Grover | S3-1, M4-2 |
| Random volumetric | RV2-D2, RV4-D4 |

This compatible starting subset is 12 configurations: 12 tasks with one execution
each, or 24 with the IBM pilot's two repetitions. Count the first task toward that
budget if its protocol matches the frozen expanded plan.

Defer VTP and Shor from this first implementation: they lack matching AWS runner
modules. VTP also includes a dynamic circuit. Check device capabilities rather than
silently rewriting it; a static replacement would be a distinct experiment. AWS's
documented dynamic-circuit support is device-specific, including IQM experimental
capabilities, and does not establish Rigetti compatibility.
[AWS dynamic circuits](https://docs.aws.amazon.com/braket/latest/developerguide/braket-experimental-capabilities.html)

## Budget and completion criteria

The listed on-demand Cepheus rate is $0.30/task plus $0.000425/shot. At 1,024 shots:
one task is $0.7352, 12 tasks are $8.8224, and 24 tasks are $17.6448, excluding storage,
tax, and any additional tasks. Recheck pricing at execution. Local simulation and
device inspection do not submit paid quantum tasks.
[AWS pricing](https://aws.amazon.com/braket/pricing/)

The initial milestone is complete when one Rigetti task is recoverable by ARN, its
counts and measurement mapping validate, its profile and artifacts are preserved,
and an export produces a comparison with matching IBM data plus explicit missing
fields. Required tests cover normalization/schema variants, mapping/ancillas,
submission interruption and duplication, and mixed-provider export compatibility.
The expanded pilot and a broader provider abstraction are subsequent work.
