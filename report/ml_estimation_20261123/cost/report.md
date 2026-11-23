# QAQS execution-cost model

Target: billed QPU seconds = resource units × 60 (1 RU = 1 minute of QPU time). 2277 jobs with an RU report on ibm_fez, ibm_kingston, ibm_marrakesh; 404 older jobs report whole seconds only and are excluded. Every job ran 1024 shots.

Observed: median 1.972 s (0.03286 RU) per job; the circuit itself runs 0.270 s, so 86% of the bill is per-job overhead. 11.8% of jobs are billed 3 whole seconds instead of 2.

## Physical terms (fitted on all jobs)

billed ≈ 1.702 s per job + shots × (258.1 µs + 1.023 × scheduled duration). Twirled jobs add 0.030 s per job and -11.8 µs + 5.23 × duration per shot.

For comparison, IBM's published rule is ~2 s per job + 350 µs per execution (250 µs default rep_delay + a typical circuit).

## Unseen-circuit validation (training campaigns, grouped K-fold)

| Model | R² | MAE (ms) | MAPE % | Billed-second accuracy |
|---|---:|---:|---:|---:|
| QAQS cost (physical + residual) | 1.000 | 1.1 | 0.05 | 1.000 |
| Physical model only | 1.000 | 1.6 | 0.07 | 1.000 |
| Gradient boosting only | 0.999 | 1.6 | 0.08 | 0.996 |
| IBM rule of thumb | -6.535 | 379.0 | 18.98 | 0.123 |

## New-run validation (validation-v1 jobs; cost not pre-registered)

| Model | Scope | R² | MAE (ms) | MAPE % | Billed-second accuracy |
|---|---|---:|---:|---:|---:|
| QAQS cost (physical + residual) | all | 0.899 | 3.1 | 0.16 | 0.984 |
| QAQS cost (physical + residual) | ibm_fez | 0.988 | 1.1 | 0.05 | 1.000 |
| QAQS cost (physical + residual) | ibm_kingston | 0.997 | 0.6 | 0.03 | 1.000 |
| QAQS cost (physical + residual) | ibm_marrakesh | 0.708 | 7.8 | 0.39 | 0.952 |
| Physical model only | all | 0.883 | 3.6 | 0.18 | 0.984 |
| Physical model only | ibm_fez | 0.986 | 1.4 | 0.07 | 1.000 |
| Physical model only | ibm_kingston | 0.994 | 0.9 | 0.04 | 1.000 |
| Physical model only | ibm_marrakesh | 0.664 | 8.3 | 0.42 | 0.952 |
| Gradient boosting only | all | 0.875 | 3.5 | 0.17 | 0.960 |
| Gradient boosting only | ibm_fez | 0.936 | 1.6 | 0.08 | 0.952 |
| Gradient boosting only | ibm_kingston | 0.975 | 0.9 | 0.04 | 0.976 |
| Gradient boosting only | ibm_marrakesh | 0.693 | 7.9 | 0.40 | 0.952 |
| IBM rule of thumb | all | -674.181 | 377.9 | 19.09 | 0.079 |
| IBM rule of thumb | ibm_fez | -939.978 | 383.3 | 19.41 | 0.048 |
| IBM rule of thumb | ibm_kingston | -769.844 | 379.6 | 19.19 | 0.071 |
| IBM rule of thumb | ibm_marrakesh | -650.338 | 370.9 | 18.67 | 0.119 |

Predictions at other shot counts use the fitted per-shot terms; the data only contains 1,024-shot jobs, so that scaling is an assumption (IBM's published structure), not validated.
