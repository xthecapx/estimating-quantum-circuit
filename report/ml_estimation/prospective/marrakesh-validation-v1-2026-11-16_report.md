# Prospective validation · `marrakesh-validation-v1-2026-11-16`

Predictions pre-registered at 2026-11-16T20:56:39.138547+00:00 (commit `f2d774ebda3ace5fb4c259275a180e06e1d7c0c6`), 42 configurations on `ibm_marrakesh`. Prepared records and frozen models were re-hashed before scoring and match.

Pre-registered criteria: H1 uses the `new` group with circuit-only models (pass needs the 95% CI above 0.80). `anchor` = known circuits, new calibration cycle (drift). `extrapolation` = larger than any measured circuit (H2).

QPU: **unseen** (training chips: ibm_fez, ibm_kingston).

| Model scope | Transfer | Target | Regime | Group | Configs / jobs | R² [95% CI] | MAE | Unseen-circuit MAE | Verdict |
|---|---|---|---|---|---:|---:|---:|---:|:---:|
| `ibm_fez` | cross_chip_zero_shot | dsr | circuit_only | all | 42 / 84 | 0.867 [0.77, 0.93] | 0.0816 | 0.1145 |  |
| `ibm_fez` | cross_chip_zero_shot | dsr | circuit_only | anchor | 20 / 40 | 0.871 [0.67, 0.96] | 0.0804 | 0.1145 |  |
| `ibm_fez` | cross_chip_zero_shot | dsr | circuit_only | extrapolation | 9 / 18 | 0.673 [-2.66, 0.91] | 0.1506 | 0.1145 |  |
| `ibm_fez` | cross_chip_zero_shot | dsr | circuit_only | new | 13 / 26 | 0.811 [0.48, 0.95] | 0.0357 | 0.1145 | INCONCLUSIVE |
| `ibm_fez` | cross_chip_zero_shot | hellinger | circuit_only | all | 42 / 84 | 0.925 [0.88, 0.95] | 0.0720 | 0.0712 |  |
| `ibm_fez` | cross_chip_zero_shot | hellinger | circuit_only | anchor | 20 / 40 | 0.937 [0.84, 0.98] | 0.0556 | 0.0712 |  |
| `ibm_fez` | cross_chip_zero_shot | hellinger | circuit_only | extrapolation | 9 / 18 | 0.683 [-2.61, 0.83] | 0.1008 | 0.0712 |  |
| `ibm_fez` | cross_chip_zero_shot | hellinger | circuit_only | new | 13 / 26 | 0.866 [0.80, 0.92] | 0.0774 | 0.0712 | INCONCLUSIVE |
| `ibm_fez` | cross_chip_zero_shot | success | circuit_only | all | 42 / 84 | 0.937 [0.89, 0.97] | 0.0615 | 0.0734 |  |
| `ibm_fez` | cross_chip_zero_shot | success | circuit_only | anchor | 20 / 40 | 0.939 [0.86, 0.98] | 0.0537 | 0.0734 |  |
| `ibm_fez` | cross_chip_zero_shot | success | circuit_only | extrapolation | 9 / 18 | 0.704 [-1.42, 0.91] | 0.0903 | 0.0734 |  |
| `ibm_fez` | cross_chip_zero_shot | success | circuit_only | new | 13 / 26 | 0.934 [0.88, 0.97] | 0.0536 | 0.0734 | PASS |
| `ibm_fez` | cross_chip_zero_shot | tvd | circuit_only | all | 42 / 84 | 0.962 [0.94, 0.98] | 0.0512 | 0.0684 |  |
| `ibm_fez` | cross_chip_zero_shot | tvd | circuit_only | anchor | 20 / 40 | 0.966 [0.92, 0.99] | 0.0422 | 0.0684 |  |
| `ibm_fez` | cross_chip_zero_shot | tvd | circuit_only | extrapolation | 9 / 18 | 0.850 [-0.44, 0.92] | 0.0664 | 0.0684 |  |
| `ibm_fez` | cross_chip_zero_shot | tvd | circuit_only | new | 13 / 26 | 0.939 [0.90, 0.96] | 0.0546 | 0.0684 | PASS |
| `ibm_fez` | cross_chip_zero_shot | dsr | mixed_submit | all | 42 / 84 | 0.798 [0.64, 0.89] | 0.1028 | 0.0859 |  |
| `ibm_fez` | cross_chip_zero_shot | dsr | mixed_submit | anchor | 20 / 40 | 0.779 [0.44, 0.89] | 0.1074 | 0.0859 |  |
| `ibm_fez` | cross_chip_zero_shot | dsr | mixed_submit | extrapolation | 9 / 18 | 0.556 [-4.13, 0.90] | 0.1770 | 0.0859 |  |
| `ibm_fez` | cross_chip_zero_shot | dsr | mixed_submit | new | 13 / 26 | 0.728 [0.54, 0.81] | 0.0442 | 0.0859 |  |
| `ibm_fez` | cross_chip_zero_shot | hellinger | mixed_submit | all | 42 / 84 | 0.908 [0.83, 0.95] | 0.0741 | 0.0556 |  |
| `ibm_fez` | cross_chip_zero_shot | hellinger | mixed_submit | anchor | 20 / 40 | 0.886 [0.71, 0.97] | 0.0738 | 0.0556 |  |
| `ibm_fez` | cross_chip_zero_shot | hellinger | mixed_submit | extrapolation | 9 / 18 | 0.759 [-2.15, 0.93] | 0.0782 | 0.0556 |  |
| `ibm_fez` | cross_chip_zero_shot | hellinger | mixed_submit | new | 13 / 26 | 0.862 [0.73, 0.93] | 0.0717 | 0.0556 |  |
| `ibm_fez` | cross_chip_zero_shot | success | mixed_submit | all | 42 / 84 | 0.804 [0.61, 0.93] | 0.0926 | 0.0584 |  |
| `ibm_fez` | cross_chip_zero_shot | success | mixed_submit | anchor | 20 / 40 | 0.875 [0.70, 0.97] | 0.0716 | 0.0584 |  |
| `ibm_fez` | cross_chip_zero_shot | success | mixed_submit | extrapolation | 9 / 18 | -0.468 [-14.14, 0.76] | 0.1723 | 0.0584 |  |
| `ibm_fez` | cross_chip_zero_shot | success | mixed_submit | new | 13 / 26 | 0.862 [0.77, 0.91] | 0.0696 | 0.0584 |  |
| `ibm_fez` | cross_chip_zero_shot | tvd | mixed_submit | all | 42 / 84 | 0.907 [0.85, 0.94] | 0.0784 | 0.0549 |  |
| `ibm_fez` | cross_chip_zero_shot | tvd | mixed_submit | anchor | 20 / 40 | 0.877 [0.73, 0.95] | 0.0794 | 0.0549 |  |
| `ibm_fez` | cross_chip_zero_shot | tvd | mixed_submit | extrapolation | 9 / 18 | 0.746 [-1.81, 0.89] | 0.0877 | 0.0549 |  |
| `ibm_fez` | cross_chip_zero_shot | tvd | mixed_submit | new | 13 / 26 | 0.887 [0.80, 0.93] | 0.0703 | 0.0549 |  |
| `ibm_kingston` | cross_chip_zero_shot | dsr | circuit_only | all | 42 / 84 | 0.708 [0.45, 0.84] | 0.1197 | 0.0844 |  |
| `ibm_kingston` | cross_chip_zero_shot | dsr | circuit_only | anchor | 20 / 40 | 0.765 [0.42, 0.90] | 0.1103 | 0.0844 |  |
| `ibm_kingston` | cross_chip_zero_shot | dsr | circuit_only | extrapolation | 9 / 18 | 0.253 [-7.47, 0.82] | 0.2092 | 0.0844 |  |
| `ibm_kingston` | cross_chip_zero_shot | dsr | circuit_only | new | 13 / 26 | 0.213 [-1.09, 0.72] | 0.0722 | 0.0844 | FAIL |
| `ibm_kingston` | cross_chip_zero_shot | hellinger | circuit_only | all | 42 / 84 | 0.806 [0.70, 0.87] | 0.1136 | 0.0506 |  |
| `ibm_kingston` | cross_chip_zero_shot | hellinger | circuit_only | anchor | 20 / 40 | 0.865 [0.74, 0.93] | 0.0837 | 0.0506 |  |
| `ibm_kingston` | cross_chip_zero_shot | hellinger | circuit_only | extrapolation | 9 / 18 | -0.012 [-11.33, 0.61] | 0.1829 | 0.0506 |  |
| `ibm_kingston` | cross_chip_zero_shot | hellinger | circuit_only | new | 13 / 26 | 0.665 [0.38, 0.84] | 0.1115 | 0.0506 | INCONCLUSIVE |
| `ibm_kingston` | cross_chip_zero_shot | success | circuit_only | all | 42 / 84 | 0.781 [0.66, 0.86] | 0.1163 | 0.0512 |  |
| `ibm_kingston` | cross_chip_zero_shot | success | circuit_only | anchor | 20 / 40 | 0.848 [0.71, 0.93] | 0.0888 | 0.0512 |  |
| `ibm_kingston` | cross_chip_zero_shot | success | circuit_only | extrapolation | 9 / 18 | -0.142 [-10.10, 0.57] | 0.1907 | 0.0512 |  |
| `ibm_kingston` | cross_chip_zero_shot | success | circuit_only | new | 13 / 26 | 0.687 [0.41, 0.85] | 0.1070 | 0.0512 | INCONCLUSIVE |
| `ibm_kingston` | cross_chip_zero_shot | tvd | circuit_only | all | 42 / 84 | 0.804 [0.70, 0.87] | 0.1128 | 0.0483 |  |
| `ibm_kingston` | cross_chip_zero_shot | tvd | circuit_only | anchor | 20 / 40 | 0.870 [0.74, 0.93] | 0.0810 | 0.0483 |  |
| `ibm_kingston` | cross_chip_zero_shot | tvd | circuit_only | extrapolation | 9 / 18 | -0.171 [-13.24, 0.49] | 0.2000 | 0.0483 |  |
| `ibm_kingston` | cross_chip_zero_shot | tvd | circuit_only | new | 13 / 26 | 0.731 [0.49, 0.87] | 0.1013 | 0.0483 | INCONCLUSIVE |
| `ibm_kingston` | cross_chip_zero_shot | dsr | mixed_submit | all | 42 / 84 | 0.823 [0.72, 0.90] | 0.1039 | 0.0826 |  |
| `ibm_kingston` | cross_chip_zero_shot | dsr | mixed_submit | anchor | 20 / 40 | 0.813 [0.58, 0.93] | 0.0971 | 0.0826 |  |
| `ibm_kingston` | cross_chip_zero_shot | dsr | mixed_submit | extrapolation | 9 / 18 | 0.687 [-2.26, 0.86] | 0.1608 | 0.0826 |  |
| `ibm_kingston` | cross_chip_zero_shot | dsr | mixed_submit | new | 13 / 26 | 0.274 [-1.33, 0.79] | 0.0749 | 0.0826 |  |
| `ibm_kingston` | cross_chip_zero_shot | hellinger | mixed_submit | all | 42 / 84 | 0.814 [0.74, 0.87] | 0.1092 | 0.0487 |  |
| `ibm_kingston` | cross_chip_zero_shot | hellinger | mixed_submit | anchor | 20 / 40 | 0.879 [0.80, 0.92] | 0.0800 | 0.0487 |  |
| `ibm_kingston` | cross_chip_zero_shot | hellinger | mixed_submit | extrapolation | 9 / 18 | -0.240 [-13.20, 0.47] | 0.1952 | 0.0487 |  |
| `ibm_kingston` | cross_chip_zero_shot | hellinger | mixed_submit | new | 13 / 26 | 0.760 [0.56, 0.92] | 0.0947 | 0.0487 |  |
| `ibm_kingston` | cross_chip_zero_shot | success | mixed_submit | all | 42 / 84 | 0.670 [0.52, 0.80] | 0.1374 | 0.0568 |  |
| `ibm_kingston` | cross_chip_zero_shot | success | mixed_submit | anchor | 20 / 40 | 0.791 [0.62, 0.89] | 0.0938 | 0.0568 |  |
| `ibm_kingston` | cross_chip_zero_shot | success | mixed_submit | extrapolation | 9 / 18 | -0.977 [-13.96, 0.24] | 0.2403 | 0.0568 |  |
| `ibm_kingston` | cross_chip_zero_shot | success | mixed_submit | new | 13 / 26 | 0.583 [0.32, 0.74] | 0.1330 | 0.0568 |  |
| `ibm_kingston` | cross_chip_zero_shot | tvd | mixed_submit | all | 42 / 84 | 0.764 [0.65, 0.84] | 0.1180 | 0.0485 |  |
| `ibm_kingston` | cross_chip_zero_shot | tvd | mixed_submit | anchor | 20 / 40 | 0.870 [0.78, 0.92] | 0.0764 | 0.0485 |  |
| `ibm_kingston` | cross_chip_zero_shot | tvd | mixed_submit | extrapolation | 9 / 18 | -0.652 [-17.71, 0.26] | 0.2394 | 0.0485 |  |
| `ibm_kingston` | cross_chip_zero_shot | tvd | mixed_submit | new | 13 / 26 | 0.708 [0.51, 0.92] | 0.0980 | 0.0485 |  |
| `pooled` | pooled_zero_shot | dsr | circuit_only | all | 42 / 84 | 0.801 [0.61, 0.90] | 0.0927 | 0.1052 |  |
| `pooled` | pooled_zero_shot | dsr | circuit_only | anchor | 20 / 40 | 0.873 [0.65, 0.95] | 0.0821 | 0.1052 |  |
| `pooled` | pooled_zero_shot | dsr | circuit_only | extrapolation | 9 / 18 | 0.396 [-5.01, 0.95] | 0.1776 | 0.1052 |  |
| `pooled` | pooled_zero_shot | dsr | circuit_only | new | 13 / 26 | 0.612 [0.36, 0.81] | 0.0502 | 0.1052 | INCONCLUSIVE |
| `pooled` | pooled_zero_shot | hellinger | circuit_only | all | 42 / 84 | 0.904 [0.85, 0.94] | 0.0768 | 0.0697 |  |
| `pooled` | pooled_zero_shot | hellinger | circuit_only | anchor | 20 / 40 | 0.926 [0.86, 0.95] | 0.0639 | 0.0697 |  |
| `pooled` | pooled_zero_shot | hellinger | circuit_only | extrapolation | 9 / 18 | 0.536 [-3.86, 0.77] | 0.1182 | 0.0697 |  |
| `pooled` | pooled_zero_shot | hellinger | circuit_only | new | 13 / 26 | 0.837 [0.61, 0.96] | 0.0679 | 0.0697 | INCONCLUSIVE |
| `pooled` | pooled_zero_shot | success | circuit_only | all | 42 / 84 | 0.901 [0.86, 0.93] | 0.0777 | 0.0709 |  |
| `pooled` | pooled_zero_shot | success | circuit_only | anchor | 20 / 40 | 0.925 [0.86, 0.96] | 0.0649 | 0.0709 |  |
| `pooled` | pooled_zero_shot | success | circuit_only | extrapolation | 9 / 18 | 0.494 [-3.55, 0.81] | 0.1154 | 0.0709 |  |
| `pooled` | pooled_zero_shot | success | circuit_only | new | 13 / 26 | 0.869 [0.74, 0.94] | 0.0711 | 0.0709 | INCONCLUSIVE |
| `pooled` | pooled_zero_shot | tvd | circuit_only | all | 42 / 84 | 0.926 [0.88, 0.96] | 0.0681 | 0.0675 |  |
| `pooled` | pooled_zero_shot | tvd | circuit_only | anchor | 20 / 40 | 0.921 [0.85, 0.96] | 0.0671 | 0.0675 |  |
| `pooled` | pooled_zero_shot | tvd | circuit_only | extrapolation | 9 / 18 | 0.738 [-1.68, 0.86] | 0.0840 | 0.0675 |  |
| `pooled` | pooled_zero_shot | tvd | circuit_only | new | 13 / 26 | 0.895 [0.76, 0.97] | 0.0585 | 0.0675 | INCONCLUSIVE |
| `pooled` | pooled_zero_shot | dsr | mixed_submit | all | 42 / 84 | 0.806 [0.66, 0.90] | 0.0964 | 0.0811 |  |
| `pooled` | pooled_zero_shot | dsr | mixed_submit | anchor | 20 / 40 | 0.848 [0.59, 0.93] | 0.0913 | 0.0811 |  |
| `pooled` | pooled_zero_shot | dsr | mixed_submit | extrapolation | 9 / 18 | 0.480 [-4.56, 0.93] | 0.1684 | 0.0811 |  |
| `pooled` | pooled_zero_shot | dsr | mixed_submit | new | 13 / 26 | 0.563 [0.19, 0.72] | 0.0543 | 0.0811 |  |
| `pooled` | pooled_zero_shot | hellinger | mixed_submit | all | 42 / 84 | 0.893 [0.83, 0.93] | 0.0827 | 0.0527 |  |
| `pooled` | pooled_zero_shot | hellinger | mixed_submit | anchor | 20 / 40 | 0.922 [0.85, 0.96] | 0.0671 | 0.0527 |  |
| `pooled` | pooled_zero_shot | hellinger | mixed_submit | extrapolation | 9 / 18 | 0.450 [-5.24, 0.76] | 0.1313 | 0.0527 |  |
| `pooled` | pooled_zero_shot | hellinger | mixed_submit | new | 13 / 26 | 0.824 [0.66, 0.94] | 0.0730 | 0.0527 |  |
| `pooled` | pooled_zero_shot | success | mixed_submit | all | 42 / 84 | 0.915 [0.87, 0.95] | 0.0693 | 0.0591 |  |
| `pooled` | pooled_zero_shot | success | mixed_submit | anchor | 20 / 40 | 0.928 [0.86, 0.97] | 0.0604 | 0.0591 |  |
| `pooled` | pooled_zero_shot | success | mixed_submit | extrapolation | 9 / 18 | 0.674 [-2.05, 0.90] | 0.0873 | 0.0591 |  |
| `pooled` | pooled_zero_shot | success | mixed_submit | new | 13 / 26 | 0.862 [0.77, 0.93] | 0.0706 | 0.0591 |  |
| `pooled` | pooled_zero_shot | tvd | mixed_submit | all | 42 / 84 | 0.913 [0.87, 0.94] | 0.0754 | 0.0508 |  |
| `pooled` | pooled_zero_shot | tvd | mixed_submit | anchor | 20 / 40 | 0.933 [0.87, 0.96] | 0.0589 | 0.0508 |  |
| `pooled` | pooled_zero_shot | tvd | mixed_submit | extrapolation | 9 / 18 | 0.579 [-3.31, 0.78] | 0.1218 | 0.0508 |  |
| `pooled` | pooled_zero_shot | tvd | mixed_submit | new | 13 / 26 | 0.861 [0.78, 0.94] | 0.0686 | 0.0508 |  |
