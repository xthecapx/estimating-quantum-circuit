# QAQS Quantum Circuit Quality Estimation Report

Scopes evaluated: ibm_fez, ibm_kingston, pooled

## Validation tests

| Test | Question | Method | Where reported |
|---|---|---|---|
| **Unseen-circuit validation** | Does QAQS predict circuits it has never seen? | Repeated grouped K-fold by circuit configuration (5 folds x 3 repeats, 189 configurations, folds shared across chips) | H1 tables below; H2; H4 |
| **Calibration-cycle validation** | Does QAQS predict a later calibration cycle? | Forward temporal holdout: train on earlier windows, test on the latest window (mostly the same circuits) | H3 section |
| **Prospective validation** | Does QAQS predict a run that did not exist at training time? | Frozen models scored on a new IBM run, predictions committed before results | Not yet run |

Unseen-circuit validation: every configuration is predicted once per repeat by a model that never saw it, on any chip. Footprint selection, calibration-feature selection, tuning and model choice happen inside each training fold.

**QAQS row** = score of that whole procedure (the honest H1 estimate). Per-model rows are shown for comparison; choosing the best of them afterwards is optimistic.

R² = mean over repeats ± sd between repeats. CI = mean of per-repeat 95% cluster-bootstrap intervals (resampling configurations). H1 PASS needs the CI above 0.80.

Calibration drift is *not* tested by unseen-circuit validation: every configuration also ran in the training windows. See calibration-cycle validation (H3) and prospective validation.

## Scope: `ibm_fez` (1236 jobs, 189 configurations) · unseen-circuit validation

| Target | QAQS circuit-only R² ± sd [95% CI] | MAE | Mixed (+calib) R² | Best single model (R²) | Deployed model | k* (fold range) | H1 |
|---|---:|---:|---:|---|---|---|:---:|
| Differential Success Rate (`dsr`) | 0.615 ± 0.007 [0.48, 0.71] | 0.1145 | 0.777 | RF (0.619) | XGBoost | 6 (6–10) | FAIL |
| Hellinger Fidelity (`hellinger`) | 0.785 ± 0.006 [0.71, 0.84] | 0.0712 | 0.879 | XGBoost (0.783) | XGBoost | 10 (3–10) | INCONCLUSIVE |
| Success Rate (`success`) | 0.777 ± 0.015 [0.68, 0.85] | 0.0734 | 0.861 | XGBoost (0.793) | RF | 8 (3–10) | INCONCLUSIVE |
| Total Variation Distance (`tvd`) | 0.801 ± 0.002 [0.73, 0.85] | 0.0684 | 0.876 | XGBoost (0.794) | RF | 10 (3–10) | INCONCLUSIVE |

## Scope: `ibm_kingston` (1173 jobs, 189 configurations) · unseen-circuit validation

| Target | QAQS circuit-only R² ± sd [95% CI] | MAE | Mixed (+calib) R² | Best single model (R²) | Deployed model | k* (fold range) | H1 |
|---|---:|---:|---:|---|---|---|:---:|
| Differential Success Rate (`dsr`) | 0.771 ± 0.011 [0.63, 0.86] | 0.0844 | 0.780 | LightGBM (0.783) | SVR | 6 (5–8) | INCONCLUSIVE |
| Hellinger Fidelity (`hellinger`) | 0.888 ± 0.008 [0.83, 0.93] | 0.0506 | 0.889 | SVR (0.892) | SVR | 8 (5–10) | PASS |
| Success Rate (`success`) | 0.909 ± 0.016 [0.85, 0.94] | 0.0512 | 0.877 | SVR (0.915) | SVR | 10 (4–10) | PASS |
| Total Variation Distance (`tvd`) | 0.896 ± 0.005 [0.84, 0.94] | 0.0483 | 0.889 | SVR (0.892) | SVR | 7 (4–10) | PASS |

## Scope: `pooled` (2409 jobs, 189 configurations) · unseen-circuit validation

