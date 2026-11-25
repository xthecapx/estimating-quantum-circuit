# QAQS quality-estimation report

Dataset `2fdcc81e9ec2` · chips: ibm_fez, ibm_kingston · providers: ibm.

| Campaign role | Jobs | Use |
|---|---:|---|
| train | 2409 | everything in this report |
| validation | 252 | prospective validation only; never trained on |
| exploratory | 20 | one-off studies; never trained on |

Scopes: `ibm_fez`, `ibm_kingston`, `pooled`. Model version: **v2**.

## Verdicts

| Scope | `dsr` | `hellinger` | `success` | `success_adj` | `tvd` |
|---|---|---|---|---|---|
| `ibm_fez` | FAIL (0.37) | INCONCLUSIVE (0.75) | FAIL (0.69) | INCONCLUSIVE (0.69) | INCONCLUSIVE (0.76) |
| `ibm_kingston` | FAIL (0.48) | PASS (0.86) | INCONCLUSIVE (0.82) | INCONCLUSIVE (0.85) | PASS (0.87) |
| `pooled` | FAIL (0.37) | FAIL (0.74) | FAIL (0.68) | INCONCLUSIVE (0.74) | INCONCLUSIVE (0.76) |

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

### `ibm_fez` · 1236 jobs, 189 configurations

| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |
|---|---:|:---:|---:|---:|---:|---:|---:|
| Differential Success Rate (`dsr`) | 0.368 ± 0.009 [0.22, 0.50] | FAIL | 0.1230 | 0.550 | 0.585 [0.36, 0.74] | 0.373 | -0.001 [-0.08, 0.08] |
| Hellinger Fidelity (`hellinger`) | 0.750 ± 0.008 [0.68, 0.81] | INCONCLUSIVE | 0.0690 | 0.721 | 0.918 [0.88, 0.94] | 0.743 | -0.003 [-0.04, 0.03] |
| Success Rate (`success`) | 0.688 ± 0.021 [0.57, 0.78] | FAIL | 0.0738 | 0.763 | 0.842 [0.74, 0.92] | 0.700 | +0.007 [-0.04, 0.06] |
| Chance-Corrected Success (`success_adj`) | 0.690 ± 0.008 [0.53, 0.80] | INCONCLUSIVE | 0.0869 | 0.810 | 0.819 [0.67, 0.92] | 0.697 | +0.003 [-0.04, 0.04] |
| Total Variation Distance (`tvd`) | 0.757 ± 0.008 [0.69, 0.82] | INCONCLUSIVE | 0.0683 | 0.732 | 0.923 [0.88, 0.95] | 0.755 | +0.003 [-0.03, 0.04] |

### `ibm_kingston` · 1173 jobs, 189 configurations

| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |
|---|---:|:---:|---:|---:|---:|---:|---:|
| Differential Success Rate (`dsr`) | 0.480 ± 0.019 [0.28, 0.63] | FAIL | 0.0917 | 0.771 | 0.570 [0.32, 0.76] | 0.193 | +0.231 [0.09, 0.38] |
| Hellinger Fidelity (`hellinger`) | 0.860 ± 0.011 [0.80, 0.91] | PASS | 0.0465 | 0.912 | 0.916 [0.87, 0.95] | 0.800 | +0.033 [-0.00, 0.07] |
| Success Rate (`success`) | 0.818 ± 0.025 [0.73, 0.89] | INCONCLUSIVE | 0.0523 | 0.918 | 0.867 [0.77, 0.93] | 0.744 | +0.048 [0.00, 0.10] |
| Chance-Corrected Success (`success_adj`) | 0.851 ± 0.001 [0.72, 0.93] | INCONCLUSIVE | 0.0608 | 0.953 | 0.857 [0.70, 0.95] | 0.774 | +0.091 [0.03, 0.17] |
| Total Variation Distance (`tvd`) | 0.874 ± 0.006 [0.82, 0.92] | PASS | 0.0431 | 0.911 | 0.932 [0.89, 0.96] | 0.800 | +0.050 [0.01, 0.10] |

### `pooled` · 2409 jobs, 189 configurations

| Target | R² ± sd [95% CI] | H1 | MAE | Ceiling | Config-mean R² | Size baseline R² | Gain over size [95% CI] |
|---|---:|:---:|---:|---:|---:|---:|---:|
| Differential Success Rate (`dsr`) | 0.372 ± 0.006 [0.22, 0.51] | FAIL | 0.1118 | 0.634 | 0.524 [0.31, 0.69] | 0.274 | +0.085 [0.01, 0.16] |
| Hellinger Fidelity (`hellinger`) | 0.738 ± 0.013 [0.67, 0.80] | FAIL | 0.0677 | 0.798 | 0.866 [0.81, 0.90] | 0.725 | +0.005 [-0.03, 0.04] |
| Success Rate (`success`) | 0.684 ± 0.007 [0.58, 0.77] | FAIL | 0.0714 | 0.826 | 0.800 [0.68, 0.87] | 0.683 | -0.009 [-0.04, 0.03] |
| Chance-Corrected Success (`success_adj`) | 0.743 ± 0.007 [0.58, 0.84] | INCONCLUSIVE | 0.0806 | 0.879 | 0.811 [0.66, 0.90] | 0.718 | +0.037 [-0.01, 0.10] |
| Total Variation Distance (`tvd`) | 0.758 ± 0.007 [0.69, 0.81] | INCONCLUSIVE | 0.0637 | 0.804 | 0.880 [0.83, 0.91] | 0.730 | +0.016 [-0.02, 0.05] |

