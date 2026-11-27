# QAQS quality-estimation report

Dataset `2fdcc81e9ec2` · chips: Cepheus-1-108Q, Forte-1, ibm_fez, ibm_kingston · providers: ibm, ionq, rigetti.

| Campaign role | Jobs | Use |
|---|---:|---|
| train | 2452 | everything in this report |
| validation | 252 | prospective validation only; never trained on |
| exploratory | 20 | one-off studies; never trained on |

Scopes: `Cepheus-1-108Q`, `Forte-1`, `ibm_fez`, `ibm_kingston`, `provider_ibm`, `pooled`.

Braket export `1d98a858767b` contributes 43 training jobs. The export reserves 15 jobs for testing.

## Verdicts

| Scope | `dsr` | `hellinger` | `tvd` | `success` | `success_adj` |
|---|---|---|---|---|---|
| `Cepheus-1-108Q` | FAIL (0.27) | INCONCLUSIVE (0.62) | FAIL (0.45) | FAIL (0.51) | FAIL (0.48) |
| `Forte-1` | — | — | — | — | — |
| `ibm_fez` | FAIL (0.40) | INCONCLUSIVE (0.76) | INCONCLUSIVE (0.78) | FAIL (0.69) | INCONCLUSIVE (0.70) |
| `ibm_kingston` | FAIL (0.51) | PASS (0.87) | PASS (0.87) | INCONCLUSIVE (0.83) | INCONCLUSIVE (0.85) |
| `provider_ibm` | FAIL (0.39) | INCONCLUSIVE (0.75) | INCONCLUSIVE (0.76) | FAIL (0.70) | INCONCLUSIVE (0.74) |
| `pooled` | FAIL (0.36) | FAIL (0.73) | FAIL (0.73) | FAIL (0.65) | INCONCLUSIVE (0.70) |

## Validation tests

| Test | Question | Method |
|---|---|---|
| **Unseen-circuit validation** | Does QAQS predict circuits it has never seen? | Repeated grouped K-fold by circuit configuration (5 folds × 3 repeats, 189 configurations, folds shared across chips). Footprint selection, tuning and model choice happen inside each training fold. |
| **Calibration-cycle validation** | Does QAQS predict a later calibration cycle? | Per chip: train on the earlier collection windows, test on the latest ones (mostly the same circuits). |
| **Prospective validation** | Does QAQS predict a run that did not exist at training time? | Frozen models, predictions committed before the results exist. |

R² is the mean over repeats ± sd between repeats; intervals are 95% cluster bootstraps that resample configurations.

## H1 · Does the footprint predict execution quality?

Unseen-circuit validation. PASS needs the whole 95% interval at or above 0.80.

- **Scored jobs.** `SHOR` sits at its chance level, so telling it apart from the other algorithms earns R² without predicting anything. Raw targets are scored without it; `success_adj` (chance-corrected success) scores every job.
- **Ceiling.** R² of predicting a job from the other repeats of the same circuit on the same chip. The footprint is identical across repeats, so no pre-runtime model can beat it at job level.
- **Config-mean R².** Observed and predicted averaged over the repeats of a circuit: the score with repeat-to-repeat noise removed.
- **Size baseline.** Same model class on four counts only (two-qubit gates, depth, width, measurements). **Gain** is footprint minus baseline, paired bootstrap over configurations.

### `Cepheus-1-108Q` · 36 jobs, 18 configurations

| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |
|---|---:|:---:|---:|---:|---:|---:|---:|
| Differential Success Rate (`dsr`) | 0.275 ± 0.115 [-1.18, 0.72] | FAIL | 0.2183 | 0.950 | 0.278 [-1.03, 0.75] | -0.127 | +0.399 [-0.44, 0.92] |
| Hellinger Fidelity (`hellinger`) | 0.622 ± 0.051 [0.13, 0.83] | INCONCLUSIVE | 0.1588 | 0.995 | 0.622 [0.12, 0.84] | -0.109 | +0.749 [0.44, 1.13] |
| Total Variation Distance (`tvd`) | 0.453 ± 0.113 [-0.25, 0.76] | FAIL | 0.1901 | 0.993 | 0.454 [-0.27, 0.75] | -0.106 | +0.509 [-0.18, 0.92] |
| Success Rate (`success`) | 0.510 ± 0.110 [-0.26, 0.75] | FAIL | 0.1864 | 0.994 | 0.511 [-0.21, 0.76] | -0.092 | +0.524 [-0.01, 0.88] |
| Chance-Corrected Success (`success_adj`) | 0.482 ± 0.143 [-0.50, 0.78] | FAIL | 0.1841 | 0.993 | 0.483 [-0.47, 0.78] | -0.104 | +0.455 [-0.28, 0.90] |

### `Forte-1` · 7 jobs, 7 configurations

| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |
|---|---:|:---:|---:|---:|---:|---:|---:|
| `dsr` | WAITING FOR DATA: 7 jobs, need 20 | | | | | | |
| `hellinger` | WAITING FOR DATA: 7 jobs, need 20 | | | | | | |
| `success` | WAITING FOR DATA: 7 jobs, need 20 | | | | | | |
| `success_adj` | WAITING FOR DATA: 7 jobs, need 20 | | | | | | |
| `tvd` | WAITING FOR DATA: 7 jobs, need 20 | | | | | | |

### `ibm_fez` · 1236 jobs, 189 configurations

| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |
|---|---:|:---:|---:|---:|---:|---:|---:|
| Differential Success Rate (`dsr`) | 0.403 ± 0.012 [0.27, 0.53] | FAIL | 0.1212 | 0.550 | 0.614 [0.42, 0.75] | 0.373 | +0.054 [-0.04, 0.14] |
| Hellinger Fidelity (`hellinger`) | 0.757 ± 0.003 [0.68, 0.82] | INCONCLUSIVE | 0.0677 | 0.721 | 0.924 [0.89, 0.95] | 0.743 | +0.010 [-0.02, 0.05] |
| Total Variation Distance (`tvd`) | 0.775 ± 0.006 [0.71, 0.84] | INCONCLUSIVE | 0.0655 | 0.732 | 0.930 [0.90, 0.95] | 0.755 | +0.012 [-0.02, 0.05] |
| Success Rate (`success`) | 0.691 ± 0.016 [0.58, 0.78] | FAIL | 0.0732 | 0.763 | 0.843 [0.74, 0.92] | 0.700 | -0.001 [-0.05, 0.05] |
| Chance-Corrected Success (`success_adj`) | 0.696 ± 0.018 [0.54, 0.81] | INCONCLUSIVE | 0.0833 | 0.810 | 0.822 [0.67, 0.92] | 0.697 | +0.022 [-0.03, 0.07] |

### `ibm_kingston` · 1173 jobs, 189 configurations

| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |
|---|---:|:---:|---:|---:|---:|---:|---:|
| Differential Success Rate (`dsr`) | 0.510 ± 0.025 [0.28, 0.67] | FAIL | 0.0874 | 0.771 | 0.604 [0.33, 0.80] | 0.193 | +0.248 [0.08, 0.43] |
| Hellinger Fidelity (`hellinger`) | 0.873 ± 0.004 [0.82, 0.92] | PASS | 0.0437 | 0.912 | 0.930 [0.90, 0.96] | 0.800 | +0.051 [0.02, 0.09] |
| Total Variation Distance (`tvd`) | 0.866 ± 0.001 [0.80, 0.92] | PASS | 0.0434 | 0.911 | 0.923 [0.86, 0.96] | 0.800 | +0.045 [0.01, 0.08] |
| Success Rate (`success`) | 0.826 ± 0.032 [0.74, 0.89] | INCONCLUSIVE | 0.0507 | 0.918 | 0.876 [0.78, 0.93] | 0.744 | +0.048 [-0.00, 0.10] |
| Chance-Corrected Success (`success_adj`) | 0.853 ± 0.005 [0.72, 0.93] | INCONCLUSIVE | 0.0597 | 0.953 | 0.861 [0.70, 0.95] | 0.774 | +0.098 [0.03, 0.18] |

