# QAQS model comparison on the validation run

246 validation jobs on `ibm_fez`, `ibm_kingston`, `ibm_marrakesh` (composite anchor excluded). Trained chips: `ibm_fez`, `ibm_kingston`; any other chip is unseen. No model here trained on these jobs.

The run was used to choose the best model, so this table describes that choice. It is not a pre-registered test of it; the next pre-registered run is.

## `dsr` · R² [95% CI] (MAE), all validation circuits

| Model | `ibm_fez` | `ibm_kingston` | `ibm_marrakesh` |
|---|---:|---:|---:|
| Per-chip models (best) | 0.755 [0.53, 0.86] (0.096) | 0.686 [-0.12, 0.85] (0.088) | 0.783 [0.61, 0.91] (0.095) |
| Pooled, no chip id | 0.811 [0.63, 0.93] (0.077) | 0.606 [-0.55, 0.86] (0.096) | 0.783 [0.61, 0.91] (0.095) |
| Pooled + chip id (candidate) | 0.800 [0.61, 0.90] (0.086) | 0.669 [-0.36, 0.89] (0.089) | 0.785 [0.64, 0.90] (0.100) |
| Per-chip + layout calibration | 0.772 [0.54, 0.88] (0.089) | 0.447 [-1.36, 0.78] (0.123) | 0.788 [0.63, 0.89] (0.098) |
| Size baseline (4 counts) | 0.600 [0.36, 0.78] (0.119) | 0.436 [-0.30, 0.68] (0.114) | 0.697 [0.53, 0.83] (0.117) |
| Pre-registered 2026-11-16 | 0.755 [0.53, 0.86] (0.096) | 0.686 [-0.12, 0.85] (0.088) | 0.783 [0.61, 0.91] (0.095) |

## `hellinger` · R² [95% CI] (MAE), all validation circuits

| Model | `ibm_fez` | `ibm_kingston` | `ibm_marrakesh` |
|---|---:|---:|---:|
| Per-chip models (best) | 0.932 [0.88, 0.96] (0.061) | 0.964 [0.93, 0.98] (0.035) | 0.904 [0.84, 0.94] (0.079) |
| Pooled, no chip id | 0.967 [0.95, 0.98] (0.045) | 0.882 [0.76, 0.94] (0.061) | 0.904 [0.84, 0.94] (0.079) |
| Pooled + chip id (candidate) | 0.959 [0.93, 0.98] (0.047) | 0.936 [0.87, 0.97] (0.046) | 0.866 [0.79, 0.91] (0.093) |
| Per-chip + layout calibration | 0.928 [0.86, 0.97] (0.058) | 0.922 [0.87, 0.96] (0.055) | 0.893 [0.84, 0.93] (0.085) |
| Size baseline (4 counts) | 0.948 [0.90, 0.97] (0.050) | 0.921 [0.87, 0.95] (0.053) | 0.913 [0.87, 0.94] (0.076) |
| Pre-registered 2026-11-16 | 0.932 [0.88, 0.96] (0.061) | 0.964 [0.93, 0.98] (0.035) | 0.904 [0.84, 0.94] (0.079) |

## `tvd` · R² [95% CI] (MAE), all validation circuits

| Model | `ibm_fez` | `ibm_kingston` | `ibm_marrakesh` |
|---|---:|---:|---:|
| Per-chip models (best) | 0.938 [0.89, 0.97] (0.054) | 0.963 [0.93, 0.98] (0.036) | 0.926 [0.89, 0.96] (0.069) |
| Pooled, no chip id | 0.955 [0.92, 0.98] (0.048) | 0.846 [0.71, 0.93] (0.072) | 0.926 [0.89, 0.96] (0.069) |
| Pooled + chip id (candidate) | 0.938 [0.88, 0.97] (0.056) | 0.932 [0.87, 0.97] (0.048) | 0.879 [0.82, 0.92] (0.090) |
| Per-chip + layout calibration | 0.915 [0.84, 0.96] (0.060) | 0.953 [0.93, 0.97] (0.042) | 0.913 [0.86, 0.94] (0.077) |
| Size baseline (4 counts) | 0.940 [0.89, 0.97] (0.053) | 0.920 [0.86, 0.95] (0.052) | 0.918 [0.88, 0.94] (0.073) |
| Pre-registered 2026-11-16 | 0.938 [0.89, 0.97] (0.054) | 0.963 [0.93, 0.98] (0.036) | 0.926 [0.89, 0.96] (0.069) |