### What each group of circuits contributes

R² of the same out-of-fold predictions on subsets. `all jobs` includes the composite anchor and is shown only to expose how much it inflates the score.

| Scope | Target | Headline | Core 6 | Random volumetric | Composite anchor | All jobs |
|---|---|---:|---:|---:|---:|---:|
| `ibm_fez` | `dsr` | 0.368 | 0.366 | 0.260 | -80.092 | 0.578 |
| `ibm_fez` | `hellinger` | 0.750 | 0.730 | 0.869 | 0.455 | 0.781 |
| `ibm_fez` | `success` | 0.688 | 0.653 | 0.896 | 0.000 | 0.777 |
| `ibm_fez` | `success_adj` | 0.690 | 0.498 | 0.889 | -3.037 | 0.690 |
| `ibm_fez` | `tvd` | 0.757 | 0.739 | 0.864 | 0.307 | 0.777 |
| `ibm_kingston` | `dsr` | 0.480 | 0.473 | 0.189 | -547.535 | 0.769 |
| `ibm_kingston` | `hellinger` | 0.860 | 0.863 | 0.813 | 0.501 | 0.884 |
| `ibm_kingston` | `success` | 0.818 | 0.820 | 0.779 | 0.448 | 0.905 |
| `ibm_kingston` | `success_adj` | 0.851 | 0.668 | 0.740 | -1.383 | 0.851 |
| `ibm_kingston` | `tvd` | 0.874 | 0.881 | 0.813 | 0.677 | 0.904 |
| `pooled` | `dsr` | 0.372 | 0.373 | 0.041 | -21.607 | 0.658 |
| `pooled` | `hellinger` | 0.738 | 0.728 | 0.771 | 0.350 | 0.783 |
| `pooled` | `success` | 0.684 | 0.663 | 0.784 | -0.260 | 0.799 |
| `pooled` | `success_adj` | 0.743 | 0.523 | 0.798 | -2.568 | 0.743 |
| `pooled` | `tvd` | 0.758 | 0.747 | 0.816 | 0.342 | 0.793 |

### Per algorithm (`success`)

R² inside one algorithm is a harder test: the spread to explain is only that algorithm's own.

| Scope | Algorithm | Configs | Observed mean ± sd | R² [95% CI] | MAE | Ceiling |
|---|---|---:|---:|---:|---:|---:|
| `ibm_fez` | BERNSTEIN-VAZIRANI | 39 | 0.78 ± 0.21 | 0.750 [0.58, 0.88] | 0.0555 | 0.749 |
| `ibm_fez` | GHZ | 15 | 0.84 ± 0.09 | 0.383 [-0.56, 0.89] | 0.0414 | 0.934 |
| `ibm_fez` | GROVER | 29 | 0.64 ± 0.28 | 0.724 [0.42, 0.90] | 0.0784 | 0.794 |
| `ibm_fez` | PHASE-ESTIMATION | 21 | 0.72 ± 0.22 | 0.672 [0.52, 0.81] | 0.0825 | 0.808 |
| `ibm_fez` | QFT | 27 | 0.75 ± 0.21 | 0.506 [-0.69, 0.86] | 0.0867 | 0.876 |
| `ibm_fez` | RANDOM-VOLUMETRIC | 15 | 0.62 ± 0.26 | 0.896 [0.79, 0.94] | 0.0633 | 0.923 |
| `ibm_fez` | SHOR | 13 | 0.15 ± 0.10 | 0.000 [-1.24, 0.62] | 0.0739 | 0.900 |
| `ibm_fez` | VTP | 30 | 0.74 ± 0.20 | 0.346 [0.11, 0.54] | 0.0989 | 0.242 |
| `ibm_kingston` | BERNSTEIN-VAZIRANI | 39 | 0.76 ± 0.20 | 0.776 [0.57, 0.91] | 0.0524 | 0.850 |
| `ibm_kingston` | GHZ | 15 | 0.85 ± 0.08 | 0.845 [0.70, 0.90] | 0.0277 | 0.911 |
| `ibm_kingston` | GROVER | 29 | 0.67 ± 0.28 | 0.899 [0.68, 0.98] | 0.0444 | 0.969 |
| `ibm_kingston` | PHASE-ESTIMATION | 21 | 0.79 ± 0.15 | 0.768 [0.63, 0.87] | 0.0512 | 0.938 |
| `ibm_kingston` | QFT | 27 | 0.82 ± 0.15 | 0.618 [-0.48, 0.81] | 0.0698 | 0.923 |
| `ibm_kingston` | RANDOM-VOLUMETRIC | 15 | 0.68 ± 0.23 | 0.779 [0.55, 0.89] | 0.0729 | 0.903 |
| `ibm_kingston` | SHOR | 13 | 0.14 ± 0.10 | 0.448 [-0.48, 0.77] | 0.0525 | 0.843 |
| `ibm_kingston` | VTP | 30 | 0.83 ± 0.09 | 0.548 [0.28, 0.70] | 0.0467 | 0.650 |
| `pooled` | BERNSTEIN-VAZIRANI | 39 | 0.77 ± 0.20 | 0.725 [0.56, 0.85] | 0.0577 | 0.795 |
| `pooled` | GHZ | 15 | 0.85 ± 0.09 | 0.621 [0.16, 0.87] | 0.0358 | 0.924 |
| `pooled` | GROVER | 29 | 0.65 ± 0.28 | 0.749 [0.43, 0.91] | 0.0729 | 0.875 |
| `pooled` | PHASE-ESTIMATION | 21 | 0.75 ± 0.19 | 0.651 [0.50, 0.76] | 0.0739 | 0.852 |
| `pooled` | QFT | 27 | 0.78 ± 0.18 | 0.472 [-0.73, 0.76] | 0.0918 | 0.896 |
| `pooled` | RANDOM-VOLUMETRIC | 15 | 0.65 ± 0.25 | 0.784 [0.57, 0.87] | 0.0854 | 0.916 |
| `pooled` | SHOR | 13 | 0.15 ± 0.10 | -0.260 [-1.71, 0.39] | 0.0833 | 0.867 |
| `pooled` | VTP | 30 | 0.79 ± 0.16 | 0.297 [0.07, 0.48] | 0.0791 | 0.365 |

