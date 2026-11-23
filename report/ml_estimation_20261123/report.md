# QAQS Quantum Circuit Quality Estimation Report

Scopes evaluated: ibm_fez, ibm_kingston, pooled

## Validation tests

| Test | Question | Method | Where reported |
|---|---|---|---|
| **Unseen-circuit validation** | Does QAQS predict circuits it has never seen? | Repeated grouped K-fold by circuit configuration (5 folds x 3 repeats, 193 configurations, folds shared across chips) | H1 tables below; H2; H4 |
| **Calibration-cycle validation** | Does QAQS predict a later calibration cycle? | Forward temporal holdout: train on earlier windows, test on the latest window (mostly the same circuits) | H3 section |
| **Prospective validation** | Does QAQS predict a run that did not exist at training time? | Frozen models scored on a new IBM run, predictions committed before results | Not yet run |

Unseen-circuit validation: every configuration is predicted once per repeat by a model that never saw it, on any chip. Footprint selection, calibration-feature selection, tuning and model choice happen inside each training fold.

**QAQS row** = score of that whole procedure (the honest H1 estimate). Per-model rows are shown for comparison; choosing the best of them afterwards is optimistic.

R² = mean over repeats ± sd between repeats. CI = mean of per-repeat 95% cluster-bootstrap intervals (resampling configurations). H1 PASS needs the CI above 0.80.

Calibration drift is *not* tested by unseen-circuit validation: every configuration also ran in the training windows. See calibration-cycle validation (H3) and prospective validation.

## Scope: `ibm_fez` (1256 jobs, 193 configurations) · unseen-circuit validation

| Target | QAQS circuit-only R² ± sd [95% CI] | MAE | Mixed (+calib) R² | Best single model (R²) | Deployed model | k* (fold range) | H1 |
|---|---:|---:|---:|---|---|---|:---:|
| Differential Success Rate (`dsr`) | 0.630 ± 0.010 [0.49, 0.74] | 0.1092 | 0.782 | LightGBM (0.634) | LightGBM | 6 (5–10) | FAIL |
| Hellinger Fidelity (`hellinger`) | 0.784 ± 0.005 [0.71, 0.85] | 0.0702 | 0.882 | XGBoost (0.791) | XGBoost | 7 (5–10) | INCONCLUSIVE |
| Total Variation Distance (`tvd`) | 0.794 ± 0.008 [0.72, 0.85] | 0.0683 | 0.895 | XGBoost (0.802) | XGBoost | 10 (5–10) | INCONCLUSIVE |
| Success Rate (`success`) | 0.781 ± 0.010 [0.68, 0.84] | 0.0726 | 0.850 | XGBoost (0.798) | XGBoost | 8 (4–10) | INCONCLUSIVE |

## Scope: `ibm_kingston` (1173 jobs, 189 configurations) · unseen-circuit validation

| Target | QAQS circuit-only R² ± sd [95% CI] | MAE | Mixed (+calib) R² | Best single model (R²) | Deployed model | k* (fold range) | H1 |
|---|---:|---:|---:|---|---|---|:---:|
| Differential Success Rate (`dsr`) | 0.761 ± 0.007 [0.62, 0.86] | 0.0858 | 0.770 | Stacking (AutoML) (0.794) | SVR | 6 (6–10) | INCONCLUSIVE |
| Hellinger Fidelity (`hellinger`) | 0.901 ± 0.003 [0.85, 0.94] | 0.0491 | 0.895 | SVR (0.895) | SVR | 8 (5–8) | PASS |
| Total Variation Distance (`tvd`) | 0.879 ± 0.024 [0.82, 0.92] | 0.0510 | 0.890 | XGBoost (0.886) | SVR | 7 (5–8) | PASS |
| Success Rate (`success`) | 0.914 ± 0.006 [0.86, 0.94] | 0.0516 | 0.877 | SVR (0.914) | SVR | 10 (5–10) | PASS |

## Scope: `pooled` (2429 jobs, 193 configurations) · unseen-circuit validation

