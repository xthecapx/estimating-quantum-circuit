# QAQS execution-cost model

**New-run MAE 3.0 ms** on 252 jobs. Whole-second bill correct for 98.4%; always predicting 2 s is correct for 92.1%. Among the 78 jobs within 20 ms of a whole second: 94.9% against 84.6% for that baseline.

Target: billed QPU seconds = resource units × 60 (1 RU = 1 minute of QPU time). 2277 jobs with an RU report on ibm_fez, ibm_kingston, ibm_marrakesh; 404 jobs have no RU report and are excluded. Every job ran 1024 shots.

Observed: median 1.972 s (0.03286 RU) per job; the circuit itself runs 0.270 s, so 86% of the bill is per-job overhead. 11.8% of jobs are billed 3 whole seconds instead of 2.

## Physical terms (fitted on all jobs)

The usage reports follow a billing formula, which these terms recover. Billed time minus IBM's circuit-execution time is one constant per runtime configuration, and circuit time is shots × (a chip constant + scheduled duration). Accuracy here is agreement with that formula.

billed ≈ 1.702 s per job + shots × (chip constant + 0.995 × scheduled duration). Twirled jobs add 0.030 s per job and -11.8 µs + 5.26 × duration per shot.

| Chip | Per-shot constant (µs) |
|---|---:|
| ibm_fez | 256.59 |
| ibm_kingston | 259.03 |
| ibm_marrakesh | 266.20 |
| any other chip (fallback: job-weighted average) | 258.29 |

The chip constants span 9.6 µs per shot. A chip without usage reports is predicted with the fallback and carries an unknown offset of that order per shot until it has data.

For comparison, IBM's published rule is ~2 s per job + 350 µs per execution (250 µs default rep_delay + a typical circuit).

## Unseen-circuit validation (training campaigns, grouped K-fold)

Whole-second accuracy is shown beside two references: the accuracy of always predicting the most common training bill, and both figures on jobs within 20 ms of a whole second, where the bill can flip. R² is last: billed time varies by milliseconds within a chip, so R² moves on errors that do not change the bill.

| Model | MAE (ms) | MAPE % | Whole-second accuracy | Majority baseline | Near boundary: jobs | Near boundary: accuracy | Near boundary: majority | R² |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| QAQS cost (physical + residual) | 0.7 | 0.03 | 100.0% | 87.7% | 148 | 100.0% | 64.9% | 1.000 |
| Physical model only | 0.8 | 0.04 | 100.0% | 87.7% | 148 | 100.0% | 64.9% | 1.000 |
| Gradient boosting only | 1.6 | 0.08 | 99.6% | 87.7% | 148 | 94.1% | 64.9% | 0.999 |
| IBM rule of thumb | 379.0 | 18.98 | 12.3% | 87.7% | 148 | 35.1% | 64.9% | -6.535 |

## New-run validation (validation jobs; cost not pre-registered)

Chips with no training jobs, predicted with the fallback constant: ibm_marrakesh. Their rows measure the unknown-chip offset, not the model with a known chip constant.

| Model · scope | MAE (ms) | MAPE % | Whole-second accuracy | Majority baseline | Near boundary: jobs | Near boundary: accuracy | Near boundary: majority | R² |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| QAQS cost (physical + residual) · all | 3.0 | 0.15 | 98.4% | 92.1% | 78 | 94.9% | 84.6% | 0.886 |
| QAQS cost (physical + residual) · ibm_fez | 0.4 | 0.02 | 100.0% | 95.2% | 12 | 100.0% | 83.3% | 0.997 |
| QAQS cost (physical + residual) · ibm_kingston | 0.4 | 0.02 | 100.0% | 92.9% | 20 | 100.0% | 80.0% | 0.997 |
| QAQS cost (physical + residual) · ibm_marrakesh (chip unseen in training) | 8.4 | 0.42 | 95.2% | 88.1% | 46 | 91.3% | 87.0% | 0.661 |
| Physical model only · all | 3.0 | 0.15 | 98.4% | 92.1% | 78 | 94.9% | 84.6% | 0.886 |
| Physical model only · ibm_fez | 0.1 | 0.01 | 100.0% | 95.2% | 12 | 100.0% | 83.3% | 0.999 |
| Physical model only · ibm_kingston | 0.4 | 0.02 | 100.0% | 92.9% | 20 | 100.0% | 80.0% | 0.996 |
| Physical model only · ibm_marrakesh (chip unseen in training) | 8.4 | 0.42 | 95.2% | 88.1% | 46 | 91.3% | 87.0% | 0.660 |
| Gradient boosting only · all | 3.5 | 0.17 | 96.0% | 92.1% | 78 | 87.2% | 84.6% | 0.875 |
| Gradient boosting only · ibm_fez | 1.6 | 0.08 | 95.2% | 95.2% | 12 | 66.7% | 83.3% | 0.936 |
| Gradient boosting only · ibm_kingston | 0.9 | 0.04 | 97.6% | 92.9% | 20 | 90.0% | 80.0% | 0.975 |
| Gradient boosting only · ibm_marrakesh (chip unseen in training) | 7.9 | 0.40 | 95.2% | 88.1% | 46 | 91.3% | 87.0% | 0.693 |
| IBM rule of thumb · all | 377.9 | 19.09 | 7.9% | 92.1% | 78 | 15.4% | 84.6% | -674.181 |
| IBM rule of thumb · ibm_fez | 383.3 | 19.41 | 4.8% | 95.2% | 12 | 16.7% | 83.3% | -939.978 |
| IBM rule of thumb · ibm_kingston | 379.6 | 19.19 | 7.1% | 92.9% | 20 | 20.0% | 80.0% | -769.844 |
| IBM rule of thumb · ibm_marrakesh (chip unseen in training) | 370.9 | 18.67 | 11.9% | 88.1% | 46 | 13.0% | 87.0% | -650.338 |

## Usage-report coverage

| Provider | Chips | Jobs | With RU report | Status |
|---|---|---:|---:|---|
| ibm | ibm_fez, ibm_kingston, ibm_marrakesh | 2681 | 2277 | modelled |

Predictions at other shot counts use the physical terms only; the residual model has no shot input and is applied only at the shot counts it was fitted on. The data contains 1024-shot jobs only, so shot scaling is an assumption (IBM's published structure, with a per-job overhead that does not depend on shots), not validated.