### Targets with a point mass at the floor

Two-stage model (is the job above the floor, then how far) on the same footprint and folds.

| Scope | Target | Jobs at floor | Procedure R² | Two-stage R² | Procedure MAE | Two-stage MAE |
|---|---|---:|---:|---:|---:|---:|
| `ibm_fez` | `dsr` | 5.4% | 0.368 | 0.369 | 0.1230 | 0.1210 |
| `ibm_fez` | `success_adj` | 6.7% | 0.690 | 0.713 | 0.0869 | 0.0863 |
| `ibm_kingston` | `success_adj` | 6.2% | 0.851 | 0.864 | 0.0608 | 0.0582 |
| `pooled` | `success_adj` | 6.5% | 0.743 | 0.744 | 0.0806 | 0.0825 |

## H2 · Generalization to unseen configurations (`success`)

The held-out circuits are larger than any trained one, or from an algorithm absent from training. Footprint chosen on each protocol's own training set. `M2 prior alone` is the analytical estimate (uses submit-time calibration) with nothing learned; `M2 prior + residual` adds a footprint model of its error. Read the pair together: the gap is what the footprint adds.

| Scope | Protocol | Task | nTrain / nTest | R² [95% CI] | MAE |
|---|---|---|---:|---:|---:|
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 232 / 72 | -0.288 [-1.71, 0.16] | 0.2070 |
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior alone | 0 / 72 | -0.131 [-1.82, 0.38] | 0.1967 |
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 232 / 72 | 0.528 [0.05, 0.72] | 0.1215 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 352 / 110 | -1.010 [-2.14, -0.44] | 0.2770 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior alone | 0 / 110 | 0.241 [-0.30, 0.58] | 0.1664 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 352 / 110 | 0.590 [0.28, 0.79] | 0.0927 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 214 / 72 | -0.171 [-0.53, -0.03] | 0.1122 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior alone | 0 / 36 | -0.891 [-1.80, -0.72] | 0.1918 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 214 / 72 | -0.156 [-0.61, 0.17] | 0.1002 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 882 / 170 | 0.353 [-0.92, 0.70] | 0.1239 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 918 / 134 | 0.423 [0.13, 0.60] | 0.1201 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 850 / 202 | 0.545 [0.23, 0.71] | 0.1123 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 792 / 260 | -0.510 [-1.49, -0.14] | 0.2213 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 864 / 188 | 0.187 [-0.01, 0.38] | 0.1194 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 954 / 98 | -2.585 [-7.27, -0.74] | 0.1454 |
| `ibm_fez` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 1052 / 86 | -6.965 [-25.73, -2.26] | 0.2254 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 216 / 72 | -0.182 [-1.99, 0.39] | 0.1330 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior alone | 0 / 72 | 0.340 [-0.81, 0.66] | 0.1034 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 216 / 72 | 0.737 [0.28, 0.88] | 0.0597 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 306 / 102 | -1.629 [-3.24, -0.96] | 0.3242 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior alone | 0 / 102 | 0.904 [0.79, 0.95] | 0.0596 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 306 / 102 | 0.945 [0.87, 0.98] | 0.0387 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 198 / 72 | 0.376 [-0.36, 0.49] | 0.0476 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior alone | 0 / 36 | -2.614 [-9.18, -1.75] | 0.0767 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 198 / 72 | 0.459 [-0.03, 0.55] | 0.0429 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 804 / 162 | 0.399 [-1.09, 0.69] | 0.0909 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 840 / 126 | 0.216 [-0.35, 0.49] | 0.1011 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 792 / 174 | -0.227 [-0.72, 0.11] | 0.1903 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 732 / 234 | 0.181 [-0.04, 0.28] | 0.1474 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 786 / 180 | 0.429 [0.13, 0.62] | 0.0597 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 876 / 90 | -2.491 [-6.23, -1.09] | 0.1389 |
| `ibm_kingston` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 966 / 117 | -11.289 [-33.12, -5.54] | 0.2988 |
| `pooled` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 448 / 144 | 0.001 [-0.98, 0.42] | 0.1550 |
| `pooled` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior alone | 0 / 144 | 0.137 [-0.82, 0.50] | 0.1501 |
| `pooled` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 448 / 144 | 0.638 [0.28, 0.80] | 0.0904 |
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 658 / 212 | -0.788 [-1.86, -0.30] | 0.2549 |
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior alone | 0 / 212 | 0.556 [0.22, 0.75] | 0.1150 |
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 658 / 212 | 0.743 [0.54, 0.87] | 0.0744 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 412 / 144 | 0.042 [-0.15, 0.13] | 0.0875 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior alone | 0 / 72 | -0.609 [-1.14, -0.50] | 0.1342 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 412 / 144 | 0.055 [-0.20, 0.31] | 0.0746 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 1686 / 332 | 0.153 [-1.61, 0.55] | 0.1429 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 1758 / 260 | 0.551 [0.35, 0.72] | 0.0830 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 1642 / 376 | -0.409 [-0.88, -0.10] | 0.2214 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 1524 / 494 | -0.780 [-1.98, -0.35] | 0.2345 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 1650 / 368 | 0.243 [0.05, 0.42] | 0.0784 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 1830 / 188 | -3.906 [-9.43, -1.79] | 0.1741 |
| `pooled` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 2018 / 203 | -5.442 [-15.45, -2.28] | 0.2095 |

