# Prospective validation · `fez-validation-v1-2026-11-16`

Predictions pre-registered at 2026-11-16T20:56:32.536106+00:00 (commit `f2d774ebda3ace5fb4c259275a180e06e1d7c0c6`), 42 configurations on `ibm_fez`. Prepared records and frozen models were re-hashed before scoring and match.

Pre-registered criteria: H1 uses the `new` group with circuit-only models (pass needs the 95% CI above 0.80). `anchor` = known circuits, new calibration cycle (drift). `extrapolation` = larger than any measured circuit (H2).

QPU: **seen** (training chips: ibm_fez, ibm_kingston).

| Model scope | Transfer | Target | Regime | Group | Configs / jobs | R² [95% CI] | MAE | Unseen-circuit MAE | Verdict |
|---|---|---|---|---|---:|---:|---:|---:|:---:|
| `ibm_fez` | same_chip | dsr | circuit_only | all | 42 / 84 | 0.786 [0.59, 0.88] | 0.0937 | 0.1145 |  |
| `ibm_fez` | same_chip | dsr | circuit_only | anchor | 20 / 40 | 0.813 [0.24, 0.94] | 0.0874 | 0.1145 |  |
| `ibm_fez` | same_chip | dsr | circuit_only | extrapolation | 9 / 18 | 0.581 [-0.88, 0.85] | 0.1718 | 0.1145 |  |
| `ibm_fez` | same_chip | dsr | circuit_only | new | 13 / 26 | 0.050 [-1.93, 0.82] | 0.0492 | 0.1145 | INCONCLUSIVE |
| `ibm_fez` | same_chip | hellinger | circuit_only | all | 42 / 84 | 0.930 [0.88, 0.96] | 0.0610 | 0.0712 |  |
| `ibm_fez` | same_chip | hellinger | circuit_only | anchor | 20 / 40 | 0.910 [0.72, 0.98] | 0.0555 | 0.0712 |  |
| `ibm_fez` | same_chip | hellinger | circuit_only | extrapolation | 9 / 18 | 0.835 [0.04, 0.92] | 0.0825 | 0.0712 |  |
| `ibm_fez` | same_chip | hellinger | circuit_only | new | 13 / 26 | 0.902 [0.82, 0.94] | 0.0545 | 0.0712 | PASS |
| `ibm_fez` | same_chip | success | circuit_only | all | 42 / 84 | 0.939 [0.89, 0.97] | 0.0531 | 0.0734 |  |
| `ibm_fez` | same_chip | success | circuit_only | anchor | 20 / 40 | 0.936 [0.83, 0.98] | 0.0502 | 0.0734 |  |
| `ibm_fez` | same_chip | success | circuit_only | extrapolation | 9 / 18 | 0.805 [0.17, 0.93] | 0.0806 | 0.0734 |  |
| `ibm_fez` | same_chip | success | circuit_only | new | 13 / 26 | 0.940 [0.82, 0.99] | 0.0386 | 0.0734 | PASS |
| `ibm_fez` | same_chip | tvd | circuit_only | all | 42 / 84 | 0.937 [0.89, 0.97] | 0.0538 | 0.0684 |  |
| `ibm_fez` | same_chip | tvd | circuit_only | anchor | 20 / 40 | 0.927 [0.81, 0.98] | 0.0492 | 0.0684 |  |
| `ibm_fez` | same_chip | tvd | circuit_only | extrapolation | 9 / 18 | 0.810 [-0.03, 0.95] | 0.0770 | 0.0684 |  |
| `ibm_fez` | same_chip | tvd | circuit_only | new | 13 / 26 | 0.924 [0.78, 0.98] | 0.0447 | 0.0684 | INCONCLUSIVE |
| `ibm_fez` | same_chip | dsr | mixed_submit | all | 42 / 84 | 0.801 [0.61, 0.90] | 0.0869 | 0.0859 |  |
| `ibm_fez` | same_chip | dsr | mixed_submit | anchor | 20 / 40 | 0.724 [-0.14, 0.89] | 0.1076 | 0.0859 |  |
| `ibm_fez` | same_chip | dsr | mixed_submit | extrapolation | 9 / 18 | 0.784 [-0.10, 0.95] | 0.1059 | 0.0859 |  |
| `ibm_fez` | same_chip | dsr | mixed_submit | new | 13 / 26 | 0.375 [-1.05, 0.89] | 0.0418 | 0.0859 |  |
| `ibm_fez` | same_chip | hellinger | mixed_submit | all | 42 / 84 | 0.924 [0.86, 0.97] | 0.0596 | 0.0556 |  |
| `ibm_fez` | same_chip | hellinger | mixed_submit | anchor | 20 / 40 | 0.861 [0.59, 0.95] | 0.0698 | 0.0556 |  |
| `ibm_fez` | same_chip | hellinger | mixed_submit | extrapolation | 9 / 18 | 0.893 [0.55, 0.93] | 0.0655 | 0.0556 |  |
| `ibm_fez` | same_chip | hellinger | mixed_submit | new | 13 / 26 | 0.951 [0.88, 0.98] | 0.0397 | 0.0556 |  |
| `ibm_fez` | same_chip | success | mixed_submit | all | 42 / 84 | 0.828 [0.66, 0.94] | 0.0764 | 0.0584 |  |
| `ibm_fez` | same_chip | success | mixed_submit | anchor | 20 / 40 | 0.773 [0.35, 0.94] | 0.0793 | 0.0584 |  |
| `ibm_fez` | same_chip | success | mixed_submit | extrapolation | 9 / 18 | 0.452 [-1.91, 0.92] | 0.1244 | 0.0584 |  |
| `ibm_fez` | same_chip | success | mixed_submit | new | 13 / 26 | 0.949 [0.88, 0.97] | 0.0386 | 0.0584 |  |
| `ibm_fez` | same_chip | tvd | mixed_submit | all | 42 / 84 | 0.912 [0.84, 0.96] | 0.0610 | 0.0549 |  |
| `ibm_fez` | same_chip | tvd | mixed_submit | anchor | 20 / 40 | 0.829 [0.51, 0.95] | 0.0754 | 0.0549 |  |
| `ibm_fez` | same_chip | tvd | mixed_submit | extrapolation | 9 / 18 | 0.884 [0.43, 0.95] | 0.0648 | 0.0549 |  |
| `ibm_fez` | same_chip | tvd | mixed_submit | new | 13 / 26 | 0.961 [0.90, 0.98] | 0.0361 | 0.0549 |  |
| `pooled` | pooled | dsr | circuit_only | all | 42 / 84 | 0.835 [0.65, 0.94] | 0.0750 | 0.1052 |  |
| `pooled` | pooled | dsr | circuit_only | anchor | 20 / 40 | 0.917 [0.61, 0.98] | 0.0601 | 0.1052 |  |
| `pooled` | pooled | dsr | circuit_only | extrapolation | 9 / 18 | 0.515 [-1.28, 0.92] | 0.1580 | 0.1052 |  |
| `pooled` | pooled | dsr | circuit_only | new | 13 / 26 | 0.658 [0.22, 0.79] | 0.0404 | 0.1052 | FAIL |
| `pooled` | pooled | hellinger | circuit_only | all | 42 / 84 | 0.966 [0.95, 0.98] | 0.0450 | 0.0697 |  |
| `pooled` | pooled | hellinger | circuit_only | anchor | 20 / 40 | 0.976 [0.95, 0.99] | 0.0335 | 0.0697 |  |
| `pooled` | pooled | hellinger | circuit_only | extrapolation | 9 / 18 | 0.834 [0.16, 0.90] | 0.0793 | 0.0697 |  |
| `pooled` | pooled | hellinger | circuit_only | new | 13 / 26 | 0.954 [0.87, 0.97] | 0.0389 | 0.0697 | PASS |
| `pooled` | pooled | success | circuit_only | all | 42 / 84 | 0.935 [0.89, 0.96] | 0.0533 | 0.0709 |  |
| `pooled` | pooled | success | circuit_only | anchor | 20 / 40 | 0.974 [0.95, 0.99] | 0.0359 | 0.0709 |  |
| `pooled` | pooled | success | circuit_only | extrapolation | 9 / 18 | 0.577 [-0.63, 0.75] | 0.1188 | 0.0709 |  |
| `pooled` | pooled | success | circuit_only | new | 13 / 26 | 0.959 [0.90, 0.98] | 0.0349 | 0.0709 | PASS |
| `pooled` | pooled | tvd | circuit_only | all | 42 / 84 | 0.954 [0.93, 0.98] | 0.0480 | 0.0675 |  |
| `pooled` | pooled | tvd | circuit_only | anchor | 20 / 40 | 0.961 [0.86, 0.99] | 0.0360 | 0.0675 |  |
| `pooled` | pooled | tvd | circuit_only | extrapolation | 9 / 18 | 0.765 [-0.17, 0.88] | 0.0996 | 0.0675 |  |
| `pooled` | pooled | tvd | circuit_only | new | 13 / 26 | 0.974 [0.93, 0.98] | 0.0308 | 0.0675 | PASS |
| `pooled` | pooled | dsr | mixed_submit | all | 42 / 84 | 0.818 [0.64, 0.91] | 0.0857 | 0.0811 |  |
| `pooled` | pooled | dsr | mixed_submit | anchor | 20 / 40 | 0.795 [0.09, 0.93] | 0.0909 | 0.0811 |  |
| `pooled` | pooled | dsr | mixed_submit | extrapolation | 9 / 18 | 0.680 [-0.49, 0.92] | 0.1445 | 0.0811 |  |
| `pooled` | pooled | dsr | mixed_submit | new | 13 / 26 | 0.725 [0.38, 0.81] | 0.0370 | 0.0811 |  |
| `pooled` | pooled | hellinger | mixed_submit | all | 42 / 84 | 0.952 [0.92, 0.97] | 0.0496 | 0.0527 |  |
| `pooled` | pooled | hellinger | mixed_submit | anchor | 20 / 40 | 0.942 [0.81, 0.98] | 0.0483 | 0.0527 |  |
| `pooled` | pooled | hellinger | mixed_submit | extrapolation | 9 / 18 | 0.851 [0.23, 0.93] | 0.0671 | 0.0527 |  |
| `pooled` | pooled | hellinger | mixed_submit | new | 13 / 26 | 0.943 [0.85, 0.98] | 0.0393 | 0.0527 |  |
| `pooled` | pooled | success | mixed_submit | all | 42 / 84 | 0.933 [0.88, 0.96] | 0.0571 | 0.0591 |  |
| `pooled` | pooled | success | mixed_submit | anchor | 20 / 40 | 0.959 [0.90, 0.98] | 0.0422 | 0.0591 |  |
| `pooled` | pooled | success | mixed_submit | extrapolation | 9 / 18 | 0.644 [-0.67, 0.87] | 0.1131 | 0.0591 |  |
| `pooled` | pooled | success | mixed_submit | new | 13 / 26 | 0.944 [0.80, 0.98] | 0.0412 | 0.0591 |  |
| `pooled` | pooled | tvd | mixed_submit | all | 42 / 84 | 0.912 [0.82, 0.97] | 0.0593 | 0.0508 |  |
| `pooled` | pooled | tvd | mixed_submit | anchor | 20 / 40 | 0.844 [0.42, 0.97] | 0.0667 | 0.0508 |  |
| `pooled` | pooled | tvd | mixed_submit | extrapolation | 9 / 18 | 0.821 [0.44, 0.92] | 0.0783 | 0.0508 |  |
| `pooled` | pooled | tvd | mixed_submit | new | 13 / 26 | 0.968 [0.92, 0.98] | 0.0347 | 0.0508 |  |