| Target | QAQS circuit-only R² ± sd [95% CI] | MAE | Mixed (+calib) R² | Best single model (R²) | Deployed model | k* (fold range) | H1 |
|---|---:|---:|---:|---|---|---|:---:|
| Differential Success Rate (`dsr`) | 0.651 ± 0.003 [0.50, 0.76] | 0.1047 | 0.778 | LightGBM (0.670) | RF | 10 (5–10) | FAIL |
| Hellinger Fidelity (`hellinger`) | 0.796 ± 0.004 [0.72, 0.85] | 0.0690 | 0.883 | LightGBM (0.802) | XGBoost | 7 (5–10) | INCONCLUSIVE |
| Total Variation Distance (`tvd`) | 0.798 ± 0.006 [0.72, 0.86] | 0.0681 | 0.889 | LightGBM (0.803) | Stacking (AutoML) | 5 (5–10) | INCONCLUSIVE |
| Success Rate (`success`) | 0.810 ± 0.013 [0.72, 0.86] | 0.0703 | 0.861 | SVR (0.819) | LightGBM | 9 (5–10) | INCONCLUSIVE |

## Selected Best Pre-Runtime Predictors (Global Core Footprint)

| Feature | Category | Selected (Scopes×Targets) | Mean Rank | Mean |SHAP| | Mean Perm ΔR² |
|---|---|---:|---:|---:|---:|
| `b.ComplexityMetrics.standardized_metrics.circuit_volume` | ISA Compiled | 10 / 12 | 1.4 | 0.1222 | 0.7849 |
| `b.ComplexityMetrics.standardized_metrics.gate_density` | ISA Compiled | 10 / 12 | 2.6 | 0.0390 | 0.1193 |
| `a.quantum_specific.magic` | Quantum Specific | 8 / 12 | 5.8 | 0.0152 | 0.0214 |
| `b.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` | ISA Compiled | 7 / 12 | 3.9 | 0.0286 | 0.0366 |
| `a.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` | Logical Complexity | 7 / 12 | 4.9 | 0.0191 | 0.0385 |
| `b.ComplexityMetrics.entanglement_metrics.entangling_width` | ISA Compiled | 7 / 12 | 4.7 | 0.0155 | 0.0248 |
| `b.StructuralMetrics.effort` | ISA Compiled | 6 / 12 | 3.2 | 0.0260 | 0.0507 |
| `b.StructuralMetrics.vocabulary` | ISA Compiled | 6 / 12 | 4.8 | 0.0148 | 0.0246 |
| `b.BehavioralMetrics.measurement` | ISA Compiled | 5 / 12 | 5.0 | 0.0113 | 0.0204 |
| `a.BehavioralMetrics.parallelism` | Logical Behavioral | 3 / 12 | 6.7 | 0.0108 | 0.0155 |
| `a.StructuralMetrics.difficulty` | Logical Structural | 2 / 12 | 1.0 | 0.0910 | 0.2405 |
| `b.ComplexityMetrics.derived_metrics.square_ratio` | ISA Compiled | 2 / 12 | 4.5 | 0.0186 | 0.0427 |
| `a.quantum_specific.coherence` | Quantum Specific | 2 / 12 | 7.0 | 0.0184 | 0.0359 |
| `b.BehavioralMetrics.liveness` | ISA Compiled | 2 / 12 | 4.5 | 0.0148 | 0.0264 |
| `b.StructuralMetrics.difficulty` | ISA Compiled | 2 / 12 | 7.5 | 0.0104 | 0.0014 |

## Top-k Pre-Runtime Feature Selection Ablation

| Scope | Target | Selected k* (CV R²) | Full Candidates k (CV R²) |
|---|---|---|---:|
| `ibm_fez` | `dsr` | k=6 (0.638) | k=11 (0.633) |
| `ibm_fez` | `hellinger` | k=7 (0.790) | k=15 (0.800) |
| `ibm_fez` | `tvd` | k=10 (0.802) | k=16 (0.794) |
| `ibm_fez` | `success` | k=8 (0.780) | k=15 (0.791) |
| `ibm_kingston` | `dsr` | k=6 (0.773) | k=16 (0.754) |
| `ibm_kingston` | `hellinger` | k=8 (0.899) | k=12 (0.904) |
| `ibm_kingston` | `tvd` | k=7 (0.894) | k=14 (0.895) |
| `ibm_kingston` | `success` | k=10 (0.905) | k=13 (0.902) |
| `pooled` | `dsr` | k=10 (0.661) | k=16 (0.670) |
| `pooled` | `hellinger` | k=7 (0.793) | k=11 (0.794) |
| `pooled` | `tvd` | k=5 (0.795) | k=7 (0.795) |
| `pooled` | `success` | k=9 (0.803) | k=10 (0.803) |