## H3 · Hardware context and transfer (`success`)

Two kinds of calibration input. **Device** (`cal.*`): one value per calibration snapshot, blind to the circuit. **Layout** (`c.*`): calibration of the qubits the circuit was mapped to, so it also carries circuit size.

Judge calibration regimes on the **calibration-cycle** column: there the test windows are new calibration cycles. In the unseen-circuit column train and test share windows, so any input that identifies the window helps; the `collection-window id` row is the control for that.

| Scope | Regime | Features | Unseen-circuit R² ± sd | Calibration-cycle R² [95% CI] | Calibration-cycle MAE |
|---|---|---:|---:|---:|---:|
| `ibm_fez` | Circuit footprint only (a.* + b.*) | 4 | 0.688 ± 0.021 | 0.649 [0.53, 0.76] | 0.0855 |
| `ibm_fez` | Size baseline (2Q gates, depth, width, measurements) | 4 | 0.700 ± 0.007 | 0.654 [0.54, 0.77] | 0.0864 |
| `ibm_fez` | Device calibration only (cal.*, one value per snapshot) | 7 | 0.037 ± 0.005 | -0.183 [-0.34, -0.03] | 0.2085 |
| `ibm_fez` | Layout calibration only (c.*, qubits the circuit uses) | 7 | 0.613 ± 0.002 | 0.362 [0.20, 0.47] | 0.1670 |
| `ibm_fez` | Footprint + device calibration (cal.*) | 11 | 0.734 ± 0.012 | 0.671 [0.57, 0.77] | 0.0855 |
| `ibm_fez` | Footprint + layout calibration (c.*) | 11 | 0.806 ± 0.004 | 0.672 [0.58, 0.77] | 0.0953 |
| `ibm_fez` | Footprint + collection-window id (control) | 5 | 0.721 ± 0.008 | — | — |
| `ibm_kingston` | Circuit footprint only (a.* + b.*) | 5 | 0.818 ± 0.025 | 0.909 [0.86, 0.94] | 0.0414 |
| `ibm_kingston` | Size baseline (2Q gates, depth, width, measurements) | 4 | 0.744 ± 0.010 | 0.908 [0.86, 0.94] | 0.0437 |
| `ibm_kingston` | Device calibration only (cal.*, one value per snapshot) | 7 | -0.137 ± 0.002 | -0.797 [-1.49, -0.45] | 0.2088 |
| `ibm_kingston` | Layout calibration only (c.*, qubits the circuit uses) | 7 | 0.585 ± 0.019 | 0.122 [-0.15, 0.29] | 0.1325 |
| `ibm_kingston` | Footprint + device calibration (cal.*) | 12 | 0.811 ± 0.008 | 0.908 [0.86, 0.94] | 0.0415 |
| `ibm_kingston` | Footprint + layout calibration (c.*) | 12 | 0.795 ± 0.012 | 0.877 [0.82, 0.91] | 0.0468 |
| `ibm_kingston` | Footprint + collection-window id (control) | 6 | 0.811 ± 0.013 | — | — |
| `pooled` | Circuit footprint only (a.* + b.*) | 5 | 0.684 ± 0.007 | — | — |
| `pooled` | Size baseline (2Q gates, depth, width, measurements) | 4 | 0.683 ± 0.010 | — | — |
| `pooled` | Device calibration only (cal.*, one value per snapshot) | 7 | -0.023 ± 0.004 | — | — |
| `pooled` | Layout calibration only (c.*, qubits the circuit uses) | 7 | 0.591 ± 0.010 | — | — |
| `pooled` | Footprint + device calibration (cal.*) | 12 | 0.765 ± 0.010 | — | — |
| `pooled` | Footprint + layout calibration (c.*) | 12 | 0.791 ± 0.012 | — | — |
| `pooled` | Footprint + collection-window id (control) | 6 | 0.761 ± 0.006 | — | — |
| `pooled` | Footprint + chip id | 6 | 0.738 ± 0.006 | — | — |