| Target | QAQS circuit-only R² ± sd [95% CI] | MAE | Mixed (+calib) R² | Best single model (R²) | Deployed model | k* (fold range) | H1 |
|---|---:|---:|---:|---|---|---|:---:|
| Differential Success Rate (`dsr`) | 0.661 ± 0.018 [0.51, 0.76] | 0.1052 | 0.794 | RF (0.664) | RF | 10 (5–10) | FAIL |
| Hellinger Fidelity (`hellinger`) | 0.798 ± 0.010 [0.72, 0.85] | 0.0697 | 0.885 | LightGBM (0.801) | LightGBM | 8 (5–10) | INCONCLUSIVE |
| Success Rate (`success`) | 0.809 ± 0.004 [0.73, 0.86] | 0.0709 | 0.867 | LightGBM (0.821) | LightGBM | 10 (5–10) | INCONCLUSIVE |
| Total Variation Distance (`tvd`) | 0.798 ± 0.004 [0.72, 0.85] | 0.0675 | 0.890 | XGBoost (0.803) | LightGBM | 8 (5–10) | INCONCLUSIVE |

## Selected Best Pre-Runtime Predictors (Global Core Footprint)

| Feature | Category | Selected (Scopes×Targets) | Mean Rank | Mean |SHAP| | Mean Perm ΔR² |
|---|---|---:|---:|---:|---:|
| `b.ComplexityMetrics.standardized_metrics.circuit_volume` | ISA Compiled | 10 / 12 | 1.4 | 0.1178 | 0.7083 |
| `b.ComplexityMetrics.standardized_metrics.gate_density` | ISA Compiled | 10 / 12 | 2.7 | 0.0388 | 0.1169 |
| `a.quantum_specific.magic` | Quantum Specific | 8 / 12 | 5.5 | 0.0155 | 0.0223 |
| `b.ComplexityMetrics.entanglement_metrics.entangling_width` | ISA Compiled | 8 / 12 | 5.1 | 0.0146 | 0.0301 |
| `b.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` | ISA Compiled | 7 / 12 | 3.6 | 0.0301 | 0.0535 |
| `b.BehavioralMetrics.measurement` | ISA Compiled | 7 / 12 | 6.3 | 0.0092 | 0.0163 |
| `b.StructuralMetrics.effort` | ISA Compiled | 6 / 12 | 3.0 | 0.0324 | 0.0636 |
| `a.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` | Logical Complexity | 6 / 12 | 4.7 | 0.0201 | 0.0393 |
| `b.StructuralMetrics.vocabulary` | ISA Compiled | 6 / 12 | 4.3 | 0.0152 | 0.0239 |
| `a.quantum_specific.coherence` | Quantum Specific | 4 / 12 | 7.0 | 0.0121 | 0.0199 |
| `b.ComplexityMetrics.derived_metrics.square_ratio` | ISA Compiled | 3 / 12 | 5.0 | 0.0145 | 0.0346 |
| `a.BehavioralMetrics.parallelism` | Logical Behavioral | 3 / 12 | 7.0 | 0.0096 | 0.0125 |
| `a.StructuralMetrics.difficulty` | Logical Structural | 2 / 12 | 1.0 | 0.0903 | 0.2440 |
| `b.BehavioralMetrics.liveness` | ISA Compiled | 2 / 12 | 4.5 | 0.0143 | 0.0183 |
| `a.ComplexityMetrics.standardized_metrics.gate_density` | Logical Complexity | 2 / 12 | 6.0 | 0.0115 | 0.0274 |

## Top-k Pre-Runtime Feature Selection Ablation

| Scope | Target | Selected k* (CV R²) | Full Candidates k (CV R²) |
|---|---|---|---:|
| `ibm_fez` | `dsr` | k=6 (0.641) | k=11 (0.639) |
| `ibm_fez` | `hellinger` | k=10 (0.790) | k=16 (0.785) |
| `ibm_fez` | `success` | k=8 (0.787) | k=15 (0.791) |
| `ibm_fez` | `tvd` | k=10 (0.793) | k=15 (0.798) |
| `ibm_kingston` | `dsr` | k=6 (0.773) | k=16 (0.754) |
| `ibm_kingston` | `hellinger` | k=8 (0.899) | k=12 (0.904) |
| `ibm_kingston` | `success` | k=10 (0.905) | k=13 (0.902) |
| `ibm_kingston` | `tvd` | k=7 (0.894) | k=14 (0.895) |
| `pooled` | `dsr` | k=10 (0.658) | k=16 (0.662) |
| `pooled` | `hellinger` | k=8 (0.800) | k=10 (0.797) |
| `pooled` | `success` | k=10 (0.832) | k=11 (0.829) |
| `pooled` | `tvd` | k=8 (0.809) | k=11 (0.796) |