### `provider_ibm` · 2409 jobs, 189 configurations

| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |
|---|---:|:---:|---:|---:|---:|---:|---:|
| Differential Success Rate (`dsr`) | 0.391 ± 0.015 [0.24, 0.52] | FAIL | 0.1113 | 0.634 | 0.533 [0.32, 0.70] | 0.274 | +0.117 [0.05, 0.19] |
| Hellinger Fidelity (`hellinger`) | 0.755 ± 0.005 [0.69, 0.81] | INCONCLUSIVE | 0.0657 | 0.798 | 0.881 [0.84, 0.91] | 0.725 | +0.021 [-0.01, 0.05] |
| Total Variation Distance (`tvd`) | 0.759 ± 0.007 [0.69, 0.82] | INCONCLUSIVE | 0.0630 | 0.804 | 0.883 [0.84, 0.91] | 0.730 | +0.016 [-0.02, 0.06] |
| Success Rate (`success`) | 0.703 ± 0.013 [0.60, 0.78] | FAIL | 0.0699 | 0.826 | 0.815 [0.71, 0.88] | 0.683 | +0.016 [-0.01, 0.05] |
| Chance-Corrected Success (`success_adj`) | 0.737 ± 0.011 [0.58, 0.84] | INCONCLUSIVE | 0.0814 | 0.879 | 0.805 [0.67, 0.89] | 0.718 | +0.034 [-0.01, 0.09] |

### `pooled` · 2452 jobs, 189 configurations

| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |
|---|---:|:---:|---:|---:|---:|---:|---:|
| Differential Success Rate (`dsr`) | 0.360 ± 0.029 [0.21, 0.49] | FAIL | 0.1201 | 0.666 | 0.441 [0.27, 0.59] | 0.287 | +0.019 [-0.08, 0.11] |
| Hellinger Fidelity (`hellinger`) | 0.729 ± 0.005 [0.66, 0.79] | FAIL | 0.0709 | 0.814 | 0.748 [0.67, 0.83] | 0.707 | +0.012 [-0.02, 0.04] |
| Total Variation Distance (`tvd`) | 0.729 ± 0.003 [0.66, 0.79] | FAIL | 0.0707 | 0.820 | 0.731 [0.64, 0.83] | 0.706 | +0.017 [-0.01, 0.05] |
| Success Rate (`success`) | 0.650 ± 0.021 [0.55, 0.73] | FAIL | 0.0762 | 0.840 | 0.642 [0.52, 0.77] | 0.657 | +0.012 [-0.03, 0.05] |
| Chance-Corrected Success (`success_adj`) | 0.696 ± 0.013 [0.53, 0.80] | INCONCLUSIVE | 0.0878 | 0.884 | 0.655 [0.50, 0.80] | 0.702 | -0.019 [-0.15, 0.07] |

### What each group of circuits contributes

R² of the same out-of-fold predictions on subsets. `all jobs` includes the composite anchor and is shown only to expose how much it inflates the score.

| Scope | Target | Headline | Core 6 | Random volumetric | Composite anchor | All jobs |
|---|---|---:|---:|---:|---:|---:|
| `Cepheus-1-108Q` | `dsr` | 0.275 | 0.047 | 0.707 | — | 0.275 |
| `Cepheus-1-108Q` | `hellinger` | 0.622 | 0.637 | 0.476 | — | 0.622 |
| `Cepheus-1-108Q` | `tvd` | 0.453 | 0.392 | 0.430 | — | 0.453 |
| `Cepheus-1-108Q` | `success` | 0.510 | 0.389 | 0.664 | — | 0.510 |
| `Cepheus-1-108Q` | `success_adj` | 0.482 | 0.335 | 0.623 | — | 0.482 |
| `ibm_fez` | `dsr` | 0.403 | 0.404 | 0.221 | -10.180 | 0.615 |
| `ibm_fez` | `hellinger` | 0.757 | 0.737 | 0.870 | 0.437 | 0.785 |
| `ibm_fez` | `tvd` | 0.775 | 0.759 | 0.872 | 0.523 | 0.801 |
| `ibm_fez` | `success` | 0.691 | 0.657 | 0.893 | -0.152 | 0.777 |
| `ibm_fez` | `success_adj` | 0.696 | 0.518 | 0.885 | -4.995 | 0.696 |
| `ibm_kingston` | `dsr` | 0.510 | 0.508 | -0.142 | -980.790 | 0.771 |
| `ibm_kingston` | `hellinger` | 0.873 | 0.878 | 0.815 | 0.454 | 0.888 |
| `ibm_kingston` | `tvd` | 0.866 | 0.870 | 0.821 | 0.637 | 0.896 |
| `ibm_kingston` | `success` | 0.826 | 0.830 | 0.773 | 0.425 | 0.909 |
| `ibm_kingston` | `success_adj` | 0.853 | 0.679 | 0.757 | -2.142 | 0.853 |
| `provider_ibm` | `dsr` | 0.391 | 0.387 | 0.225 | -81.424 | 0.661 |
| `provider_ibm` | `hellinger` | 0.755 | 0.744 | 0.800 | 0.424 | 0.798 |
| `provider_ibm` | `tvd` | 0.759 | 0.744 | 0.849 | 0.416 | 0.798 |
| `provider_ibm` | `success` | 0.703 | 0.684 | 0.794 | -0.354 | 0.809 |
| `provider_ibm` | `success_adj` | 0.737 | 0.507 | 0.816 | -2.481 | 0.737 |
| `pooled` | `dsr` | 0.360 | 0.361 | 0.100 | -11.800 | 0.635 |
| `pooled` | `hellinger` | 0.729 | 0.722 | 0.748 | 0.342 | 0.772 |
| `pooled` | `tvd` | 0.729 | 0.722 | 0.753 | 0.385 | 0.771 |
| `pooled` | `success` | 0.650 | 0.638 | 0.696 | -0.123 | 0.773 |
| `pooled` | `success_adj` | 0.696 | 0.463 | 0.704 | -2.269 | 0.696 |

### Per algorithm (`success`)

R² inside one algorithm is a harder test: the spread to explain is only that algorithm's own.