- `ibm_fez` calibration-cycle split: 787 training jobs (16 calibration snapshots), 410 test jobs (6 snapshots); 171 of 176 test configurations also trained; strictly later than training: yes.
- `ibm_kingston` calibration-cycle split: 782 training jobs (3 calibration snapshots), 352 test jobs (3 snapshots); 176 of 176 test configurations also trained; strictly later than training: yes.

### Cross-chip transfer (zero-shot)

Model trained on the source chip with the footprint chosen there, scored on every job of the target chip. Diagonal cells are within-chip grouped CV.

| Source | Target | Regime | Same provider | R² [95% CI] | MAE |
|---|---|---|:---:|---:|---:|
| `ibm_fez` | `ibm_fez` | Circuit Footprint Only | yes | 0.691 [0.57, 0.79] | 0.0754 |
| `ibm_fez` | `ibm_fez` | Device Calibration Only | yes | 0.053 [-0.04, 0.12] | 0.1763 |
| `ibm_fez` | `ibm_fez` | Mixed (Footprint + Layout Calibration) | yes | 0.807 [0.70, 0.88] | 0.0584 |
| `ibm_fez` | `ibm_kingston` | Circuit Footprint Only | yes | 0.667 [0.54, 0.75] | 0.0812 |
| `ibm_fez` | `ibm_kingston` | Device Calibration Only | yes | -0.800 [-1.43, -0.49] | 0.2272 |
| `ibm_fez` | `ibm_kingston` | Mixed (Footprint + Layout Calibration) | yes | 0.435 [0.20, 0.62] | 0.0894 |
| `ibm_kingston` | `ibm_fez` | Circuit Footprint Only | yes | 0.614 [0.52, 0.70] | 0.0827 |
| `ibm_kingston` | `ibm_fez` | Device Calibration Only | yes | -0.657 [-1.01, -0.44] | 0.2250 |
| `ibm_kingston` | `ibm_fez` | Mixed (Footprint + Layout Calibration) | yes | 0.660 [0.58, 0.74] | 0.0797 |
| `ibm_kingston` | `ibm_kingston` | Circuit Footprint Only | yes | 0.814 [0.71, 0.88] | 0.0524 |
| `ibm_kingston` | `ibm_kingston` | Device Calibration Only | yes | -0.137 [-0.33, -0.05] | 0.1672 |
| `ibm_kingston` | `ibm_kingston` | Mixed (Footprint + Layout Calibration) | yes | 0.811 [0.71, 0.89] | 0.0500 |

### Cross-provider transfer (leave one provider out)

WAITING FOR DATA: the export holds ibm only.

## H4 · Paradigm circuits vs random-volumetric circuits (`success`)

Forward rows test on paradigm circuits, reverse rows on random-volumetric (RV) circuits; every test configuration is predicted once by a model that never saw it. `size-matched` trains on as many paradigm rows as there are RV rows.

| Scope | Regime | nTrain | nTest | R² [95% CI] | MAE |
|---|---|---:|---:|---:|---:|
| `ibm_fez` | Random Volumetric Only (RV) | 98 | 1052 | 0.343 [0.19, 0.47] | 0.1353 |
| `ibm_fez` | Paradigm Algorithms Only (6 Core) | 841 | 1052 | 0.669 [0.56, 0.77] | 0.0771 |
| `ibm_fez` | Combined (RV + 6 Core) | 939 | 1052 | 0.679 [0.57, 0.78] | 0.0757 |
| `ibm_fez` | Paradigm Only, size-matched to RV | 98 | 1052 | 0.331 [0.26, 0.49] | 0.1196 |
| `ibm_fez` | Reverse · paradigm-trained, tested on RV | 841 | 98 | 0.841 [0.60, 0.92] | 0.0766 |
| `ibm_fez` | Reverse · RV-trained, tested on unseen RV | 78 | 98 | 0.812 [0.65, 0.89] | 0.0855 |
| `ibm_kingston` | Random Volumetric Only (RV) | 90 | 966 | 0.542 [0.37, 0.66] | 0.0907 |
| `ibm_kingston` | Paradigm Algorithms Only (6 Core) | 772 | 966 | 0.785 [0.65, 0.86] | 0.0551 |
| `ibm_kingston` | Combined (RV + 6 Core) | 862 | 966 | 0.802 [0.67, 0.88] | 0.0531 |
| `ibm_kingston` | Paradigm Only, size-matched to RV | 90 | 966 | 0.416 [0.28, 0.61] | 0.0990 |
| `ibm_kingston` | Reverse · paradigm-trained, tested on RV | 772 | 90 | 0.829 [0.68, 0.89] | 0.0785 |
| `ibm_kingston` | Reverse · RV-trained, tested on unseen RV | 72 | 90 | 0.753 [0.49, 0.84] | 0.0912 |
| `pooled` | Random Volumetric Only (RV) | 188 | 2018 | 0.424 [0.27, 0.56] | 0.1024 |
| `pooled` | Paradigm Algorithms Only (6 Core) | 1614 | 2018 | 0.691 [0.57, 0.78] | 0.0704 |
| `pooled` | Combined (RV + 6 Core) | 1802 | 2018 | 0.686 [0.56, 0.78] | 0.0706 |
| `pooled` | Paradigm Only, size-matched to RV | 188 | 2018 | 0.367 [0.20, 0.48] | 0.1077 |
| `pooled` | Reverse · paradigm-trained, tested on RV | 1614 | 188 | 0.722 [0.38, 0.83] | 0.1005 |
| `pooled` | Reverse · RV-trained, tested on unseen RV | 150 | 188 | 0.817 [0.68, 0.88] | 0.0778 |

