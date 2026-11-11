# Run the Rigetti pilot locally

The entry point is `python -m experiments.aws_campaign`. It prepares
**one task per run directory**, defaulting to the existing IBM pilot's `BV3-ALT`
configuration at 1,024 shots. Only `submit` creates a paid task. No workflow,
AWS managed job, or automatic batch submission is involved.

## Setup

From the repository root, install the existing AWS dependency extra:

```bash
uv sync --extra aws
```

Keep the `qbraid` extra out of this environment: its Braket dependencies conflict
with the direct AWS stack. The repository pins `qiskit-braket-provider==0.23.2`
and `amazon-braket-sdk==1.126.1`. Each prepared record saves the actual installed
versions. If using pip in a dedicated environment, use `python -m pip install -e '.[aws]'`.

Use your normal AWS credential chain or pass `--profile YOUR_PROFILE` on the AWS
commands. Temporary credentials and SSO profiles work through boto3; the script
does not read or save secret keys. Supply an existing result bucket in `us-west-1`.
The code never creates a bucket or changes IAM. Its cloud operations are STS
GetCallerIdentity, S3 HeadBucket/GetBucketLocation/GetObject, and Braket
GetDevice/CreateQuantumTask/GetQuantumTask. Task tags may also require tagging
permission under your account's IAM policy. S3/KMS policies must permit Braket
result delivery and your retrieval; read-only preflight cannot prove write access.

## Prepare and review without contacting AWS

Replace `YOUR_BRAKET_BUCKET` with the bucket name (no `s3://` prefix):

```bash
uv run --extra aws -m experiments.aws_campaign prepare \
  --out experiments/data/aws_pilot/bv3-alt-r1 \
  --bucket YOUR_BRAKET_BUCKET
```

Preparation performs exact local probability checks against the original circuit's
ideal reference, then executes the saved OpenQASM program on the local Braket
simulator. Inspect these files before submitting:

- `prepared.json`: configuration, success labels, reference distribution, circuit
  metrics, compiler settings, original/compiled measurement mappings, package
  versions, hashes, local verification, and cost estimate.
- `action.json`: exact OpenQASM program.
- `request.json`: complete immutable CreateQuantumTask request, including device
  ARN, shots, S3 destination, stable client token, and run-identifying tags.
- `logical.qpy`, `submitted.qpy`: logical and intermediate Qiskit circuits.
- `journal.json`: current lifecycle state and, after submission, the task ARN.

The fixed target is Rigetti Cepheus-1-108Q in `us-west-1`. The first task is bounded
to at most 1,024 shots. Its estimated on-demand cost at the recorded 2026-11-10 rate
is $0.7352, excluding storage/tax. Check current pricing before running a new
campaign. [AWS pricing](https://aws.amazon.com/braket/pricing/)

## Read the live QPU profile

```bash
uv run --extra aws -m experiments.aws_campaign preflight \
  --record experiments/data/aws_pilot/bv3-alt-r1
```

This is read-only AWS access. `preflight.json` contains the full GetDevice response,
capture time, account identity, topology/native gate information, standardized
per-qubit/per-edge calibration, and provider-specific properties. T1/T2 values
are additionally normalized to microseconds when the units are known. Unavailable
properties remain absent or explicitly missing, rather than zero-filled.

Preflight validates device identity/status, OpenQASM operations, shot/qubit limits,
and S3 bucket region/access. Execution windows are displayed; a device marked
ONLINE may still queue the task until its execution window opens. Profile data
and observation time are preserved without claiming to know the actual
execution-time calibration.

## Submit manually after review

```bash
uv run --extra aws -m experiments.aws_campaign submit \
  --record experiments/data/aws_pilot/bv3-alt-r1
```

This is the paid step. It repeats preflight, freezes `profile_at_submission.json`,
writes submission intent, sends the saved request, immediately persists the ARN,
and exits without polling. Repeating it after a saved ARN returns the existing
task and submits nothing. Use the same run directory for recovery.

If AWS accepted the task but the response was lost, the journal stays `submitting`
or `submission_unknown`. The script refuses to submit again. Find the task in the
Braket console using the `qward-run-id` tag from `prepared.json`, then reconcile:

```bash
uv run --extra aws -m experiments.aws_campaign recover \
  --record experiments/data/aws_pilot/bv3-alt-r1 \
  --task-arn 'arn:aws:braket:us-west-1:ACCOUNT:quantum-task/TASK_ID'
```

Account, region, device, shots, bucket, and run tag must match before the ARN is
accepted. Do not delete the journal or prepare another paid run to recover a
lost response. A copied run directory retains the same request/token and identity;
a deliberate new repetition requires a fresh `prepare` directory.

## Retrieve and compare

```bash
uv run --extra aws -m experiments.aws_campaign recover \
  --record experiments/data/aws_pilot/bv3-alt-r1

uv run --extra aws -m experiments.aws_campaign export \
  --record experiments/data/aws_pilot/bv3-alt-r1
```

Recovery checks once. If QUEUED/RUNNING, run it again later. It never submits,
replaces, or cancels a task. Failed/cancelled tasks are preserved and reported.
Completed tasks produce the exact `raw_result.json`, `task_metadata.json`, evaluated
`result.json`, and `profile_at_retrieval.json`. Raw data is saved before decoding;
any measurement or metric issue remains recoverable. Returned Rigetti compiled
program metadata is retained in the raw result.

`comparison.csv` contains the Rigetti row and matching IBM repetitions from the
repository. Matching requires config, logical circuit hash, shots, optimization
level, and transpiler seed. `comparison_report.json` reports exclusions and the
number of matches, including zero. Success rate, a 95% Wilson interval, fidelity,
DSR, and histogram metrics use shared IBM target definitions and frozen success
labels. IBM repetitions stay separate. `--ibm-root` can select a different papers
directory. This pilot export is separate from the strict IBM v2 dataset/dashboard;
it does not fabricate IBM hardware/error-prediction fields for Rigetti.

## Supported expansion and interpretation

Select one configuration per prepared run using `--algorithm` and `--config`:

| Algorithm | Window-0 configurations |
| --- | --- |
| bv | BV3-ALT, BV8-ONES |
| ghz | GHZ3, GHZ10 |
| qft | SR3, SP6-P4 |
| pe | PE-T3, PE-S6 |
| grover | S3-1, M4-2 |
| rv | RV2-D2, RV4-D4 |

For example, add `--algorithm ghz --config GHZ3` to a new prepare command.
VTP and Shor are excluded from this initial runner. There is no `all` option.

Local optimization uses level 3 and seed 11 in a portable gate basis. Barriers
are retained during Qiskit optimization and removed before Braket translation.
The exact submitted action is verified locally, but Rigetti then performs native
compilation/rewiring. Submitted depth is not native hardware depth; native physical
mapping is not inferred. In particular, mirror circuits can be simplified by the
remote compiler. Inspect compiled metadata before interpreting RV as a depth/noise
benchmark. One task gives a descriptive result, not a vendor ranking.

`BV3-ALT` has palindromic expected output `101`; separate asymmetric, permuted
measurement and ancilla tests verify the decoder without extra QPU tasks.

Run the offline tests with:

```bash
uv run --extra aws python -m pytest tests/test_aws_campaign.py -q
```

Install pytest in the environment if it is not already available. Tests use local
simulation and fake AWS clients; they do not require account credentials.