| Scope | Algorithm | Configs | Observed mean ± sd | R² [95% CI] | MAE | Ceiling |
|---|---|---:|---:|---:|---:|---:|
| `Cepheus-1-108Q` | BERNSTEIN-VAZIRANI | 3 | 0.25 ± 0.32 | -0.014 | 0.2294 | 0.998 |
| `Cepheus-1-108Q` | GHZ | 3 | 0.48 ± 0.35 | 0.586 | 0.1784 | 0.970 |
| `Cepheus-1-108Q` | GROVER | 3 | 0.48 ± 0.36 | 0.419 | 0.2154 | 0.997 |
| `Cepheus-1-108Q` | PHASE-ESTIMATION | 3 | 0.29 ± 0.22 | 0.667 | 0.0964 | 0.990 |
| `Cepheus-1-108Q` | QFT | 3 | 0.18 ± 0.15 | -2.400 | 0.1983 | 0.999 |
| `Cepheus-1-108Q` | RANDOM-VOLUMETRIC | 3 | 0.62 ± 0.46 | 0.664 | 0.2157 | 0.999 |
| `ibm_fez` | BERNSTEIN-VAZIRANI | 39 | 0.78 ± 0.21 | 0.738 [0.56, 0.89] | 0.0527 | 0.749 |
| `ibm_fez` | GHZ | 15 | 0.84 ± 0.09 | 0.370 [-0.58, 0.89] | 0.0426 | 0.934 |
| `ibm_fez` | GROVER | 29 | 0.64 ± 0.28 | 0.739 [0.45, 0.91] | 0.0768 | 0.794 |
| `ibm_fez` | PHASE-ESTIMATION | 21 | 0.72 ± 0.22 | 0.645 [0.45, 0.79] | 0.0856 | 0.808 |
| `ibm_fez` | QFT | 27 | 0.75 ± 0.21 | 0.514 [-0.67, 0.86] | 0.0859 | 0.876 |
| `ibm_fez` | RANDOM-VOLUMETRIC | 15 | 0.62 ± 0.26 | 0.893 [0.79, 0.94] | 0.0664 | 0.923 |
| `ibm_fez` | SHOR | 13 | 0.15 ± 0.10 | -0.152 [-1.72, 0.63] | 0.0771 | 0.900 |
| `ibm_fez` | VTP | 30 | 0.74 ± 0.20 | 0.374 [0.14, 0.57] | 0.0966 | 0.242 |
| `ibm_kingston` | BERNSTEIN-VAZIRANI | 39 | 0.76 ± 0.20 | 0.790 [0.60, 0.91] | 0.0504 | 0.850 |
| `ibm_kingston` | GHZ | 15 | 0.85 ± 0.08 | 0.825 [0.63, 0.90] | 0.0286 | 0.911 |
| `ibm_kingston` | GROVER | 29 | 0.67 ± 0.28 | 0.900 [0.68, 0.98] | 0.0439 | 0.969 |
| `ibm_kingston` | PHASE-ESTIMATION | 21 | 0.79 ± 0.15 | 0.760 [0.60, 0.85] | 0.0542 | 0.938 |
| `ibm_kingston` | QFT | 27 | 0.82 ± 0.15 | 0.675 [-0.26, 0.86] | 0.0624 | 0.923 |
| `ibm_kingston` | RANDOM-VOLUMETRIC | 15 | 0.68 ± 0.23 | 0.773 [0.54, 0.89] | 0.0724 | 0.903 |
| `ibm_kingston` | SHOR | 13 | 0.14 ± 0.10 | 0.425 [-0.37, 0.71] | 0.0555 | 0.843 |
| `ibm_kingston` | VTP | 30 | 0.83 ± 0.09 | 0.575 [0.32, 0.73] | 0.0451 | 0.650 |
| `provider_ibm` | BERNSTEIN-VAZIRANI | 39 | 0.77 ± 0.20 | 0.751 [0.61, 0.86] | 0.0560 | 0.795 |
| `provider_ibm` | GHZ | 15 | 0.85 ± 0.09 | 0.686 [0.34, 0.89] | 0.0338 | 0.924 |
| `provider_ibm` | GROVER | 29 | 0.65 ± 0.28 | 0.743 [0.42, 0.90] | 0.0748 | 0.875 |
| `provider_ibm` | PHASE-ESTIMATION | 21 | 0.75 ± 0.19 | 0.653 [0.49, 0.77] | 0.0728 | 0.852 |
| `provider_ibm` | QFT | 27 | 0.78 ± 0.18 | 0.542 [-0.39, 0.78] | 0.0858 | 0.896 |
| `provider_ibm` | RANDOM-VOLUMETRIC | 15 | 0.65 ± 0.25 | 0.794 [0.62, 0.87] | 0.0850 | 0.916 |
| `provider_ibm` | SHOR | 13 | 0.15 ± 0.10 | -0.354 [-2.82, 0.58] | 0.0808 | 0.867 |
| `provider_ibm` | VTP | 30 | 0.79 ± 0.16 | 0.359 [0.18, 0.51] | 0.0781 | 0.365 |
| `pooled` | BERNSTEIN-VAZIRANI | 39 | 0.76 ± 0.21 | 0.682 [0.53, 0.82] | 0.0641 | 0.814 |
| `pooled` | GHZ | 15 | 0.84 ± 0.12 | 0.554 [0.34, 0.85] | 0.0430 | 0.954 |
| `pooled` | GROVER | 29 | 0.65 ± 0.28 | 0.748 [0.46, 0.90] | 0.0742 | 0.878 |
| `pooled` | PHASE-ESTIMATION | 21 | 0.74 ± 0.20 | 0.524 [0.25, 0.70] | 0.0873 | 0.872 |
| `pooled` | QFT | 27 | 0.77 ± 0.20 | 0.492 [-0.30, 0.75] | 0.0916 | 0.914 |
| `pooled` | RANDOM-VOLUMETRIC | 15 | 0.65 ± 0.26 | 0.696 [0.39, 0.83] | 0.0944 | 0.923 |
| `pooled` | SHOR | 13 | 0.15 ± 0.10 | -0.123 [-1.16, 0.44] | 0.0760 | 0.867 |
| `pooled` | VTP | 30 | 0.79 ± 0.16 | 0.326 [0.15, 0.48] | 0.0808 | 0.365 |

### Targets with a point mass at the floor

Two-stage model (is the job above the floor, then how far) on the same footprint and folds.

| Scope | Target | Jobs at floor | Procedure R² | Two-stage R² | Procedure MAE | Two-stage MAE |
|---|---|---:|---:|---:|---:|---:|
| `Cepheus-1-108Q` | `dsr` | 55.6% | 0.275 | -0.127 | 0.2183 | 0.3461 |
| `Cepheus-1-108Q` | `hellinger` | 13.9% | 0.622 | -0.109 | 0.1588 | 0.3259 |
| `Cepheus-1-108Q` | `success` | 5.6% | 0.510 | -0.092 | 0.1864 | 0.3101 |
| `Cepheus-1-108Q` | `success_adj` | 27.8% | 0.482 | -0.105 | 0.1841 | 0.3147 |
| `ibm_fez` | `dsr` | 5.4% | 0.403 | 0.400 | 0.1212 | 0.1156 |
| `ibm_fez` | `success_adj` | 6.7% | 0.696 | 0.726 | 0.0833 | 0.0826 |
| `ibm_kingston` | `success_adj` | 6.2% | 0.853 | 0.864 | 0.0597 | 0.0575 |
| `provider_ibm` | `success_adj` | 6.5% | 0.737 | 0.753 | 0.0814 | 0.0811 |
| `pooled` | `success_adj` | 6.8% | 0.696 | 0.730 | 0.0878 | 0.0865 |

## H2 · Generalization to unseen configurations (`success`)

The held-out circuits are larger than any trained one, or from an algorithm absent from training. Footprint chosen on each protocol's own training set. `M2 prior alone` is the analytical estimate (uses submit-time calibration) with nothing learned; `M2 prior + residual` adds a footprint model of its error. Read the pair together: the gap is what the footprint adds.