Two intervals that overlap do not show two regimes are equal, and two that do not overlap are not the test either. The comparison is the paired difference on the same test jobs:

| Scope | Question | R²(a) − R²(b) [95% CI] | Verdict |
|---|---|---:|---|
| `ibm_fez` | Same training size: do paradigm circuits predict paradigm circuits better than RV circuits do? (`paradigm_matched` − `random_only`) | +0.045 [-0.07, 0.18] | no difference shown |
| `ibm_fez` | Do RV circuits add anything once paradigm circuits are in training? (`combined` − `paradigm_only`) | +0.010 [0.00, 0.02] | first is better |
| `ibm_fez` | Do paradigm circuits add anything once RV circuits are in training? (`combined` − `random_only`) | +0.336 [0.23, 0.46] | first is better |
| `ibm_fez` | Reverse: do RV circuits predict RV circuits better than paradigm circuits do? (`reverse_random_cv` − `reverse_paradigm`) | -0.029 [-0.13, 0.11] | no difference shown |
| `ibm_kingston` | Same training size: do paradigm circuits predict paradigm circuits better than RV circuits do? (`paradigm_matched` − `random_only`) | -0.073 [-0.19, 0.04] | no difference shown |
| `ibm_kingston` | Do RV circuits add anything once paradigm circuits are in training? (`combined` − `paradigm_only`) | +0.018 [-0.00, 0.04] | no difference shown |
| `ibm_kingston` | Do paradigm circuits add anything once RV circuits are in training? (`combined` − `random_only`) | +0.260 [0.17, 0.39] | first is better |
| `ibm_kingston` | Reverse: do RV circuits predict RV circuits better than paradigm circuits do? (`reverse_random_cv` − `reverse_paradigm`) | -0.075 [-0.21, 0.00] | no difference shown |
| `pooled` | Same training size: do paradigm circuits predict paradigm circuits better than RV circuits do? (`paradigm_matched` − `random_only`) | -0.068 [-0.21, 0.07] | no difference shown |
| `pooled` | Do RV circuits add anything once paradigm circuits are in training? (`combined` − `paradigm_only`) | -0.006 [-0.02, 0.01] | no difference shown |
| `pooled` | Do paradigm circuits add anything once RV circuits are in training? (`combined` − `random_only`) | +0.262 [0.17, 0.38] | first is better |
| `pooled` | Reverse: do RV circuits predict RV circuits better than paradigm circuits do? (`reverse_random_cv` − `reverse_paradigm`) | +0.095 [-0.00, 0.30] | no difference shown |

## The footprint

A feature belongs to the footprint only if the selection procedure picks it in at least 80% of the outer folds. Features chosen once on the full data but rarely inside folds are listed in `footprint.csv` with their selection frequency and are not part of the claim.

| Feature | Category | Stable in (scope × target) | Mean selection frequency |
|---|---|---:|---:|
| `b.ComplexityMetrics.standardized_metrics.circuit_volume` | ISA Compiled | 12 / 15 | 1.00 |
| `b.ComplexityMetrics.standardized_metrics.gate_density` | ISA Compiled | 9 / 15 | 0.90 |
| `a.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` | Logical Complexity | 5 / 15 | 0.83 |
| `b.ComplexityMetrics.entanglement_metrics.entangling_width` | ISA Compiled | 4 / 15 | 0.95 |
| `b.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` | ISA Compiled | 2 / 15 | 1.00 |
| `a.quantum_specific.magic` | Quantum Specific | 2 / 15 | 0.90 |
| `a.StructuralMetrics.difficulty` | Logical Structural | 1 / 15 | 0.87 |
| `b.StructuralMetrics.effort` | ISA Compiled | 1 / 15 | 0.80 |

Footprint size is chosen by the one-standard-error rule (smallest k within one standard error of the best k). The ablation R² in `footprint_ablation.csv` is a selection score, not accuracy.