## H2 · Generalization to unseen configurations (success rate)

Protocol-specific unseen-circuit tests (the held-out circuits are larger, or from another algorithm). Footprint chosen on each protocol's own training set. `M2 prior + residual` adds the analytical M2 estimate (uses submit-time calibration) as a decay prior and learns its residual from the footprint; it is calibration-aware, so it is reported separately from the circuit-only claim.

| Scope | Protocol | Task | nTrain / nTest | R² [95% CI] | MAE |
|---|---|---|---:|---:|---:|
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 232 / 72 | -0.288 [-1.71, 0.16] | 0.2070 |
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 232 / 72 | 0.528 [0.05, 0.72] | 0.1215 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 354 / 118 | -1.499 [-2.69, -0.86] | 0.3160 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 354 / 118 | 0.610 [0.32, 0.83] | 0.0868 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 224 / 72 | -0.212 [-0.57, -0.07] | 0.1134 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 224 / 72 | -0.091 [-0.55, 0.08] | 0.1253 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 902 / 170 | 0.228 [-1.43, 0.63] | 0.1490 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 938 / 134 | 0.295 [-0.05, 0.48] | 0.1408 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 870 / 202 | 0.544 [0.23, 0.71] | 0.1181 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 802 / 270 | -1.171 [-2.58, -0.61] | 0.2649 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 884 / 188 | -0.043 [-0.34, 0.24] | 0.1329 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 964 / 108 | -5.013 [-11.95, -2.01] | 0.1933 |
| `ibm_fez` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 1072 / 86 | -3.021 [-11.94, -0.87] | 0.1662 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 216 / 72 | -0.182 [-1.99, 0.39] | 0.1330 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 216 / 72 | 0.737 [0.28, 0.88] | 0.0597 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 306 / 102 | -1.629 [-3.24, -0.96] | 0.3242 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 306 / 102 | 0.945 [0.87, 0.98] | 0.0387 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 198 / 72 | 0.376 [-0.36, 0.49] | 0.0476 |
| `ibm_kingston` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 198 / 72 | 0.459 [-0.03, 0.55] | 0.0429 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 804 / 162 | 0.405 [-1.03, 0.69] | 0.0852 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 840 / 126 | 0.197 [-0.45, 0.51] | 0.1009 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 792 / 174 | 0.048 [-0.34, 0.30] | 0.1694 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 732 / 234 | 0.155 [-0.26, 0.30] | 0.1511 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 786 / 180 | 0.429 [0.13, 0.62] | 0.0597 |
| `ibm_kingston` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 876 / 90 | -2.491 [-6.23, -1.09] | 0.1389 |
| `ibm_kingston` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 966 / 117 | -12.242 [-33.55, -6.58] | 0.3138 |
| `pooled` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 448 / 144 | 0.001 [-0.98, 0.42] | 0.1550 |
| `pooled` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 448 / 144 | 0.638 [0.28, 0.80] | 0.0904 |
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 654 / 226 | -1.518 [-2.76, -0.93] | 0.3165 |
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 654 / 226 | 0.768 [0.58, 0.89] | 0.0741 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 422 / 144 | -2.569 [-4.47, -1.11] | 0.1859 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 422 / 144 | -2.160 [-4.17, -0.72] | 0.1725 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 1706 / 332 | 0.323 [-0.98, 0.65] | 0.1185 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 1778 / 260 | 0.421 [0.14, 0.60] | 0.1007 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 1662 / 376 | 0.524 [0.23, 0.68] | 0.1200 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 1534 / 504 | -0.232 [-0.90, 0.03] | 0.1941 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 1670 / 368 | 0.248 [0.10, 0.40] | 0.0914 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 1840 / 198 | -5.032 [-11.77, -2.30] | 0.1942 |
| `pooled` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 2038 / 203 | -5.349 [-15.85, -2.37] | 0.2136 |

## H3 · Hardware context and calibration drift (success rate)

**Unseen-circuit** columns: new circuits, calibration windows shared with training. **Calibration-cycle** columns: trained on earlier windows, tested on the latest window (mostly the same circuits), so they isolate calibration drift.