| Scope | Protocol | Task | nTrain / nTest | R² [95% CI] | MAE |
|---|---|---|---:|---:|---:|
| `Cepheus-1-108Q` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 24 / 6 | -2.197 | 0.1986 |
| `Cepheus-1-108Q` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 24 / 6 | -0.089 | 0.1949 |
| `Cepheus-1-108Q` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 24 / 6 | -0.311 | 0.2884 |
| `Cepheus-1-108Q` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 24 / 6 | -0.119 | 0.3131 |
| `Cepheus-1-108Q` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 24 / 6 | -0.314 | 0.3208 |
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 232 / 72 | -0.288 [-1.71, 0.16] | 0.2070 |
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior alone | 0 / 72 | -0.131 [-1.82, 0.38] | 0.1967 |
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 232 / 72 | 0.528 [0.05, 0.72] | 0.1215 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 352 / 110 | -1.134 [-2.31, -0.53] | 0.2892 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior alone | 0 / 110 | 0.241 [-0.30, 0.58] | 0.1664 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 352 / 110 | 0.587 [0.27, 0.79] | 0.0914 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 214 / 72 | -0.171 [-0.53, -0.03] | 0.1122 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior alone | 0 / 36 | -0.891 [-1.80, -0.72] | 0.1918 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 214 / 72 | -0.156 [-0.61, 0.17] | 0.1002 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 882 / 170 | 0.188 [-1.50, 0.60] | 0.1568 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 918 / 134 | 0.377 [0.08, 0.56] | 0.1223 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 850 / 202 | 0.533 [0.22, 0.70] | 0.1121 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 792 / 260 | -1.170 [-2.84, -0.60] | 0.2718 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 864 / 188 | 0.031 [-0.26, 0.30] | 0.1265 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 954 / 98 | -5.501 [-13.23, -2.53] | 0.2064 |
| `ibm_fez` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 1052 / 86 | -6.573 [-24.63, -2.00] | 0.2201 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 216 / 72 | -0.182 [-1.99, 0.39] | 0.1330 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior alone | 0 / 72 | 0.340 [-0.81, 0.66] | 0.1034 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 216 / 72 | 0.737 [0.28, 0.88] | 0.0597 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 306 / 102 | -1.629 [-3.24, -0.96] | 0.3242 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior alone | 0 / 102 | 0.904 [0.79, 0.95] | 0.0596 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 306 / 102 | 0.945 [0.87, 0.98] | 0.0387 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 198 / 72 | 0.376 [-0.36, 0.49] | 0.0476 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior alone | 0 / 36 | -2.614 [-9.18, -1.75] | 0.0767 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 198 / 72 | 0.459 [-0.03, 0.55] | 0.0429 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 804 / 162 | 0.405 [-1.03, 0.69] | 0.0852 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 840 / 126 | 0.197 [-0.45, 0.51] | 0.1009 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 792 / 174 | 0.048 [-0.34, 0.30] | 0.1694 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 732 / 234 | 0.155 [-0.26, 0.30] | 0.1511 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 786 / 180 | 0.429 [0.13, 0.62] | 0.0597 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 876 / 90 | -2.491 [-6.23, -1.09] | 0.1389 |
| `ibm_kingston` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 966 / 117 | -12.242 [-33.55, -6.58] | 0.3138 |
| `provider_ibm` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 448 / 144 | 0.001 [-0.98, 0.42] | 0.1550 |
| `provider_ibm` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior alone | 0 / 144 | 0.137 [-0.82, 0.50] | 0.1501 |
| `provider_ibm` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 448 / 144 | 0.638 [0.28, 0.80] | 0.0904 |
| `provider_ibm` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 658 / 212 | -0.956 [-2.12, -0.42] | 0.2718 |
| `provider_ibm` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior alone | 0 / 212 | 0.556 [0.22, 0.75] | 0.1150 |
| `provider_ibm` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 658 / 212 | 0.743 [0.54, 0.87] | 0.0745 |
| `provider_ibm` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 412 / 144 | 0.042 [-0.15, 0.13] | 0.0875 |
| `provider_ibm` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior alone | 0 / 72 | -0.609 [-1.14, -0.50] | 0.1342 |
| `provider_ibm` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 412 / 144 | 0.055 [-0.20, 0.31] | 0.0746 |
| `provider_ibm` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 1686 / 332 | 0.236 [-1.30, 0.61] | 0.1313 |
| `provider_ibm` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 1758 / 260 | 0.393 [0.11, 0.65] | 0.1018 |
| `provider_ibm` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 1642 / 376 | -0.581 [-1.11, -0.25] | 0.2338 |
| `provider_ibm` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 1524 / 494 | -0.326 [-1.12, -0.06] | 0.2029 |
| `provider_ibm` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 1650 / 368 | 0.243 [0.05, 0.42] | 0.0784 |
| `provider_ibm` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 1830 / 188 | -1.882 [-5.17, -0.50] | 0.1314 |
| `provider_ibm` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 2018 / 203 | -5.804 [-16.36, -2.47] | 0.2149 |
| `pooled` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 448 / 144 | 0.001 [-0.98, 0.42] | 0.1550 |
| `pooled` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior alone | 0 / 144 | 0.137 [-0.82, 0.50] | 0.1501 |
| `pooled` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 448 / 144 | 0.638 [0.28, 0.80] | 0.0904 |
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 658 / 212 | -0.956 [-2.12, -0.42] | 0.2718 |
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior alone | 0 / 212 | 0.556 [0.22, 0.75] | 0.1150 |
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 658 / 212 | 0.743 [0.54, 0.87] | 0.0745 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 412 / 144 | 0.042 [-0.15, 0.13] | 0.0875 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior alone | 0 / 72 | -0.609 [-1.14, -0.50] | 0.1342 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 412 / 144 | 0.055 [-0.20, 0.31] | 0.0746 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 1713 / 340 | 0.358 [-0.59, 0.62] | 0.1255 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 1787 / 266 | 0.495 [0.26, 0.70] | 0.0970 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 1670 / 383 | -0.043 [-0.43, 0.18] | 0.2066 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 1553 / 500 | -0.093 [-0.67, 0.13] | 0.1905 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 1685 / 368 | 0.200 [0.02, 0.37] | 0.0868 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 1857 / 196 | -0.343 [-2.28, 0.22] | 0.1165 |
| `pooled` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 2053 / 203 | -5.079 [-14.93, -2.08] | 0.2067 |

## H3 · Hardware context and transfer (`success`)

Two kinds of calibration input. **Device** (`cal.*`): one value per calibration snapshot, blind to the circuit. **Layout** (`c.*`): calibration of the qubits the circuit was mapped to, so it also carries circuit size.

Judge calibration regimes on the **calibration-cycle** column: there the test windows are new calibration cycles. In the unseen-circuit column train and test share windows, so any input that identifies the window helps; the `collection-window id` row is the control for that.