| Scope | Target | k deployed | k across folds (min–median–max) | Stable features |
|---|---|---:|---:|---:|
| `ibm_fez` | `dsr` | 5 | 5–5–5 | 3 |
| `ibm_fez` | `hellinger` | 5 | 3–5–5 | 3 |
| `ibm_fez` | `success` | 5 | 3–5–6 | 1 |
| `ibm_fez` | `success_adj` | 5 | 3–5–6 | 2 |
| `ibm_fez` | `tvd` | 5 | 3–5–5 | 1 |
| `ibm_kingston` | `dsr` | 5 | 5–5–5 | 3 |
| `ibm_kingston` | `hellinger` | 5 | 5–5–7 | 3 |
| `ibm_kingston` | `success` | 5 | 4–5–6 | 4 |
| `ibm_kingston` | `success_adj` | 5 | 4–5–5 | 4 |
| `ibm_kingston` | `tvd` | 5 | 4–5–6 | 4 |
| `pooled` | `dsr` | 5 | 5–5–5 | 3 |
| `pooled` | `hellinger` | 5 | 5–5–5 | 2 |
| `pooled` | `success` | 8 | 5–5–6 | 1 |
| `pooled` | `success_adj` | 5 | 5–5–5 | 1 |
| `pooled` | `tvd` | 5 | 5–5–5 | 1 |

## Prospective validation (frozen v1 models)

Models frozen on 2026-11-16 and scored on a run collected afterwards, predictions committed first. These are the **v1** models in `report/frozen_v1`; the models saved by this report are **v2** and have no prospective score until a new pre-registered run. The pre-registered H1 rule applies to the `new` group of every model scope; all scopes are listed, because which source chip transfers best to an unseen chip is not known beforehand.

| Chip | QPU | Model scope | Group | Configs | R² [95% CI] | MAE |
|---|---|---|---|---:|---:|---:|
| `ibm_fez` | seen | `ibm_fez` | anchor | 20 | 0.936 [0.83, 0.98] | 0.0502 |
| `ibm_fez` | seen | `ibm_fez` | extrapolation | 9 | 0.805 [0.17, 0.93] | 0.0806 |
| `ibm_fez` | seen | `ibm_fez` | new | 13 | 0.940 [0.82, 0.99] | 0.0386 |
| `ibm_fez` | seen | `pooled` | anchor | 20 | 0.974 [0.95, 0.99] | 0.0359 |
| `ibm_fez` | seen | `pooled` | extrapolation | 9 | 0.577 [-0.63, 0.75] | 0.1188 |
| `ibm_fez` | seen | `pooled` | new | 13 | 0.959 [0.90, 0.98] | 0.0349 |
| `ibm_kingston` | seen | `ibm_kingston` | anchor | 20 | 0.967 [0.92, 0.98] | 0.0355 |
| `ibm_kingston` | seen | `ibm_kingston` | extrapolation | 9 | 0.964 [0.90, 0.98] | 0.0324 |
| `ibm_kingston` | seen | `ibm_kingston` | new | 13 | 0.933 [0.84, 0.98] | 0.0334 |
| `ibm_kingston` | seen | `pooled` | anchor | 20 | 0.917 [0.76, 0.98] | 0.0467 |
| `ibm_kingston` | seen | `pooled` | extrapolation | 9 | 0.302 [-2.13, 0.71] | 0.1389 |
| `ibm_kingston` | seen | `pooled` | new | 13 | 0.859 [0.56, 0.94] | 0.0591 |
| `ibm_marrakesh` | unseen | `ibm_fez` | anchor | 20 | 0.939 [0.86, 0.98] | 0.0537 |
| `ibm_marrakesh` | unseen | `ibm_fez` | extrapolation | 9 | 0.704 [-1.42, 0.91] | 0.0903 |
| `ibm_marrakesh` | unseen | `ibm_fez` | new | 13 | 0.934 [0.88, 0.97] | 0.0536 |
| `ibm_marrakesh` | unseen | `ibm_kingston` | anchor | 20 | 0.848 [0.71, 0.93] | 0.0888 |
| `ibm_marrakesh` | unseen | `ibm_kingston` | extrapolation | 9 | -0.142 [-10.10, 0.57] | 0.1907 |
| `ibm_marrakesh` | unseen | `ibm_kingston` | new | 13 | 0.687 [0.41, 0.85] | 0.1070 |
| `ibm_marrakesh` | unseen | `pooled` | anchor | 20 | 0.925 [0.86, 0.96] | 0.0649 |
| `ibm_marrakesh` | unseen | `pooled` | extrapolation | 9 | 0.494 [-3.55, 0.81] | 0.1154 |
| `ibm_marrakesh` | unseen | `pooled` | new | 13 | 0.869 [0.74, 0.94] | 0.0711 |

`new` holds 13 configurations and `extrapolation` 9 per chip, so their intervals are wide.

## Saved models (v2)

Fitted on every training-role job with the procedure scored above. Not prospectively validated.