## H2 · Generalization to unseen configurations (success rate)

Protocol-specific unseen-circuit tests (the held-out circuits are larger, or from another algorithm). Footprint chosen on each protocol's own training set. `M2 prior + residual` adds the analytical M2 estimate (uses submit-time calibration) as a decay prior and learns its residual from the footprint; it is calibration-aware, so it is reported separately from the circuit-only claim.

| Scope | Protocol | Task | nTrain / nTest | R² [95% CI] | MAE |
|---|---|---|---:|---:|---:|
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) | 232 / 72 | -0.288 [-1.71, 0.16] | 0.2070 |
| `ibm_fez` | scaling_extrapolation | Scaling · Fourier (QFT/PHASE-ESTIMATION) · M2 prior + residual | 232 / 72 | 0.528 [0.05, 0.72] | 0.1215 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 352 / 110 | -1.134 [-2.31, -0.53] | 0.2892 |
| `ibm_fez` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 352 / 110 | 0.587 [0.27, 0.79] | 0.0914 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 214 / 72 | -0.171 [-0.53, -0.03] | 0.1122 |
| `ibm_fez` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 214 / 72 | -0.156 [-0.61, 0.17] | 0.1002 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 882 / 170 | 0.188 [-1.50, 0.60] | 0.1568 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 918 / 134 | 0.377 [0.08, 0.56] | 0.1223 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 850 / 202 | 0.533 [0.22, 0.70] | 0.1121 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 792 / 260 | -1.170 [-2.84, -0.60] | 0.2718 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 864 / 188 | 0.031 [-0.26, 0.30] | 0.1265 |
| `ibm_fez` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 954 / 98 | -5.501 [-13.23, -2.53] | 0.2064 |
| `ibm_fez` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 1052 / 86 | -6.573 [-24.63, -2.00] | 0.2201 |
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
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) | 658 / 212 | -0.956 [-2.12, -0.42] | 0.2718 |
| `pooled` | scaling_extrapolation | Scaling · Oracle (GROVER/BERNSTEIN-VAZIRANI) · M2 prior + residual | 658 / 212 | 0.743 [0.54, 0.87] | 0.0745 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) | 412 / 144 | 0.042 [-0.15, 0.13] | 0.0875 |
| `pooled` | scaling_extrapolation | Scaling · Entanglement (VTP/GHZ) · M2 prior + residual | 412 / 144 | 0.055 [-0.20, 0.31] | 0.0746 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> QFT | 1686 / 332 | 0.236 [-1.30, 0.61] | 0.1313 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> PHASE-ESTIMATION | 1758 / 260 | 0.393 [0.11, 0.65] | 0.1018 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> GROVER | 1642 / 376 | -0.581 [-1.11, -0.25] | 0.2338 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> BERNSTEIN-VAZIRANI | 1524 / 494 | -0.326 [-1.12, -0.06] | 0.2029 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> VTP | 1650 / 368 | 0.243 [0.05, 0.42] | 0.0784 |
| `pooled` | leave_algorithm_out | Zero-shot · Core 5 -> GHZ | 1830 / 188 | -1.882 [-5.17, -0.50] | 0.1314 |
| `pooled` | composite_anchor | Zero-shot composite · Core 6 -> SHOR | 2018 / 203 | -5.804 [-16.36, -2.47] | 0.2149 |

## H3 · Hardware context and calibration drift (success rate)

**Unseen-circuit** columns: new circuits, calibration windows shared with training. **Calibration-cycle** columns: trained on earlier windows, tested on the latest window (mostly the same circuits), so they isolate calibration drift.