| Scope | Regime | Features | Unseen-circuit R² ± sd | Calibration-cycle R² [95% CI] | Calibration-cycle MAE |
|---|---|---:|---:|---:|---:|
| `Cepheus-1-108Q` | Circuit footprint only (a.* + b.*) | 4 | 0.510 ± 0.110 | — | — |
| `Cepheus-1-108Q` | Size baseline (2Q gates, depth, width, measurements) | 1 | -0.092 ± 0.035 | — | — |
| `Cepheus-1-108Q` | Footprint, two-stage (floor / above floor) | 4 | -0.092 ± 0.035 | — | — |
| `ibm_fez` | Circuit footprint only (a.* + b.*) | 7 | 0.691 ± 0.016 | 0.649 [0.53, 0.76] | 0.0855 |
| `ibm_fez` | Size baseline (2Q gates, depth, width, measurements) | 4 | 0.700 ± 0.007 | 0.654 [0.54, 0.77] | 0.0864 |
| `ibm_fez` | Device calibration only (cal.*, one value per snapshot) | 7 | 0.037 ± 0.005 | -0.183 [-0.34, -0.03] | 0.2085 |
| `ibm_fez` | Layout calibration only (c.*, qubits the circuit uses) | 7 | 0.613 ± 0.002 | 0.362 [0.20, 0.47] | 0.1670 |
| `ibm_fez` | Footprint + device calibration (cal.*) | 14 | 0.754 ± 0.012 | 0.671 [0.57, 0.77] | 0.0855 |
| `ibm_fez` | Footprint + layout calibration (c.*) | 14 | 0.813 ± 0.001 | 0.672 [0.58, 0.77] | 0.0953 |
| `ibm_fez` | Footprint + collection-window id (control) | 8 | 0.741 ± 0.011 | — | — |
| `ibm_kingston` | Circuit footprint only (a.* + b.*) | 6 | 0.826 ± 0.032 | 0.909 [0.86, 0.94] | 0.0414 |
| `ibm_kingston` | Size baseline (2Q gates, depth, width, measurements) | 4 | 0.744 ± 0.010 | 0.908 [0.86, 0.94] | 0.0437 |
| `ibm_kingston` | Device calibration only (cal.*, one value per snapshot) | 7 | -0.137 ± 0.002 | -0.797 [-1.49, -0.45] | 0.2088 |
| `ibm_kingston` | Layout calibration only (c.*, qubits the circuit uses) | 7 | 0.585 ± 0.019 | 0.122 [-0.15, 0.29] | 0.1325 |
| `ibm_kingston` | Footprint + device calibration (cal.*) | 13 | 0.810 ± 0.007 | 0.908 [0.86, 0.94] | 0.0415 |
| `ibm_kingston` | Footprint + layout calibration (c.*) | 13 | 0.795 ± 0.016 | 0.877 [0.82, 0.91] | 0.0468 |
| `ibm_kingston` | Footprint + collection-window id (control) | 7 | 0.809 ± 0.010 | — | — |
| `provider_ibm` | Circuit footprint only (a.* + b.*) | 7 | 0.703 ± 0.013 | — | — |
| `provider_ibm` | Size baseline (2Q gates, depth, width, measurements) | 4 | 0.683 ± 0.010 | — | — |
| `provider_ibm` | Device calibration only (cal.*, one value per snapshot) | 7 | -0.023 ± 0.004 | — | — |
| `provider_ibm` | Layout calibration only (c.*, qubits the circuit uses) | 7 | 0.591 ± 0.010 | — | — |
| `provider_ibm` | Footprint + device calibration (cal.*) | 14 | 0.783 ± 0.002 | — | — |
| `provider_ibm` | Footprint + layout calibration (c.*) | 14 | 0.808 ± 0.007 | — | — |
| `provider_ibm` | Footprint + collection-window id (control) | 8 | 0.776 ± 0.005 | — | — |
| `provider_ibm` | Footprint + chip id (one model for all chips) | 9 | 0.736 ± 0.009 | — | — |
| `pooled` | Circuit footprint only (a.* + b.*) | 6 | 0.650 ± 0.021 | — | — |
| `pooled` | Size baseline (2Q gates, depth, width, measurements) | 4 | 0.657 ± 0.008 | — | — |
| `pooled` | Device calibration only (cal.*, one value per snapshot) | 7 | 0.006 ± 0.005 | — | — |
| `pooled` | Layout calibration only (c.*, qubits the circuit uses) | 7 | 0.567 ± 0.005 | — | — |
| `pooled` | Footprint + device calibration (cal.*) | 13 | 0.745 ± 0.004 | — | — |
| `pooled` | Footprint + layout calibration (c.*) | 13 | 0.782 ± 0.008 | — | — |
| `pooled` | Footprint + collection-window id (control) | 7 | 0.740 ± 0.003 | — | — |
| `pooled` | Footprint + chip id (one model for all chips) | 10 | 0.734 ± 0.009 | — | — |

- `ibm_fez` calibration-cycle split: 787 training jobs (16 calibration snapshots), 410 test jobs (6 snapshots); 171 of 176 test configurations also trained; strictly later than training: yes.
- `ibm_kingston` calibration-cycle split: 782 training jobs (3 calibration snapshots), 352 test jobs (3 snapshots); 176 of 176 test configurations also trained; strictly later than training: yes.

### Cross-chip transfer (zero-shot)

Model trained on the source chip with the footprint chosen there, scored on every job of the target chip. Diagonal cells are within-chip grouped CV.

| Source | Target | Regime | Same provider | R² [95% CI] | MAE |
|---|---|---|:---:|---:|---:|
| `Cepheus-1-108Q` | `Cepheus-1-108Q` | Circuit Footprint Only | yes | -0.177 [-0.82, -0.09] | 0.3211 |
| `Cepheus-1-108Q` | `ibm_fez` | Circuit Footprint Only | no | -2.316 [-3.32, -1.66] | 0.3823 |
| `Cepheus-1-108Q` | `ibm_kingston` | Circuit Footprint Only | no | -3.986 [-6.20, -2.77] | 0.4040 |
| `ibm_fez` | `Cepheus-1-108Q` | Circuit Footprint Only | no | -0.913 [-4.06, -0.16] | 0.4132 |
| `ibm_fez` | `ibm_fez` | Circuit Footprint Only | yes | 0.702 [0.59, 0.80] | 0.0731 |
| `ibm_fez` | `ibm_fez` | Device Calibration Only | yes | 0.053 [-0.04, 0.12] | 0.1763 |
| `ibm_fez` | `ibm_fez` | Mixed (Footprint + Layout Calibration) | yes | 0.808 [0.70, 0.88] | 0.0567 |
| `ibm_fez` | `ibm_kingston` | Circuit Footprint Only | yes | 0.661 [0.52, 0.75] | 0.0811 |
| `ibm_fez` | `ibm_kingston` | Device Calibration Only | yes | -0.800 [-1.43, -0.49] | 0.2272 |
| `ibm_fez` | `ibm_kingston` | Mixed (Footprint + Layout Calibration) | yes | 0.416 [0.16, 0.61] | 0.0898 |
| `ibm_kingston` | `Cepheus-1-108Q` | Circuit Footprint Only | no | -1.160 [-4.96, -0.24] | 0.4275 |
| `ibm_kingston` | `ibm_fez` | Circuit Footprint Only | yes | 0.618 [0.53, 0.70] | 0.0810 |
| `ibm_kingston` | `ibm_fez` | Device Calibration Only | yes | -0.657 [-1.01, -0.44] | 0.2250 |
| `ibm_kingston` | `ibm_fez` | Mixed (Footprint + Layout Calibration) | yes | 0.630 [0.54, 0.72] | 0.0783 |
| `ibm_kingston` | `ibm_kingston` | Circuit Footprint Only | yes | 0.823 [0.73, 0.89] | 0.0494 |
| `ibm_kingston` | `ibm_kingston` | Device Calibration Only | yes | -0.137 [-0.33, -0.05] | 0.1672 |
| `ibm_kingston` | `ibm_kingston` | Mixed (Footprint + Layout Calibration) | yes | 0.823 [0.73, 0.89] | 0.0488 |

