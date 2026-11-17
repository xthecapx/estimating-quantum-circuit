# Prospective validation · `kingston-validation-v1-2026-11-16`

Predictions pre-registered at 2026-11-16T20:56:26.202718+00:00 (commit `f2d774ebda3ace5fb4c259275a180e06e1d7c0c6`), 42 configurations on `ibm_kingston`. Prepared records and frozen models were re-hashed before scoring and match.

Pre-registered criteria: H1 uses the `new` group with circuit-only models (pass needs the 95% CI above 0.80). `anchor` = known circuits, new calibration cycle (drift). `extrapolation` = larger than any measured circuit (H2).

QPU: **seen** (training chips: ibm_fez, ibm_kingston).

| Model scope | Transfer | Target | Regime | Group | Configs / jobs | R² [95% CI] | MAE | Unseen-circuit MAE | Verdict |
|---|---|---|---|---|---:|---:|---:|---:|:---:|
| `ibm_kingston` | same_chip | dsr | circuit_only | all | 42 / 84 | 0.751 [-0.05, 0.88] | 0.0862 | 0.0844 |  |
| `ibm_kingston` | same_chip | dsr | circuit_only | anchor | 20 / 40 | 0.861 [-0.20, 0.96] | 0.0694 | 0.0844 |  |
| `ibm_kingston` | same_chip | dsr | circuit_only | extrapolation | 9 / 18 | 0.450 [-4.44, 0.73] | 0.1955 | 0.0844 |  |
| `ibm_kingston` | same_chip | dsr | circuit_only | new | 13 / 26 | 0.290 [-0.92, 0.65] | 0.0362 | 0.0844 | FAIL |
| `ibm_kingston` | same_chip | hellinger | circuit_only | all | 42 / 84 | 0.958 [0.92, 0.98] | 0.0374 | 0.0506 |  |
| `ibm_kingston` | same_chip | hellinger | circuit_only | anchor | 20 / 40 | 0.946 [0.84, 0.98] | 0.0398 | 0.0506 |  |
| `ibm_kingston` | same_chip | hellinger | circuit_only | extrapolation | 9 / 18 | 0.933 [0.75, 0.97] | 0.0413 | 0.0506 |  |
| `ibm_kingston` | same_chip | hellinger | circuit_only | new | 13 / 26 | 0.916 [0.79, 0.99] | 0.0311 | 0.0506 | INCONCLUSIVE |
| `ibm_kingston` | same_chip | success | circuit_only | all | 42 / 84 | 0.969 [0.95, 0.98] | 0.0342 | 0.0512 |  |
| `ibm_kingston` | same_chip | success | circuit_only | anchor | 20 / 40 | 0.967 [0.92, 0.98] | 0.0355 | 0.0512 |  |
| `ibm_kingston` | same_chip | success | circuit_only | extrapolation | 9 / 18 | 0.964 [0.90, 0.98] | 0.0324 | 0.0512 |  |
| `ibm_kingston` | same_chip | success | circuit_only | new | 13 / 26 | 0.933 [0.84, 0.98] | 0.0334 | 0.0512 | PASS |
| `ibm_kingston` | same_chip | tvd | circuit_only | all | 42 / 84 | 0.956 [0.92, 0.98] | 0.0383 | 0.0483 |  |
| `ibm_kingston` | same_chip | tvd | circuit_only | anchor | 20 / 40 | 0.932 [0.80, 0.97] | 0.0429 | 0.0483 |  |
| `ibm_kingston` | same_chip | tvd | circuit_only | extrapolation | 9 / 18 | 0.932 [0.66, 0.99] | 0.0335 | 0.0483 |  |
| `ibm_kingston` | same_chip | tvd | circuit_only | new | 13 / 26 | 0.943 [0.84, 0.97] | 0.0344 | 0.0483 | PASS |
| `ibm_kingston` | same_chip | dsr | mixed_submit | all | 42 / 84 | 0.563 [-1.16, 0.81] | 0.1197 | 0.0826 |  |
| `ibm_kingston` | same_chip | dsr | mixed_submit | anchor | 20 / 40 | 0.658 [-2.00, 0.94] | 0.1008 | 0.0826 |  |
| `ibm_kingston` | same_chip | dsr | mixed_submit | extrapolation | 9 / 18 | 0.370 [-6.36, 0.78] | 0.2209 | 0.0826 |  |
| `ibm_kingston` | same_chip | dsr | mixed_submit | new | 13 / 26 | -4.082 [-24.44, 0.23] | 0.0788 | 0.0826 |  |
| `ibm_kingston` | same_chip | hellinger | mixed_submit | all | 42 / 84 | 0.913 [0.86, 0.95] | 0.0568 | 0.0487 |  |
| `ibm_kingston` | same_chip | hellinger | mixed_submit | anchor | 20 / 40 | 0.919 [0.74, 0.97] | 0.0516 | 0.0487 |  |
| `ibm_kingston` | same_chip | hellinger | mixed_submit | extrapolation | 9 / 18 | 0.682 [0.23, 0.80] | 0.0910 | 0.0487 |  |
| `ibm_kingston` | same_chip | hellinger | mixed_submit | new | 13 / 26 | 0.891 [0.56, 0.97] | 0.0412 | 0.0487 |  |
| `ibm_kingston` | same_chip | success | mixed_submit | all | 42 / 84 | 0.933 [0.87, 0.96] | 0.0518 | 0.0568 |  |
| `ibm_kingston` | same_chip | success | mixed_submit | anchor | 20 / 40 | 0.936 [0.84, 0.96] | 0.0519 | 0.0568 |  |
| `ibm_kingston` | same_chip | success | mixed_submit | extrapolation | 9 / 18 | 0.922 [0.80, 0.96] | 0.0443 | 0.0568 |  |
| `ibm_kingston` | same_chip | success | mixed_submit | new | 13 / 26 | 0.829 [0.58, 0.94] | 0.0568 | 0.0568 |  |
| `ibm_kingston` | same_chip | tvd | mixed_submit | all | 42 / 84 | 0.943 [0.91, 0.97] | 0.0450 | 0.0485 |  |
| `ibm_kingston` | same_chip | tvd | mixed_submit | anchor | 20 / 40 | 0.931 [0.76, 0.97] | 0.0451 | 0.0485 |  |
| `ibm_kingston` | same_chip | tvd | mixed_submit | extrapolation | 9 / 18 | 0.857 [0.61, 0.93] | 0.0557 | 0.0485 |  |
| `ibm_kingston` | same_chip | tvd | mixed_submit | new | 13 / 26 | 0.927 [0.80, 0.97] | 0.0373 | 0.0485 |  |
| `pooled` | pooled | dsr | circuit_only | all | 42 / 84 | 0.689 [-0.59, 0.90] | 0.0936 | 0.1052 |  |
| `pooled` | pooled | dsr | circuit_only | anchor | 20 / 40 | 0.746 [-1.67, 0.94] | 0.0897 | 0.1052 |  |
| `pooled` | pooled | dsr | circuit_only | extrapolation | 9 / 18 | 0.503 [-4.38, 0.96] | 0.1515 | 0.1052 |  |
| `pooled` | pooled | dsr | circuit_only | new | 13 / 26 | -1.099 [-4.32, 0.41] | 0.0595 | 0.1052 | FAIL |
| `pooled` | pooled | hellinger | circuit_only | all | 42 / 84 | 0.873 [0.75, 0.94] | 0.0636 | 0.0697 |  |
| `pooled` | pooled | hellinger | circuit_only | anchor | 20 / 40 | 0.850 [0.54, 0.95] | 0.0564 | 0.0697 |  |
| `pooled` | pooled | hellinger | circuit_only | extrapolation | 9 / 18 | 0.627 [-0.47, 0.90] | 0.0911 | 0.0697 |  |
| `pooled` | pooled | hellinger | circuit_only | new | 13 / 26 | 0.850 [0.60, 0.95] | 0.0558 | 0.0697 | INCONCLUSIVE |
| `pooled` | pooled | success | circuit_only | all | 42 / 84 | 0.852 [0.70, 0.92] | 0.0703 | 0.0709 |  |
| `pooled` | pooled | success | circuit_only | anchor | 20 / 40 | 0.917 [0.76, 0.98] | 0.0467 | 0.0709 |  |
| `pooled` | pooled | success | circuit_only | extrapolation | 9 / 18 | 0.302 [-2.13, 0.71] | 0.1389 | 0.0709 |  |
| `pooled` | pooled | success | circuit_only | new | 13 / 26 | 0.859 [0.56, 0.94] | 0.0591 | 0.0709 | INCONCLUSIVE |
| `pooled` | pooled | tvd | circuit_only | all | 42 / 84 | 0.836 [0.70, 0.91] | 0.0736 | 0.0675 |  |
| `pooled` | pooled | tvd | circuit_only | anchor | 20 / 40 | 0.852 [0.55, 0.95] | 0.0584 | 0.0675 |  |
| `pooled` | pooled | tvd | circuit_only | extrapolation | 9 / 18 | 0.338 [-1.67, 0.83] | 0.1255 | 0.0675 |  |
| `pooled` | pooled | tvd | circuit_only | new | 13 / 26 | 0.849 [0.62, 0.92] | 0.0610 | 0.0675 | INCONCLUSIVE |
| `pooled` | pooled | dsr | mixed_submit | all | 42 / 84 | 0.743 [-0.16, 0.89] | 0.0929 | 0.0811 |  |
| `pooled` | pooled | dsr | mixed_submit | anchor | 20 / 40 | 0.803 [-0.78, 0.95] | 0.0826 | 0.0811 |  |
| `pooled` | pooled | dsr | mixed_submit | extrapolation | 9 / 18 | 0.606 [-3.15, 0.89] | 0.1615 | 0.0811 |  |
| `pooled` | pooled | dsr | mixed_submit | new | 13 / 26 | -1.585 [-6.00, 0.26] | 0.0614 | 0.0811 |  |
| `pooled` | pooled | hellinger | mixed_submit | all | 42 / 84 | 0.922 [0.86, 0.96] | 0.0528 | 0.0527 |  |
| `pooled` | pooled | hellinger | mixed_submit | anchor | 20 / 40 | 0.929 [0.79, 0.98] | 0.0401 | 0.0527 |  |
| `pooled` | pooled | hellinger | mixed_submit | extrapolation | 9 / 18 | 0.748 [0.15, 0.89] | 0.0831 | 0.0527 |  |
| `pooled` | pooled | hellinger | mixed_submit | new | 13 / 26 | 0.874 [0.65, 0.96] | 0.0514 | 0.0527 |  |
| `pooled` | pooled | success | mixed_submit | all | 42 / 84 | 0.824 [0.66, 0.92] | 0.0726 | 0.0591 |  |
| `pooled` | pooled | success | mixed_submit | anchor | 20 / 40 | 0.940 [0.83, 0.98] | 0.0424 | 0.0591 |  |
| `pooled` | pooled | success | mixed_submit | extrapolation | 9 / 18 | 0.010 [-3.31, 0.62] | 0.1651 | 0.0591 |  |
| `pooled` | pooled | success | mixed_submit | new | 13 / 26 | 0.842 [0.46, 0.94] | 0.0551 | 0.0591 |  |
| `pooled` | pooled | tvd | mixed_submit | all | 42 / 84 | 0.918 [0.86, 0.95] | 0.0538 | 0.0508 |  |
| `pooled` | pooled | tvd | mixed_submit | anchor | 20 / 40 | 0.920 [0.78, 0.96] | 0.0432 | 0.0508 |  |
| `pooled` | pooled | tvd | mixed_submit | extrapolation | 9 / 18 | 0.744 [0.10, 0.90] | 0.0838 | 0.0508 |  |
| `pooled` | pooled | tvd | mixed_submit | new | 13 / 26 | 0.878 [0.59, 0.95] | 0.0494 | 0.0508 |  |
