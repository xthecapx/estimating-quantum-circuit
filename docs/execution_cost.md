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

2,257 of 2,661 jobs have the RU report. The 404 oldest Fez jobs (`fez-dataset-v2` and its
pilot) only report whole seconds and are excluded from the model. Every job ran 1,024 shots.

## Model

One model for all chips, with no chip input. Inputs are known before running: shots,
scheduled duration of one shot (`c.duration_s`), twirling, dynamical decoupling, the
dynamic-circuit flag, and compiled depth/size/two-qubit gates.

The structure follows IBM's usage formula, *per-job overhead + shots × per-shot time*,
plus a gradient-boosted residual on circuit features. Because every job ran the same
number of shots, overhead and per-shot time are collinear in billed time; they are
separated using IBM's measured circuit execution time, a training label only (never an
input). Fitted on all jobs: about 1.70 s per job + shots × (258 µs + 1.02 × scheduled
duration). Twirled jobs (all Shor) add their own terms.

## Evaluation

* **Unseen-circuit validation:** repeated grouped K-fold by circuit configuration on the
  training campaigns.
* **New-run validation:** the 252 `validation-v1` jobs on Fez, Kingston and the unseen
  Marrakesh. Cost was not pre-registered for these runs, so this is an out-of-sample test,
  not a pre-registration.
* **Baselines:** the physical model alone, gradient boosting alone, and IBM's published
  rule of thumb (~2 s + 350 µs per execution).

Results and the frozen model are in `report/ml_estimation/cost/`.

## Limits

* Scaling to other shot counts uses the fitted per-shot terms. It follows IBM's published
  structure but is not validated: the data contains only 1,024-shot jobs.
* RU-to-money depends on the IBM plan; the dashboard takes a price per RU as input and
  does not assume one.
* Twirling only occurs with Shor, so its effect is confounded with that algorithm.

## Refresh

After a new export:

```sh
python -m experiments.qaqs_cost          # report, frozen model and dashboard snapshot
python scripts/run.py dashboard
```

If the export only added columns or rows, `python scripts/restamp_snapshots.py --previous
<old export dir>` verifies that and re-stamps every snapshot (including cost) instead.