| Scope | Regime | Unseen-circuit R² ± sd | Calibration-cycle R² [95% CI] | Calibration-cycle MAE |
|---|---|---:|---:|---:|
| `ibm_fez` | Circuit Footprint Only (a.* + b.*) | 0.777 ± 0.015 | 0.745 [0.63, 0.82] | 0.0815 |
| `ibm_fez` | Hardware Calibration Only (c.*, device-level) | 0.637 ± 0.005 | 0.334 [0.19, 0.44] | 0.1893 |
| `ibm_fez` | Mixed · Footprint + Submit Calib (c.*) | 0.861 ± 0.001 | 0.759 [0.66, 0.83] | 0.0920 |
| `ibm_kingston` | Circuit Footprint Only (a.* + b.*) | 0.909 ± 0.016 | 0.949 [0.92, 0.97] | 0.0423 |
| `ibm_kingston` | Hardware Calibration Only (c.*, device-level) | 0.703 ± 0.008 | 0.320 [0.18, 0.43] | 0.1606 |
| `ibm_kingston` | Mixed · Footprint + Submit Calib (c.*) | 0.877 ± 0.009 | 0.931 [0.90, 0.96] | 0.0481 |
| `pooled` | Circuit Footprint Only (a.* + b.*) | 0.809 ± 0.004 | — | — |
| `pooled` | Hardware Calibration Only (c.*, device-level) | 0.652 ± 0.008 | — | — |
| `pooled` | Mixed · Footprint + Submit Calib (c.*) | 0.867 ± 0.004 | — | — |

Cross-chip transfer (zero-shot, footprint chosen on the source chip) is in `h3_cross_chip_transfer.csv`. Both chips are IBM Heron, so it supports cross-*chip* transfer only; the cross-*provider* claim needs Rigetti/IonQ data.

## H4 · Paradigm vs random-volumetric training (success rate)

Every paradigm configuration predicted once (repeat-0 folds). `size-matched` trains on as many paradigm rows as random-only has, so training size is not confounded with signal.

| Scope | Regime | nTrain | R² [95% CI] | MAE |
|---|---|---:|---:|---:|
| `ibm_fez` | Random Volumetric Only (RV) | 98 | 0.262 [0.10, 0.40] | 0.1415 |
| `ibm_fez` | Paradigm Algorithms Only (6 Core) | 841 | 0.692 [0.58, 0.79] | 0.0737 |
| `ibm_fez` | Combined (RV + 6 Core) | 939 | 0.701 [0.60, 0.80] | 0.0722 |
| `ibm_fez` | Paradigm Only, size-matched to RV | 98 | 0.524 [0.44, 0.60] | 0.1018 |
| `ibm_kingston` | Random Volumetric Only (RV) | 90 | 0.563 [0.37, 0.68] | 0.0873 |
| `ibm_kingston` | Paradigm Algorithms Only (6 Core) | 772 | 0.783 [0.64, 0.86] | 0.0544 |
| `ibm_kingston` | Combined (RV + 6 Core) | 862 | 0.802 [0.67, 0.88] | 0.0526 |
| `ibm_kingston` | Paradigm Only, size-matched to RV | 90 | 0.605 [0.47, 0.69] | 0.0799 |
| `pooled` | Random Volumetric Only (RV) | 188 | 0.305 [0.12, 0.46] | 0.1266 |
| `pooled` | Paradigm Algorithms Only (6 Core) | 1614 | 0.700 [0.59, 0.79] | 0.0685 |
| `pooled` | Combined (RV + 6 Core) | 1802 | 0.693 [0.57, 0.78] | 0.0696 |
| `pooled` | Paradigm Only, size-matched to RV | 188 | 0.571 [0.48, 0.65] | 0.0895 |

## Saved Trained Model Artifacts