| Scope | Target | Regime | Model | Features | Procedure R² | MAE | Artifact |
|---|---|---|---|---:|---:|---:|---|
| `ibm_fez` | `dsr` | `circuit_only` | XGBoost | 5 | 0.368 | 0.1230 | `models/ibm_fez_dsr_circuit_only.joblib` |
| `ibm_fez` | `dsr` | `mixed_submit` | LightGBM | 12 | 0.643 | 0.0935 | `models/ibm_fez_dsr_mixed_submit.joblib` |
| `ibm_fez` | `hellinger` | `circuit_only` | XGBoost | 5 | 0.750 | 0.0690 | `models/ibm_fez_hellinger_circuit_only.joblib` |
| `ibm_fez` | `hellinger` | `mixed_submit` | XGBoost | 12 | 0.889 | 0.0506 | `models/ibm_fez_hellinger_mixed_submit.joblib` |
| `ibm_fez` | `success` | `circuit_only` | XGBoost | 5 | 0.688 | 0.0738 | `models/ibm_fez_success_circuit_only.joblib` |
| `ibm_fez` | `success` | `mixed_submit` | XGBoost | 12 | 0.806 | 0.0590 | `models/ibm_fez_success_mixed_submit.joblib` |
| `ibm_fez` | `success_adj` | `circuit_only` | SVR | 5 | 0.690 | 0.0869 | `models/ibm_fez_success_adj_circuit_only.joblib` |
| `ibm_fez` | `success_adj` | `mixed_submit` | LightGBM | 12 | 0.810 | 0.0664 | `models/ibm_fez_success_adj_mixed_submit.joblib` |
| `ibm_fez` | `tvd` | `circuit_only` | XGBoost | 5 | 0.757 | 0.0683 | `models/ibm_fez_tvd_circuit_only.joblib` |
| `ibm_fez` | `tvd` | `mixed_submit` | Stacking (AutoML) | 12 | 0.891 | 0.0477 | `models/ibm_fez_tvd_mixed_submit.joblib` |
| `ibm_kingston` | `dsr` | `circuit_only` | LightGBM | 5 | 0.480 | 0.0917 | `models/ibm_kingston_dsr_circuit_only.joblib` |
| `ibm_kingston` | `dsr` | `mixed_submit` | RF | 12 | 0.522 | 0.0846 | `models/ibm_kingston_dsr_mixed_submit.joblib` |
| `ibm_kingston` | `hellinger` | `circuit_only` | SVR | 5 | 0.860 | 0.0465 | `models/ibm_kingston_hellinger_circuit_only.joblib` |
| `ibm_kingston` | `hellinger` | `mixed_submit` | RF | 12 | 0.873 | 0.0428 | `models/ibm_kingston_hellinger_mixed_submit.joblib` |
| `ibm_kingston` | `success` | `circuit_only` | SVR | 5 | 0.818 | 0.0523 | `models/ibm_kingston_success_circuit_only.joblib` |
| `ibm_kingston` | `success` | `mixed_submit` | LightGBM | 12 | 0.795 | 0.0529 | `models/ibm_kingston_success_mixed_submit.joblib` |
| `ibm_kingston` | `success_adj` | `circuit_only` | SVR | 5 | 0.851 | 0.0608 | `models/ibm_kingston_success_adj_circuit_only.joblib` |
| `ibm_kingston` | `success_adj` | `mixed_submit` | XGBoost | 12 | 0.836 | 0.0640 | `models/ibm_kingston_success_adj_mixed_submit.joblib` |
| `ibm_kingston` | `tvd` | `circuit_only` | SVR | 5 | 0.874 | 0.0431 | `models/ibm_kingston_tvd_circuit_only.joblib` |
| `ibm_kingston` | `tvd` | `mixed_submit` | LightGBM | 12 | 0.881 | 0.0410 | `models/ibm_kingston_tvd_mixed_submit.joblib` |
| `pooled` | `dsr` | `circuit_only` | SVR | 5 | 0.372 | 0.1118 | `models/pooled_dsr_circuit_only.joblib` |
| `pooled` | `dsr` | `mixed_submit` | Stacking (AutoML) | 12 | 0.621 | 0.0883 | `models/pooled_dsr_mixed_submit.joblib` |
| `pooled` | `hellinger` | `circuit_only` | RF | 5 | 0.738 | 0.0677 | `models/pooled_hellinger_circuit_only.joblib` |
| `pooled` | `hellinger` | `mixed_submit` | Stacking (AutoML) | 12 | 0.879 | 0.0475 | `models/pooled_hellinger_mixed_submit.joblib` |
| `pooled` | `success` | `circuit_only` | LightGBM | 8 | 0.684 | 0.0714 | `models/pooled_success_circuit_only.joblib` |
| `pooled` | `success` | `mixed_submit` | LightGBM | 15 | 0.791 | 0.0584 | `models/pooled_success_mixed_submit.joblib` |
| `pooled` | `success_adj` | `circuit_only` | KNN | 5 | 0.743 | 0.0806 | `models/pooled_success_adj_circuit_only.joblib` |
| `pooled` | `success_adj` | `mixed_submit` | RF | 12 | 0.809 | 0.0685 | `models/pooled_success_adj_mixed_submit.joblib` |
| `pooled` | `tvd` | `circuit_only` | RF | 5 | 0.758 | 0.0637 | `models/pooled_tvd_circuit_only.joblib` |
| `pooled` | `tvd` | `mixed_submit` | LightGBM | 12 | 0.882 | 0.0466 | `models/pooled_tvd_mixed_submit.joblib` |