| Scope | Regime | Unseen-circuit R² ± sd | Calibration-cycle R² [95% CI] | Calibration-cycle MAE |
|---|---|---:|---:|---:|
| `ibm_fez` | Circuit Footprint Only (a.* + b.*) | 0.781 ± 0.010 | 0.758 [0.64, 0.84] | 0.0777 |
| `ibm_fez` | Hardware Calibration Only (c.*, device-level) | 0.619 ± 0.009 | 0.371 [0.24, 0.47] | 0.1806 |
| `ibm_fez` | Mixed · Footprint + Submit Calib (c.*) | 0.850 ± 0.008 | 0.773 [0.68, 0.85] | 0.0833 |
| `ibm_kingston` | Circuit Footprint Only (a.* + b.*) | 0.914 ± 0.006 | 0.949 [0.92, 0.97] | 0.0423 |
| `ibm_kingston` | Hardware Calibration Only (c.*, device-level) | 0.683 ± 0.017 | 0.320 [0.18, 0.43] | 0.1606 |
| `ibm_kingston` | Mixed · Footprint + Submit Calib (c.*) | 0.877 ± 0.006 | 0.931 [0.90, 0.96] | 0.0481 |
| `pooled` | Circuit Footprint Only (a.* + b.*) | 0.810 ± 0.013 | — | — |
| `pooled` | Hardware Calibration Only (c.*, device-level) | 0.644 ± 0.009 | — | — |
| `pooled` | Mixed · Footprint + Submit Calib (c.*) | 0.861 ± 0.008 | — | — |

Cross-chip transfer (zero-shot, footprint chosen on the source chip) is in `h3_cross_chip_transfer.csv`. Both chips are IBM Heron, so it supports cross-*chip* transfer only; the cross-*provider* claim needs Rigetti/IonQ data.

## H4 · Paradigm vs random-volumetric training (success rate)

Every paradigm configuration predicted once (repeat-0 folds). `size-matched` trains on as many paradigm rows as random-only has, so training size is not confounded with signal.

| Scope | Regime | nTrain | R² [95% CI] | MAE |
|---|---|---:|---:|---:|
| `ibm_fez` | Random Volumetric Only (RV) | 98 | 0.034 [-0.24, 0.22] | 0.1764 |
| `ibm_fez` | Paradigm Algorithms Only (6 Core) | 857 | 0.676 [0.56, 0.77] | 0.0758 |
| `ibm_fez` | Combined (RV + 6 Core) | 955 | 0.695 [0.58, 0.79] | 0.0735 |
| `ibm_fez` | Paradigm Only, size-matched to RV | 98 | 0.581 [0.49, 0.66] | 0.0967 |
| `ibm_kingston` | Random Volumetric Only (RV) | 90 | 0.558 [0.37, 0.68] | 0.0886 |
| `ibm_kingston` | Paradigm Algorithms Only (6 Core) | 772 | 0.790 [0.64, 0.88] | 0.0522 |
| `ibm_kingston` | Combined (RV + 6 Core) | 862 | 0.795 [0.65, 0.88] | 0.0512 |
| `ibm_kingston` | Paradigm Only, size-matched to RV | 90 | 0.572 [0.45, 0.64] | 0.0856 |
| `pooled` | Random Volumetric Only (RV) | 188 | 0.414 [0.25, 0.54] | 0.1080 |
| `pooled` | Paradigm Algorithms Only (6 Core) | 1630 | 0.677 [0.56, 0.77] | 0.0707 |
| `pooled` | Combined (RV + 6 Core) | 1818 | 0.691 [0.58, 0.79] | 0.0691 |
| `pooled` | Paradigm Only, size-matched to RV | 188 | 0.602 [0.51, 0.67] | 0.0905 |

## Saved Trained Model Artifacts