### Cross-provider transfer (leave one provider out)

| Held-out provider | Trained on | Regime | nTrain / nTest | R² [95% CI] | MAE |
|---|---|---|---:|---:|---:|
| `ibm` | ionq, rigetti | Circuit footprint only (a.* + b.*) | 43 / 2206 | -2.995 [-4.48, -2.10] | 0.3746 |
| `ibm` | ionq, rigetti | Size baseline (2Q gates, depth, width, measurements) | 43 / 2206 | -2.873 [-4.26, -2.00] | 0.3619 |
| `rigetti` | ibm, ionq | Circuit footprint only (a.* + b.*) | 2416 / 36 | -0.990 [-4.54, -0.13] | 0.4147 |
| `rigetti` | ibm, ionq | Size baseline (2Q gates, depth, width, measurements) | 2416 / 36 | -0.782 [-4.00, -0.05] | 0.3752 |

## H4 · Paradigm circuits vs random-volumetric circuits (`success`)

Forward rows test on paradigm circuits, reverse rows on random-volumetric (RV) circuits; every test configuration is predicted once by a model that never saw it. `size-matched` trains on as many paradigm rows as there are RV rows.

| Scope | Regime | nTrain | nTest | R² [95% CI] | MAE |
|---|---|---:|---:|---:|---:|
| `Cepheus-1-108Q` | Reverse · paradigm-trained, tested on RV | 24 | 6 | -0.569 | 0.5065 |
| `ibm_fez` | Random Volumetric Only (RV) | 98 | 1052 | 0.262 [0.10, 0.40] | 0.1415 |
| `ibm_fez` | Paradigm Algorithms Only (6 Core) | 841 | 1052 | 0.692 [0.58, 0.79] | 0.0737 |
| `ibm_fez` | Combined (RV + 6 Core) | 939 | 1052 | 0.701 [0.60, 0.80] | 0.0722 |
| `ibm_fez` | Paradigm Only, size-matched to RV | 98 | 1052 | 0.336 [0.22, 0.46] | 0.1243 |
| `ibm_fez` | Reverse · paradigm-trained, tested on RV | 841 | 98 | 0.801 [0.49, 0.91] | 0.0844 |
| `ibm_fez` | Reverse · RV-trained, tested on unseen RV | 78 | 98 | 0.812 [0.65, 0.88] | 0.0840 |
| `ibm_kingston` | Random Volumetric Only (RV) | 90 | 966 | 0.563 [0.37, 0.68] | 0.0873 |
| `ibm_kingston` | Paradigm Algorithms Only (6 Core) | 772 | 966 | 0.783 [0.64, 0.86] | 0.0544 |
| `ibm_kingston` | Combined (RV + 6 Core) | 862 | 966 | 0.802 [0.67, 0.88] | 0.0526 |
| `ibm_kingston` | Paradigm Only, size-matched to RV | 90 | 966 | 0.429 [0.26, 0.61] | 0.0976 |
| `ibm_kingston` | Reverse · paradigm-trained, tested on RV | 772 | 90 | 0.839 [0.69, 0.89] | 0.0757 |
| `ibm_kingston` | Reverse · RV-trained, tested on unseen RV | 72 | 90 | 0.776 [0.54, 0.86] | 0.0805 |
| `provider_ibm` | Random Volumetric Only (RV) | 188 | 2018 | 0.305 [0.12, 0.46] | 0.1266 |
| `provider_ibm` | Paradigm Algorithms Only (6 Core) | 1614 | 2018 | 0.700 [0.59, 0.79] | 0.0685 |
| `provider_ibm` | Combined (RV + 6 Core) | 1802 | 2018 | 0.693 [0.57, 0.78] | 0.0696 |
| `provider_ibm` | Paradigm Only, size-matched to RV | 188 | 2018 | 0.385 [0.21, 0.49] | 0.1066 |
| `provider_ibm` | Reverse · paradigm-trained, tested on RV | 1614 | 188 | 0.654 [0.17, 0.80] | 0.1143 |
| `provider_ibm` | Reverse · RV-trained, tested on unseen RV | 150 | 188 | 0.829 [0.69, 0.88] | 0.0765 |
| `pooled` | Random Volumetric Only (RV) | 196 | 2053 | -0.407 [-0.77, -0.15] | 0.1939 |
| `pooled` | Paradigm Algorithms Only (6 Core) | 1642 | 2053 | 0.688 [0.58, 0.76] | 0.0732 |
| `pooled` | Combined (RV + 6 Core) | 1838 | 2053 | 0.680 [0.57, 0.76] | 0.0743 |
| `pooled` | Paradigm Only, size-matched to RV | 196 | 2053 | 0.304 [0.18, 0.44] | 0.1137 |
| `pooled` | Reverse · paradigm-trained, tested on RV | 1642 | 196 | 0.592 [0.16, 0.74] | 0.1189 |
| `pooled` | Reverse · RV-trained, tested on unseen RV | 156 | 196 | 0.701 [0.39, 0.83] | 0.0990 |

Two intervals that overlap do not show two regimes are equal, and two that do not overlap are not the test either. The comparison is the paired difference on the same test jobs:

| Scope | Question | R²(a) − R²(b) [95% CI] | Verdict |
|---|---|---:|---|
| `ibm_fez` | Same training size: do paradigm circuits predict paradigm circuits better than RV circuits do? (`paradigm_matched` − `random_only`) | +0.089 [-0.05, 0.24] | no difference shown |
| `ibm_fez` | Do RV circuits add anything once paradigm circuits are in training? (`combined` − `paradigm_only`) | +0.009 [-0.00, 0.02] | no difference shown |
| `ibm_fez` | Do paradigm circuits add anything once RV circuits are in training? (`combined` − `random_only`) | +0.439 [0.32, 0.60] | first is better |
| `ibm_fez` | Reverse: do RV circuits predict RV circuits better than paradigm circuits do? (`reverse_random_cv` − `reverse_paradigm`) | +0.011 [-0.12, 0.25] | no difference shown |
| `ibm_kingston` | Same training size: do paradigm circuits predict paradigm circuits better than RV circuits do? (`paradigm_matched` − `random_only`) | -0.102 [-0.22, 0.01] | no difference shown |
| `ibm_kingston` | Do RV circuits add anything once paradigm circuits are in training? (`combined` − `paradigm_only`) | +0.018 [0.00, 0.04] | first is better |
| `ibm_kingston` | Do paradigm circuits add anything once RV circuits are in training? (`combined` − `random_only`) | +0.238 [0.15, 0.36] | first is better |
| `ibm_kingston` | Reverse: do RV circuits predict RV circuits better than paradigm circuits do? (`reverse_random_cv` − `reverse_paradigm`) | -0.063 [-0.20, 0.05] | no difference shown |
| `provider_ibm` | Same training size: do paradigm circuits predict paradigm circuits better than RV circuits do? (`paradigm_matched` − `random_only`) | +0.059 [-0.08, 0.20] | no difference shown |
| `provider_ibm` | Do RV circuits add anything once paradigm circuits are in training? (`combined` − `paradigm_only`) | -0.007 [-0.02, 0.01] | no difference shown |
| `provider_ibm` | Do paradigm circuits add anything once RV circuits are in training? (`combined` − `random_only`) | +0.389 [0.29, 0.52] | first is better |
| `provider_ibm` | Reverse: do RV circuits predict RV circuits better than paradigm circuits do? (`reverse_random_cv` − `reverse_paradigm`) | +0.175 [0.04, 0.51] | first is better |
| `pooled` | Same training size: do paradigm circuits predict paradigm circuits better than RV circuits do? (`paradigm_matched` − `random_only`) | +0.724 [0.41, 1.10] | first is better |
| `pooled` | Do RV circuits add anything once paradigm circuits are in training? (`combined` − `paradigm_only`) | -0.008 [-0.03, 0.01] | no difference shown |
| `pooled` | Do paradigm circuits add anything once RV circuits are in training? (`combined` − `random_only`) | +1.087 [0.84, 1.43] | first is better |
| `pooled` | Reverse: do RV circuits predict RV circuits better than paradigm circuits do? (`reverse_random_cv` − `reverse_paradigm`) | +0.109 [-0.04, 0.38] | no difference shown |