## `success` · R² [95% CI] (MAE), all validation circuits

| Model | `ibm_fez` | `ibm_kingston` | `ibm_marrakesh` |
|---|---:|---:|---:|
| Per-chip models (best) | 0.938 [0.89, 0.96] (0.054) | 0.968 [0.95, 0.98] (0.035) | 0.899 [0.85, 0.94] (0.079) |
| Pooled, no chip id | 0.934 [0.90, 0.96] (0.054) | 0.844 [0.70, 0.92] (0.071) | 0.899 [0.85, 0.94] (0.079) |
| Pooled + chip id (candidate) | 0.932 [0.88, 0.96] (0.058) | 0.846 [0.69, 0.93] (0.066) | 0.899 [0.84, 0.93] (0.076) |
| Per-chip + layout calibration | 0.823 [0.66, 0.93] (0.078) | 0.931 [0.87, 0.96] (0.051) | 0.914 [0.86, 0.95] (0.070) |
| Size baseline (4 counts) | 0.917 [0.86, 0.95] (0.063) | 0.914 [0.86, 0.95] (0.053) | 0.829 [0.71, 0.91] (0.093) |
| Pre-registered 2026-11-16 | 0.938 [0.89, 0.96] (0.054) | 0.968 [0.95, 0.98] (0.035) | 0.899 [0.85, 0.94] (0.079) |

## Per-chip models against each alternative

Paired difference in R² (best minus alternative), mean over chips, bootstrap over configurations.

| Target | Alternative | ΔR² [95% CI] | Reading |
|---|---|---:|---|
| `dsr` | Pooled, no chip id | +0.008 [-0.04, 0.15] | no difference shown |
| `dsr` | Pooled + chip id (candidate) | -0.010 [-0.08, 0.09] | no difference shown |
| `dsr` | Per-chip + layout calibration | +0.072 [-0.02, 0.38] | no difference shown |
| `dsr` | Size baseline (4 counts) | +0.164 [-0.01, 0.31] | no difference shown |
| `dsr` | Pre-registered 2026-11-16 | +0.000 [0.00, 0.00] | no difference shown |
| `hellinger` | Pooled, no chip id | +0.016 [-0.01, 0.04] | no difference shown |
| `hellinger` | Pooled + chip id (candidate) | +0.013 [-0.00, 0.03] | no difference shown |
| `hellinger` | Per-chip + layout calibration | +0.019 [0.00, 0.04] | best is better |
| `hellinger` | Size baseline (4 counts) | +0.006 [-0.01, 0.02] | no difference shown |
| `hellinger` | Pre-registered 2026-11-16 | +0.000 [0.00, 0.00] | no difference shown |
| `tvd` | Pooled, no chip id | +0.033 [0.01, 0.07] | best is better |
| `tvd` | Pooled + chip id (candidate) | +0.026 [0.01, 0.05] | best is better |
| `tvd` | Per-chip + layout calibration | +0.016 [-0.01, 0.04] | no difference shown |
| `tvd` | Size baseline (4 counts) | +0.017 [-0.00, 0.04] | no difference shown |
| `tvd` | Pre-registered 2026-11-16 | +0.000 [0.00, 0.00] | no difference shown |
| `success` | Pooled, no chip id | +0.043 [0.02, 0.08] | best is better |
| `success` | Pooled + chip id (candidate) | +0.043 [0.01, 0.09] | best is better |
| `success` | Per-chip + layout calibration | +0.046 [0.02, 0.09] | best is better |
| `success` | Size baseline (4 counts) | +0.048 [0.01, 0.09] | best is better |
| `success` | Pre-registered 2026-11-16 | +0.000 [0.00, 0.00] | no difference shown |