| Scope | Target | Regime | Best Model | Features | R² | MAE | Size (KB) | Artifact |
|---|---|---|---|---:|---:|---:|---:|---|
| `ibm_fez` | `dsr` | `circuit_only` | LightGBM | 6 | 0.630 | 0.1092 | 54.5 | `models/ibm_fez_dsr_circuit_only.joblib` |
| `ibm_fez` | `dsr` | `mixed_submit` | XGBoost | 13 | 0.782 | 0.0837 | 77.9 | `models/ibm_fez_dsr_mixed_submit.joblib` |
| `ibm_fez` | `hellinger` | `circuit_only` | XGBoost | 7 | 0.784 | 0.0702 | 76.5 | `models/ibm_fez_hellinger_circuit_only.joblib` |
| `ibm_fez` | `hellinger` | `mixed_submit` | Stacking (AutoML) | 14 | 0.882 | 0.0552 | 1002.1 | `models/ibm_fez_hellinger_mixed_submit.joblib` |
| `ibm_fez` | `tvd` | `circuit_only` | XGBoost | 10 | 0.794 | 0.0683 | 25.9 | `models/ibm_fez_tvd_circuit_only.joblib` |
| `ibm_fez` | `tvd` | `mixed_submit` | XGBoost | 17 | 0.895 | 0.0516 | 84.8 | `models/ibm_fez_tvd_mixed_submit.joblib` |
| `ibm_fez` | `success` | `circuit_only` | XGBoost | 8 | 0.781 | 0.0726 | 183.0 | `models/ibm_fez_success_circuit_only.joblib` |
| `ibm_fez` | `success` | `mixed_submit` | XGBoost | 15 | 0.850 | 0.0599 | 82.3 | `models/ibm_fez_success_mixed_submit.joblib` |
| `ibm_kingston` | `dsr` | `circuit_only` | SVR | 6 | 0.761 | 0.0858 | 10.1 | `models/ibm_kingston_dsr_circuit_only.joblib` |
| `ibm_kingston` | `dsr` | `mixed_submit` | XGBoost | 13 | 0.770 | 0.0834 | 74.4 | `models/ibm_kingston_dsr_mixed_submit.joblib` |
| `ibm_kingston` | `hellinger` | `circuit_only` | SVR | 8 | 0.901 | 0.0491 | 12.4 | `models/ibm_kingston_hellinger_circuit_only.joblib` |
| `ibm_kingston` | `hellinger` | `mixed_submit` | XGBoost | 15 | 0.895 | 0.0485 | 25.6 | `models/ibm_kingston_hellinger_mixed_submit.joblib` |
| `ibm_kingston` | `tvd` | `circuit_only` | SVR | 7 | 0.879 | 0.0510 | 11.3 | `models/ibm_kingston_tvd_circuit_only.joblib` |
| `ibm_kingston` | `tvd` | `mixed_submit` | XGBoost | 14 | 0.890 | 0.0486 | 80.1 | `models/ibm_kingston_tvd_mixed_submit.joblib` |
| `ibm_kingston` | `success` | `circuit_only` | SVR | 10 | 0.914 | 0.0516 | 13.7 | `models/ibm_kingston_success_circuit_only.joblib` |
| `ibm_kingston` | `success` | `mixed_submit` | SVR | 17 | 0.877 | 0.0559 | 21.6 | `models/ibm_kingston_success_mixed_submit.joblib` |
| `pooled` | `dsr` | `circuit_only` | RF | 10 | 0.651 | 0.1047 | 957.0 | `models/pooled_dsr_circuit_only.joblib` |
| `pooled` | `dsr` | `mixed_submit` | RF | 17 | 0.778 | 0.0831 | 1860.8 | `models/pooled_dsr_mixed_submit.joblib` |
| `pooled` | `hellinger` | `circuit_only` | XGBoost | 7 | 0.796 | 0.0690 | 25.5 | `models/pooled_hellinger_circuit_only.joblib` |
| `pooled` | `hellinger` | `mixed_submit` | XGBoost | 14 | 0.883 | 0.0536 | 241.3 | `models/pooled_hellinger_mixed_submit.joblib` |
| `pooled` | `tvd` | `circuit_only` | Stacking (AutoML) | 5 | 0.798 | 0.0681 | 1158.3 | `models/pooled_tvd_circuit_only.joblib` |
| `pooled` | `tvd` | `mixed_submit` | LightGBM | 12 | 0.889 | 0.0514 | 126.4 | `models/pooled_tvd_mixed_submit.joblib` |
| `pooled` | `success` | `circuit_only` | LightGBM | 9 | 0.810 | 0.0703 | 60.9 | `models/pooled_success_circuit_only.joblib` |
| `pooled` | `success` | `mixed_submit` | LightGBM | 16 | 0.861 | 0.0596 | 109.7 | `models/pooled_success_mixed_submit.joblib` |
