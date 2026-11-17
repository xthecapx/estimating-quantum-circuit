# Prospective validation · seen vs unseen QPU

Seen QPU = a chip with training data; unseen QPU = no training data (zero-shot). Rows are never pooled across `qpu`. Groups: `anchor` known circuits, `new` unseen circuits in range, `extrapolation` larger circuits.

## success

| QPU | Chip | Model scope | Transfer | Regime | anchor R² | new R² [95% CI] | extrapolation R² | new verdict |
|---|---|---|---|---|---:|---:|---:|:---:|
| seen | `ibm_fez` | `ibm_fez` | same_chip | circuit_only | 0.936 | 0.940 [0.82, 0.99] | 0.805 | PASS |
| seen | `ibm_fez` | `ibm_fez` | same_chip | mixed_submit | 0.773 | 0.949 [0.88, 0.97] | 0.452 |  |
| seen | `ibm_fez` | `pooled` | pooled | circuit_only | 0.974 | 0.959 [0.90, 0.98] | 0.577 | PASS |
| seen | `ibm_fez` | `pooled` | pooled | mixed_submit | 0.959 | 0.944 [0.80, 0.98] | 0.644 |  |
| seen | `ibm_kingston` | `ibm_kingston` | same_chip | circuit_only | 0.967 | 0.933 [0.84, 0.98] | 0.964 | PASS |
| seen | `ibm_kingston` | `ibm_kingston` | same_chip | mixed_submit | 0.936 | 0.829 [0.58, 0.94] | 0.922 |  |
| seen | `ibm_kingston` | `pooled` | pooled | circuit_only | 0.917 | 0.859 [0.56, 0.94] | 0.302 | INCONCLUSIVE |
| seen | `ibm_kingston` | `pooled` | pooled | mixed_submit | 0.940 | 0.842 [0.46, 0.94] | 0.010 |  |
| unseen | `ibm_marrakesh` | `ibm_fez` | cross_chip_zero_shot | circuit_only | 0.939 | 0.934 [0.88, 0.97] | 0.704 | PASS |
| unseen | `ibm_marrakesh` | `ibm_fez` | cross_chip_zero_shot | mixed_submit | 0.875 | 0.862 [0.77, 0.91] | -0.468 |  |
| unseen | `ibm_marrakesh` | `ibm_kingston` | cross_chip_zero_shot | circuit_only | 0.848 | 0.687 [0.41, 0.85] | -0.142 | INCONCLUSIVE |
| unseen | `ibm_marrakesh` | `ibm_kingston` | cross_chip_zero_shot | mixed_submit | 0.791 | 0.583 [0.32, 0.74] | -0.977 |  |
| unseen | `ibm_marrakesh` | `pooled` | pooled_zero_shot | circuit_only | 0.925 | 0.869 [0.74, 0.94] | 0.494 | INCONCLUSIVE |
| unseen | `ibm_marrakesh` | `pooled` | pooled_zero_shot | mixed_submit | 0.928 | 0.862 [0.77, 0.93] | 0.674 |  |

## hellinger

| QPU | Chip | Model scope | Transfer | Regime | anchor R² | new R² [95% CI] | extrapolation R² | new verdict |
|---|---|---|---|---|---:|---:|---:|:---:|
| seen | `ibm_fez` | `ibm_fez` | same_chip | circuit_only | 0.910 | 0.902 [0.82, 0.94] | 0.835 | PASS |
| seen | `ibm_fez` | `ibm_fez` | same_chip | mixed_submit | 0.861 | 0.951 [0.88, 0.98] | 0.893 |  |
| seen | `ibm_fez` | `pooled` | pooled | circuit_only | 0.976 | 0.954 [0.87, 0.97] | 0.834 | PASS |
| seen | `ibm_fez` | `pooled` | pooled | mixed_submit | 0.942 | 0.943 [0.85, 0.98] | 0.851 |  |
| seen | `ibm_kingston` | `ibm_kingston` | same_chip | circuit_only | 0.946 | 0.916 [0.79, 0.99] | 0.933 | INCONCLUSIVE |
| seen | `ibm_kingston` | `ibm_kingston` | same_chip | mixed_submit | 0.919 | 0.891 [0.56, 0.97] | 0.682 |  |
| seen | `ibm_kingston` | `pooled` | pooled | circuit_only | 0.850 | 0.850 [0.60, 0.95] | 0.627 | INCONCLUSIVE |
| seen | `ibm_kingston` | `pooled` | pooled | mixed_submit | 0.929 | 0.874 [0.65, 0.96] | 0.748 |  |
| unseen | `ibm_marrakesh` | `ibm_fez` | cross_chip_zero_shot | circuit_only | 0.937 | 0.866 [0.80, 0.92] | 0.683 | INCONCLUSIVE |
| unseen | `ibm_marrakesh` | `ibm_fez` | cross_chip_zero_shot | mixed_submit | 0.886 | 0.862 [0.73, 0.93] | 0.759 |  |
| unseen | `ibm_marrakesh` | `ibm_kingston` | cross_chip_zero_shot | circuit_only | 0.865 | 0.665 [0.38, 0.84] | -0.012 | INCONCLUSIVE |
| unseen | `ibm_marrakesh` | `ibm_kingston` | cross_chip_zero_shot | mixed_submit | 0.879 | 0.760 [0.56, 0.92] | -0.240 |  |
| unseen | `ibm_marrakesh` | `pooled` | pooled_zero_shot | circuit_only | 0.926 | 0.837 [0.61, 0.96] | 0.536 | INCONCLUSIVE |
| unseen | `ibm_marrakesh` | `pooled` | pooled_zero_shot | mixed_submit | 0.922 | 0.824 [0.66, 0.94] | 0.450 |  |

