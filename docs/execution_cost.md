# QAQS execution-cost model

Predicts the billed QPU time of a job, in IBM resource units, before it is submitted.
Code: `experiments/qaqs_cost.py`. Dashboard: **Execution cost** tab.

## What IBM bills

Each recovered job carries IBM's usage report (`execution_metrics.usage`):

| Exported column | Source | Meaning |
| --- | --- | --- |
| `g.cost_rus` | `usage.value` (`unit = resource_units`) | Billed QPU time in RU; 1 RU = 1 minute of QPU time |
| `g.billed_seconds` | `usage.qpu_charge_time_seconds` | The same time, rounded up to whole seconds |
| `g.circuit_execution_seconds` | `circuits_execution_time_ns` | Time spent executing the circuit itself |
| `g.quantum_seconds` | `usage.quantum_seconds` | Older usage format: whole seconds only |

2,277 of 2,681 jobs have the RU report. The 404 oldest Fez jobs (`fez-dataset-v2` and its
pilot) only report whole seconds and are excluded from the model. Every job ran 1,024 shots.
Counts come from the export; `report.md` states them for the export it was built from.

A provider whose jobs carry no `g.cost_rus` is skipped, listed in the report's coverage
table, and marked `WAITING FOR DATA`. The run does not fail.

## Model

The usage reports follow a billing formula, and the model recovers it. Billed time minus
IBM's circuit-execution time takes one value per runtime configuration: 1.702 s for
untwirled jobs and 1.732 s for twirled jobs. Circuit time is shots × (a chip constant +
scheduled duration). Agreement with held-out jobs measures how well that formula is
recovered. It is not evidence of a learned predictor.

Inputs are known before running: the chip, shots, scheduled duration of one shot
(`c.duration_s`), twirling, dynamical decoupling, the dynamic-circuit flag, and compiled
depth/size/two-qubit gates.

**Chip constant.** The per-shot constant differs between chips: 256.6 µs on Fez, 259.0 µs
on Kingston and 266.2 µs on Marrakesh, fitted on all jobs. Ten microseconds per shot is
10 ms per 1,024-shot job, enough to move a job across a whole-second billing boundary. The
physical model fits one constant per chip. A chip with no training jobs is predicted with
the job-weighted average of the training chips (258.3 µs) and flagged as unseen: its
offset is unknown, of the order of 10 µs per shot, until it has usage reports. The tree
models do not receive the chip.

**Overhead and per-shot time.** Because every job ran the same number of shots, overhead
and per-shot time are collinear in billed time. They are separated using IBM's measured
circuit execution time, a training label only (never an input). Fitted on all jobs:
1.702 s per job + shots × (chip constant + 0.995 × scheduled duration). Twirled jobs
(all Shor) add their own terms.

**Residual.** A gradient-boosted model corrects the physical prediction from circuit
features. It has no shot input, so it is applied only at the shot counts it was fitted on.
At any other shot count the prediction is the physical terms alone.

## Evaluation

* **Unseen-circuit validation:** repeated grouped K-fold by circuit configuration on the
  training campaigns.
* **New-run validation:** the 252 `validation-v1` jobs on Fez, Kingston and Marrakesh.
  Cost was not pre-registered for these runs, so this is an out-of-sample test, not a
  pre-registration. About half of the validation configurations also occur in training,
  so this tests new runs more than new circuits. Marrakesh has no training jobs: its rows
  use the fallback constant and measure the unknown-chip offset.
* **Baselines:** the physical model alone, gradient boosting alone, IBM's published
  rule of thumb (~2 s + 350 µs per execution), and always predicting the most common
  whole-second bill in the training jobs.

Mean absolute error in milliseconds is the headline. Whole-second accuracy is reported
beside the majority baseline, and again on jobs within 20 ms of a whole second, where the
bill can flip. R² is reported last. Billed time varies by about 13 ms within a chip, so R²
moves on errors that do not change the bill.

| New-run scope | Jobs | MAE (ms) | Whole-second accuracy | Majority baseline | Near boundary: jobs | Accuracy | Majority |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| All | 252 | 3.0 | 98.4% | 92.1% | 78 | 94.9% | 84.6% |
| Fez | 84 | 0.4 | 100.0% | 95.2% | 12 | 100.0% | 83.3% |
| Kingston | 84 | 0.4 | 100.0% | 92.9% | 20 | 100.0% | 80.0% |
| Marrakesh (unseen chip, fallback constant) | 84 | 8.4 | 95.2% | 88.1% | 46 | 91.3% | 87.0% |

Unseen-circuit validation on the 2,025 training jobs: MAE 0.7 ms, whole-second accuracy
100.0% against a majority baseline of 87.7%. The four whole-second misses are all
Marrakesh jobs billed just above 2 s. The physical model alone matches the hybrid on
every chip (Fez 0.1 ms against 0.4 ms), so the residual adds nothing on these jobs.

These figures come from the current export; the model and its report are in
`report/ml_estimation/cost/`.

## Limits

* Scaling to other shot counts uses the physical terms. It follows IBM's published
  structure and assumes the per-job overhead does not depend on shots. It is not
  validated: the data contains only 1,024-shot jobs.
* A chip without usage reports has an unknown per-shot offset. Three chips of one
  processor family are covered. Other providers: WAITING FOR DATA.
* RU-to-money depends on the IBM plan; the dashboard takes a price per RU as input and
  does not assume one.
* Twirling only occurs with Shor, so its effect is confounded with that algorithm. The
  twirled duration term rests on 13 configurations.

## Refresh

After a new export:

```sh
python -m experiments.qaqs_cost          # report, frozen model and dashboard snapshot
python scripts/run.py dashboard
```

If the export only added columns or rows, `python scripts/restamp_snapshots.py --previous
<old export dir>` verifies that and re-stamps every snapshot (including cost) instead.