## The footprint

A feature belongs to the footprint only if the selection procedure picks it in at least 80% of the outer folds. Features chosen once on the full data but rarely inside folds are listed in `footprint.csv` with their selection frequency and are not part of the claim.

| Feature | Category | Stable in (scope × target) | Mean selection frequency |
|---|---|---:|---:|
| `b.ComplexityMetrics.standardized_metrics.circuit_volume` | ISA Compiled | 18 / 25 | 0.98 |
| `b.ComplexityMetrics.standardized_metrics.gate_density` | ISA Compiled | 11 / 25 | 0.92 |
| `a.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` |  | 8 / 25 | 0.86 |
| `a.quantum_specific.magic` | Quantum Specific | 6 / 25 | 0.91 |
| `b.ComplexityMetrics.entanglement_metrics.entangling_width` | ISA Compiled | 4 / 25 | 0.95 |
| `b.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` | ISA Compiled | 3 / 25 | 0.98 |
| `b.StructuralMetrics.effort` | ISA Compiled | 3 / 25 | 0.80 |
| `a.StructuralMetrics.difficulty` | Logical Structural | 1 / 25 | 0.87 |
| `b.StructuralMetrics.vocabulary` | ISA Compiled | 1 / 25 | 0.87 |
| `a.StructuralMetrics.avg_dens` | Logical Structural | 1 / 25 | 0.83 |
| `a.StructuralMetrics.volume` | Logical Structural | 1 / 25 | 0.83 |
| `a.StructuralMetrics.effort` | Logical Structural | 1 / 25 | 0.80 |

Footprint size is the smallest k whose selection score is within 0.0015 R² of the best k. The ablation R² in `footprint_ablation.csv` is a selection score, not accuracy.

| Scope | Target | k deployed | k across folds (min–median–max) | Stable features |
|---|---|---:|---:|---:|
| `Cepheus-1-108Q` | `dsr` | 5 | 4–5–5 | 0 |
| `Cepheus-1-108Q` | `hellinger` | 5 | 4–5–5 | 1 |
| `Cepheus-1-108Q` | `tvd` | 5 | 4–5–5 | 0 |
| `Cepheus-1-108Q` | `success` | 5 | 2–5–5 | 1 |
| `Cepheus-1-108Q` | `success_adj` | 5 | 4–5–5 | 0 |
| `ibm_fez` | `dsr` | 6 | 6–8–10 | 5 |
| `ibm_fez` | `hellinger` | 10 | 3–6–10 | 3 |
| `ibm_fez` | `tvd` | 10 | 3–7–10 | 3 |
| `ibm_fez` | `success` | 8 | 3–7–10 | 2 |
| `ibm_fez` | `success_adj` | 10 | 3–7–10 | 2 |
| `ibm_kingston` | `dsr` | 6 | 5–6–8 | 3 |
| `ibm_kingston` | `hellinger` | 8 | 5–7–10 | 5 |
| `ibm_kingston` | `tvd` | 7 | 4–7–10 | 4 |
| `ibm_kingston` | `success` | 10 | 4–7–10 | 4 |
| `ibm_kingston` | `success_adj` | 6 | 4–6–8 | 4 |
| `provider_ibm` | `dsr` | 10 | 5–8–10 | 5 |
| `provider_ibm` | `hellinger` | 8 | 5–7–10 | 3 |
| `provider_ibm` | `tvd` | 8 | 5–7–10 | 1 |
| `provider_ibm` | `success` | 10 | 5–7–10 | 1 |
| `provider_ibm` | `success_adj` | 7 | 5–7–10 | 1 |
| `pooled` | `dsr` | 10 | 5–7–10 | 4 |
| `pooled` | `hellinger` | 10 | 5–7–10 | 3 |
| `pooled` | `tvd` | 7 | 5–7–10 | 1 |
| `pooled` | `success` | 10 | 5–7–10 | 1 |
| `pooled` | `success_adj` | 7 | 5–7–10 | 1 |

## Saved models

Each model is fitted on all eligible jobs in its scope.