## tvd

| QPU | Chip | Model scope | Transfer | Regime | anchor R² | new R² [95% CI] | extrapolation R² | new verdict |
|---|---|---|---|---|---:|---:|---:|:---:|
| seen | `ibm_fez` | `ibm_fez` | same_chip | circuit_only | 0.927 | 0.924 [0.78, 0.98] | 0.810 | INCONCLUSIVE |
| seen | `ibm_fez` | `ibm_fez` | same_chip | mixed_submit | 0.829 | 0.961 [0.90, 0.98] | 0.884 |  |
| seen | `ibm_fez` | `pooled` | pooled | circuit_only | 0.961 | 0.974 [0.93, 0.98] | 0.765 | PASS |
| seen | `ibm_fez` | `pooled` | pooled | mixed_submit | 0.844 | 0.968 [0.92, 0.98] | 0.821 |  |
| seen | `ibm_kingston` | `ibm_kingston` | same_chip | circuit_only | 0.932 | 0.943 [0.84, 0.97] | 0.932 | PASS |
| seen | `ibm_kingston` | `ibm_kingston` | same_chip | mixed_submit | 0.931 | 0.927 [0.80, 0.97] | 0.857 |  |
| seen | `ibm_kingston` | `pooled` | pooled | circuit_only | 0.852 | 0.849 [0.62, 0.92] | 0.338 | INCONCLUSIVE |
| seen | `ibm_kingston` | `pooled` | pooled | mixed_submit | 0.920 | 0.878 [0.59, 0.95] | 0.744 |  |
| unseen | `ibm_marrakesh` | `ibm_fez` | cross_chip_zero_shot | circuit_only | 0.966 | 0.939 [0.90, 0.96] | 0.850 | PASS |
| unseen | `ibm_marrakesh` | `ibm_fez` | cross_chip_zero_shot | mixed_submit | 0.877 | 0.887 [0.80, 0.93] | 0.746 |  |
| unseen | `ibm_marrakesh` | `ibm_kingston` | cross_chip_zero_shot | circuit_only | 0.870 | 0.731 [0.49, 0.87] | -0.171 | INCONCLUSIVE |
| unseen | `ibm_marrakesh` | `ibm_kingston` | cross_chip_zero_shot | mixed_submit | 0.870 | 0.708 [0.51, 0.92] | -0.652 |  |
| unseen | `ibm_marrakesh` | `pooled` | pooled_zero_shot | circuit_only | 0.921 | 0.895 [0.76, 0.97] | 0.738 | INCONCLUSIVE |
| unseen | `ibm_marrakesh` | `pooled` | pooled_zero_shot | mixed_submit | 0.933 | 0.861 [0.78, 0.94] | 0.579 |  |

## dsr

| QPU | Chip | Model scope | Transfer | Regime | anchor R² | new R² [95% CI] | extrapolation R² | new verdict |
|---|---|---|---|---|---:|---:|---:|:---:|
| seen | `ibm_fez` | `ibm_fez` | same_chip | circuit_only | 0.813 | 0.050 [-1.93, 0.82] | 0.581 | INCONCLUSIVE |
| seen | `ibm_fez` | `ibm_fez` | same_chip | mixed_submit | 0.724 | 0.375 [-1.05, 0.89] | 0.784 |  |
| seen | `ibm_fez` | `pooled` | pooled | circuit_only | 0.917 | 0.658 [0.22, 0.79] | 0.515 | FAIL |
| seen | `ibm_fez` | `pooled` | pooled | mixed_submit | 0.795 | 0.725 [0.38, 0.81] | 0.680 |  |
| seen | `ibm_kingston` | `ibm_kingston` | same_chip | circuit_only | 0.861 | 0.290 [-0.92, 0.65] | 0.450 | FAIL |
| seen | `ibm_kingston` | `ibm_kingston` | same_chip | mixed_submit | 0.658 | -4.082 [-24.44, 0.23] | 0.370 |  |
| seen | `ibm_kingston` | `pooled` | pooled | circuit_only | 0.746 | -1.099 [-4.32, 0.41] | 0.503 | FAIL |
| seen | `ibm_kingston` | `pooled` | pooled | mixed_submit | 0.803 | -1.585 [-6.00, 0.26] | 0.606 |  |
| unseen | `ibm_marrakesh` | `ibm_fez` | cross_chip_zero_shot | circuit_only | 0.871 | 0.811 [0.48, 0.95] | 0.673 | INCONCLUSIVE |
| unseen | `ibm_marrakesh` | `ibm_fez` | cross_chip_zero_shot | mixed_submit | 0.779 | 0.728 [0.54, 0.81] | 0.556 |  |
| unseen | `ibm_marrakesh` | `ibm_kingston` | cross_chip_zero_shot | circuit_only | 0.765 | 0.213 [-1.09, 0.72] | 0.253 | FAIL |
| unseen | `ibm_marrakesh` | `ibm_kingston` | cross_chip_zero_shot | mixed_submit | 0.813 | 0.274 [-1.33, 0.79] | 0.687 |  |
| unseen | `ibm_marrakesh` | `pooled` | pooled_zero_shot | circuit_only | 0.873 | 0.612 [0.36, 0.81] | 0.396 | INCONCLUSIVE |
| unseen | `ibm_marrakesh` | `pooled` | pooled_zero_shot | mixed_submit | 0.848 | 0.563 [0.19, 0.72] | 0.480 |  |