| Scope | Target | Regime | Best Model | Features | R² | MAE | Size (KB) | Artifact |
|---|---|---|---|---:|---:|---:|---:|---|
| `ibm_fez` | `dsr` | `circuit_only` | XGBoost | 6 | 0.615 | 0.1145 | 25.3 | `models/ibm_fez_dsr_circuit_only.joblib` |
| `ibm_fez` | `dsr` | `mixed_submit` | LightGBM | 13 | 0.777 | 0.0859 | 75.5 | `models/ibm_fez_dsr_mixed_submit.joblib` |
| `ibm_fez` | `hellinger` | `circuit_only` | XGBoost | 10 | 0.785 | 0.0712 | 78.7 | `models/ibm_fez_hellinger_circuit_only.joblib` |
| `ibm_fez` | `hellinger` | `mixed_submit` | LightGBM | 17 | 0.879 | 0.0556 | 64.5 | `models/ibm_fez_hellinger_mixed_submit.joblib` |
| `ibm_fez` | `success` | `circuit_only` | RF | 8 | 0.777 | 0.0734 | 670.2 | `models/ibm_fez_success_circuit_only.joblib` |
| `ibm_fez` | `success` | `mixed_submit` | XGBoost | 15 | 0.861 | 0.0584 | 80.6 | `models/ibm_fez_success_mixed_submit.joblib` |
| `ibm_fez` | `tvd` | `circuit_only` | RF | 10 | 0.801 | 0.0684 | 1613.5 | `models/ibm_fez_tvd_circuit_only.joblib` |
| `ibm_fez` | `tvd` | `mixed_submit` | XGBoost | 17 | 0.876 | 0.0549 | 25.7 | `models/ibm_fez_tvd_mixed_submit.joblib` |
| `ibm_kingston` | `dsr` | `circuit_only` | SVR | 6 | 0.771 | 0.0844 | 10.1 | `models/ibm_kingston_dsr_circuit_only.joblib` |
| `ibm_kingston` | `dsr` | `mixed_submit` | XGBoost | 13 | 0.780 | 0.0826 | 74.4 | `models/ibm_kingston_dsr_mixed_submit.joblib` |
| `ibm_kingston` | `hellinger` | `circuit_only` | SVR | 8 | 0.888 | 0.0506 | 12.4 | `models/ibm_kingston_hellinger_circuit_only.joblib` |
| `ibm_kingston` | `hellinger` | `mixed_submit` | XGBoost | 15 | 0.889 | 0.0487 | 25.6 | `models/ibm_kingston_hellinger_mixed_submit.joblib` |
| `ibm_kingston` | `success` | `circuit_only` | SVR | 10 | 0.909 | 0.0512 | 13.7 | `models/ibm_kingston_success_circuit_only.joblib` |
| `ibm_kingston` | `success` | `mixed_submit` | SVR | 17 | 0.877 | 0.0568 | 21.6 | `models/ibm_kingston_success_mixed_submit.joblib` |
| `ibm_kingston` | `tvd` | `circuit_only` | SVR | 7 | 0.896 | 0.0483 | 11.3 | `models/ibm_kingston_tvd_circuit_only.joblib` |
| `ibm_kingston` | `tvd` | `mixed_submit` | XGBoost | 14 | 0.889 | 0.0485 | 80.1 | `models/ibm_kingston_tvd_mixed_submit.joblib` |
| `pooled` | `dsr` | `circuit_only` | RF | 10 | 0.661 | 0.1052 | 980.8 | `models/pooled_dsr_circuit_only.joblib` |
| `pooled` | `dsr` | `mixed_submit` | LightGBM | 17 | 0.794 | 0.0811 | 93.6 | `models/pooled_dsr_mixed_submit.joblib` |
| `pooled` | `hellinger` | `circuit_only` | LightGBM | 8 | 0.798 | 0.0697 | 62.0 | `models/pooled_hellinger_circuit_only.joblib` |
| `pooled` | `hellinger` | `mixed_submit` | LightGBM | 15 | 0.885 | 0.0527 | 65.0 | `models/pooled_hellinger_mixed_submit.joblib` |
| `pooled` | `success` | `circuit_only` | LightGBM | 10 | 0.809 | 0.0709 | 58.8 | `models/pooled_success_circuit_only.joblib` |
| `pooled` | `success` | `mixed_submit` | LightGBM | 17 | 0.867 | 0.0591 | 107.6 | `models/pooled_success_mixed_submit.joblib` |
| `pooled` | `tvd` | `circuit_only` | LightGBM | 8 | 0.798 | 0.0675 | 61.5 | `models/pooled_tvd_circuit_only.joblib` |
| `pooled` | `tvd` | `mixed_submit` | LightGBM | 15 | 0.890 | 0.0508 | 128.2 | `models/pooled_tvd_mixed_submit.joblib` |