| Scope | Target | Regime | Model | Features | Procedure R² | MAE | Artifact |
|---|---|---|---|---:|---:|---:|---|
| `Cepheus-1-108Q` | `dsr` | `circuit_only` | KNN | 5 | 0.275 | 0.2183 | `models/Cepheus-1-108Q_dsr_circuit_only.joblib` |
| `Cepheus-1-108Q` | `hellinger` | `circuit_only` | LR | 5 | 0.622 | 0.1588 | `models/Cepheus-1-108Q_hellinger_circuit_only.joblib` |
| `Cepheus-1-108Q` | `tvd` | `circuit_only` | SVR | 5 | 0.453 | 0.1901 | `models/Cepheus-1-108Q_tvd_circuit_only.joblib` |
| `Cepheus-1-108Q` | `success` | `circuit_only` | LR | 5 | 0.510 | 0.1864 | `models/Cepheus-1-108Q_success_circuit_only.joblib` |
| `Cepheus-1-108Q` | `success_adj` | `circuit_only` | SVR | 5 | 0.482 | 0.1841 | `models/Cepheus-1-108Q_success_adj_circuit_only.joblib` |
| `ibm_fez` | `dsr` | `circuit_only` | XGBoost | 6 | 0.403 | 0.1212 | `models/ibm_fez_dsr_circuit_only.joblib` |
| `ibm_fez` | `dsr` | `mixed_submit` | LightGBM | 13 | 0.655 | 0.0903 | `models/ibm_fez_dsr_mixed_submit.joblib` |
| `ibm_fez` | `hellinger` | `circuit_only` | XGBoost | 10 | 0.757 | 0.0677 | `models/ibm_fez_hellinger_circuit_only.joblib` |
| `ibm_fez` | `hellinger` | `mixed_submit` | LightGBM | 17 | 0.889 | 0.0500 | `models/ibm_fez_hellinger_mixed_submit.joblib` |
| `ibm_fez` | `tvd` | `circuit_only` | RF | 10 | 0.775 | 0.0655 | `models/ibm_fez_tvd_circuit_only.joblib` |
| `ibm_fez` | `tvd` | `mixed_submit` | XGBoost | 17 | 0.890 | 0.0489 | `models/ibm_fez_tvd_mixed_submit.joblib` |
| `ibm_fez` | `success` | `circuit_only` | RF | 8 | 0.691 | 0.0732 | `models/ibm_fez_success_circuit_only.joblib` |
| `ibm_fez` | `success` | `mixed_submit` | XGBoost | 15 | 0.813 | 0.0570 | `models/ibm_fez_success_mixed_submit.joblib` |
| `ibm_fez` | `success_adj` | `circuit_only` | SVR | 10 | 0.696 | 0.0833 | `models/ibm_fez_success_adj_circuit_only.joblib` |
| `ibm_fez` | `success_adj` | `mixed_submit` | SVR | 17 | 0.799 | 0.0697 | `models/ibm_fez_success_adj_mixed_submit.joblib` |
| `ibm_kingston` | `dsr` | `circuit_only` | SVR | 6 | 0.510 | 0.0874 | `models/ibm_kingston_dsr_circuit_only.joblib` |
| `ibm_kingston` | `dsr` | `mixed_submit` | XGBoost | 13 | 0.524 | 0.0845 | `models/ibm_kingston_dsr_mixed_submit.joblib` |
| `ibm_kingston` | `hellinger` | `circuit_only` | SVR | 8 | 0.873 | 0.0437 | `models/ibm_kingston_hellinger_circuit_only.joblib` |
| `ibm_kingston` | `hellinger` | `mixed_submit` | XGBoost | 15 | 0.879 | 0.0417 | `models/ibm_kingston_hellinger_mixed_submit.joblib` |
| `ibm_kingston` | `tvd` | `circuit_only` | SVR | 7 | 0.866 | 0.0434 | `models/ibm_kingston_tvd_circuit_only.joblib` |
| `ibm_kingston` | `tvd` | `mixed_submit` | XGBoost | 14 | 0.881 | 0.0407 | `models/ibm_kingston_tvd_mixed_submit.joblib` |
| `ibm_kingston` | `success` | `circuit_only` | SVR | 10 | 0.826 | 0.0507 | `models/ibm_kingston_success_circuit_only.joblib` |
| `ibm_kingston` | `success` | `mixed_submit` | SVR | 17 | 0.795 | 0.0526 | `models/ibm_kingston_success_mixed_submit.joblib` |
| `ibm_kingston` | `success_adj` | `circuit_only` | SVR | 6 | 0.853 | 0.0597 | `models/ibm_kingston_success_adj_circuit_only.joblib` |
| `ibm_kingston` | `success_adj` | `mixed_submit` | XGBoost | 13 | 0.836 | 0.0642 | `models/ibm_kingston_success_adj_mixed_submit.joblib` |
| `provider_ibm` | `dsr` | `circuit_chip` | LightGBM | 12 | 0.453 | 0.1048 | `models/provider_ibm_dsr_circuit_chip.joblib` |
| `provider_ibm` | `dsr` | `circuit_only` | RF | 10 | 0.391 | 0.1113 | `models/provider_ibm_dsr_circuit_only.joblib` |
| `provider_ibm` | `dsr` | `mixed_submit` | LightGBM | 17 | 0.621 | 0.0871 | `models/provider_ibm_dsr_mixed_submit.joblib` |
| `provider_ibm` | `hellinger` | `circuit_chip` | LightGBM | 10 | 0.794 | 0.0582 | `models/provider_ibm_hellinger_circuit_chip.joblib` |
| `provider_ibm` | `hellinger` | `circuit_only` | LightGBM | 8 | 0.755 | 0.0657 | `models/provider_ibm_hellinger_circuit_only.joblib` |
| `provider_ibm` | `hellinger` | `mixed_submit` | LightGBM | 15 | 0.885 | 0.0468 | `models/provider_ibm_hellinger_mixed_submit.joblib` |
| `provider_ibm` | `tvd` | `circuit_chip` | LightGBM | 10 | 0.793 | 0.0571 | `models/provider_ibm_tvd_circuit_chip.joblib` |
| `provider_ibm` | `tvd` | `circuit_only` | LightGBM | 8 | 0.759 | 0.0630 | `models/provider_ibm_tvd_circuit_only.joblib` |
| `provider_ibm` | `tvd` | `mixed_submit` | LightGBM | 15 | 0.888 | 0.0451 | `models/provider_ibm_tvd_mixed_submit.joblib` |
| `provider_ibm` | `success` | `circuit_chip` | LightGBM | 12 | 0.736 | 0.0647 | `models/provider_ibm_success_circuit_chip.joblib` |
| `provider_ibm` | `success` | `circuit_only` | LightGBM | 10 | 0.703 | 0.0699 | `models/provider_ibm_success_circuit_only.joblib` |
| `provider_ibm` | `success` | `mixed_submit` | LightGBM | 17 | 0.808 | 0.0559 | `models/provider_ibm_success_mixed_submit.joblib` |
| `provider_ibm` | `success_adj` | `circuit_chip` | RF | 9 | 0.765 | 0.0751 | `models/provider_ibm_success_adj_circuit_chip.joblib` |
| `provider_ibm` | `success_adj` | `circuit_only` | RF | 7 | 0.737 | 0.0814 | `models/provider_ibm_success_adj_circuit_only.joblib` |
| `provider_ibm` | `success_adj` | `mixed_submit` | SVR | 14 | 0.823 | 0.0651 | `models/provider_ibm_success_adj_mixed_submit.joblib` |
| `pooled` | `dsr` | `circuit_chip` | XGBoost | 14 | 0.445 | 0.1100 | `models/pooled_dsr_circuit_chip.joblib` |
| `pooled` | `dsr` | `circuit_only` | LightGBM | 10 | 0.360 | 0.1201 | `models/pooled_dsr_circuit_only.joblib` |
| `pooled` | `dsr` | `mixed_submit` | LightGBM | 17 | 0.595 | 0.0945 | `models/pooled_dsr_mixed_submit.joblib` |
| `pooled` | `hellinger` | `circuit_chip` | XGBoost | 14 | 0.782 | 0.0608 | `models/pooled_hellinger_circuit_chip.joblib` |
| `pooled` | `hellinger` | `circuit_only` | LightGBM | 10 | 0.729 | 0.0709 | `models/pooled_hellinger_circuit_only.joblib` |
| `pooled` | `hellinger` | `mixed_submit` | XGBoost | 17 | 0.851 | 0.0515 | `models/pooled_hellinger_mixed_submit.joblib` |
| `pooled` | `tvd` | `circuit_chip` | XGBoost | 11 | 0.786 | 0.0595 | `models/pooled_tvd_circuit_chip.joblib` |
| `pooled` | `tvd` | `circuit_only` | LightGBM | 7 | 0.729 | 0.0707 | `models/pooled_tvd_circuit_only.joblib` |
| `pooled` | `tvd` | `mixed_submit` | LightGBM | 14 | 0.850 | 0.0517 | `models/pooled_tvd_mixed_submit.joblib` |
| `pooled` | `success` | `circuit_chip` | XGBoost | 14 | 0.734 | 0.0661 | `models/pooled_success_circuit_chip.joblib` |
| `pooled` | `success` | `circuit_only` | XGBoost | 10 | 0.650 | 0.0762 | `models/pooled_success_circuit_only.joblib` |
| `pooled` | `success` | `mixed_submit` | LightGBM | 17 | 0.782 | 0.0606 | `models/pooled_success_mixed_submit.joblib` |
| `pooled` | `success_adj` | `circuit_chip` | SVR | 11 | 0.756 | 0.0775 | `models/pooled_success_adj_circuit_chip.joblib` |
| `pooled` | `success_adj` | `circuit_only` | XGBoost | 7 | 0.696 | 0.0878 | `models/pooled_success_adj_circuit_only.joblib` |
| `pooled` | `success_adj` | `mixed_submit` | XGBoost | 14 | 0.785 | 0.0716 | `models/pooled_success_adj_mixed_submit.joblib` |

