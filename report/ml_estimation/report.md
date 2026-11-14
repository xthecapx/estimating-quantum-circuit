# QAQS Quantum Circuit Quality Estimation Report

Scopes evaluated: ibm_fez, ibm_kingston, pooled

## Scope: `ibm_fez` (1236 jobs: 757 train/CV, 479 temporal holdout)

| Target | Best Model | k* Pre-Runtime / Candidates | Holdout R² | Holdout MAE | Holdout RMSE | CV R² | H1 (>=0.80) |
|---|---|---|---:|---:|---:|---:|:---:|
| Differential Success Rate (`dsr`) | RF | 7 / 12 | 0.506 | 0.1307 | 0.2426 | 0.784 | FAIL |
| Hellinger Fidelity (`hellinger`) | RF | 10 / 13 | 0.709 | 0.0805 | 0.1513 | 0.858 | FAIL |
| Total Variation Distance (`tvd`) | XGBoost | 10 / 13 | 0.717 | 0.0850 | 0.1496 | 0.882 | FAIL |
| Success Rate (`success`) | RF | 6 / 13 | 0.784 | 0.0763 | 0.1358 | 0.865 | FAIL |

## Scope: `ibm_kingston` (1173 jobs: 782 train/CV, 391 temporal holdout)

| Target | Best Model | k* Pre-Runtime / Candidates | Holdout R² | Holdout MAE | Holdout RMSE | CV R² | H1 (>=0.80) |
|---|---|---|---:|---:|---:|---:|:---:|
| Differential Success Rate (`dsr`) | Stacking (AutoML) | 7 / 16 | 0.877 | 0.0753 | 0.1105 | 0.762 | PASS |
| Hellinger Fidelity (`hellinger`) | RF | 8 / 12 | 0.922 | 0.0465 | 0.0685 | 0.886 | PASS |
| Total Variation Distance (`tvd`) | Stacking (AutoML) | 5 / 14 | 0.910 | 0.0499 | 0.0732 | 0.890 | PASS |
| Success Rate (`success`) | LightGBM | 5 / 16 | 0.944 | 0.0443 | 0.0631 | 0.874 | PASS |

## Scope: `pooled` (2409 jobs: 1539 train/CV, 870 temporal holdout)

| Target | Best Model | k* Pre-Runtime / Candidates | Holdout R² | Holdout MAE | Holdout RMSE | CV R² | H1 (>=0.80) |
|---|---|---|---:|---:|---:|---:|:---:|
| Differential Success Rate (`dsr`) | Stacking (AutoML) | 7 / 16 | 0.694 | 0.0973 | 0.1846 | 0.777 | FAIL |
| Hellinger Fidelity (`hellinger`) | Stacking (AutoML) | 10 / 14 | 0.772 | 0.0668 | 0.1280 | 0.888 | FAIL |
| Total Variation Distance (`tvd`) | Stacking (AutoML) | 8 / 14 | 0.793 | 0.0671 | 0.1220 | 0.888 | FAIL |
| Success Rate (`success`) | RF | 10 / 13 | 0.836 | 0.0617 | 0.1146 | 0.865 | PASS |

## Selected Best Pre-Runtime Predictors (Global Core Footprint)

| Feature | Category | Selected (Scopes×Targets) | Mean Rank | Mean |SHAP| | Mean Perm ΔR² |
|---|---|---:|---:|---:|---:|
| `b.ComplexityMetrics.standardized_metrics.circuit_volume` | ISA Compiled | 10 / 12 | 1.4 | 0.1161 | 0.6772 |
| `b.ComplexityMetrics.standardized_metrics.gate_density` | ISA Compiled | 10 / 12 | 2.5 | 0.0323 | 0.1029 |
| `a.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` | Logical Complexity | 9 / 12 | 3.8 | 0.0248 | 0.0512 |
| `b.ComplexityMetrics.entanglement_metrics.entangling_width` | ISA Compiled | 9 / 12 | 4.0 | 0.0188 | 0.0310 |
| `b.StructuralMetrics.vocabulary` | ISA Compiled | 8 / 12 | 5.1 | 0.0157 | 0.0081 |
| `a.quantum_specific.magic` | Quantum Specific | 7 / 12 | 6.7 | 0.0142 | 0.0134 |
| `b.StructuralMetrics.effort` | ISA Compiled | 6 / 12 | 2.7 | 0.0258 | 0.0469 |
| `b.ComplexityMetrics.gate_based_metrics.multi_qubit_ratio` | ISA Compiled | 5 / 12 | 4.6 | 0.0269 | 0.0537 |
| `b.BehavioralMetrics.measurement` | ISA Compiled | 5 / 12 | 6.2 | 0.0132 | 0.0062 |
| `b.BehavioralMetrics.critical_depth` | ISA Compiled | 4 / 12 | 8.5 | 0.0069 | 0.0054 |
| `a.BehavioralMetrics.measurement` | Logical Behavioral | 3 / 12 | 8.3 | 0.0071 | 0.0033 |
| `a.StructuralMetrics.effort` | Logical Structural | 2 / 12 | 4.0 | 0.0639 | 0.1885 |
| `b.BehavioralMetrics.liveness` | ISA Compiled | 2 / 12 | 6.0 | 0.0117 | 0.0062 |
| `a.StructuralMetrics.total_operands` | Logical Structural | 1 / 12 | 2.0 | 0.1017 | 0.3595 |
| `a.StructuralMetrics.difficulty` | Logical Structural | 1 / 12 | 1.0 | 0.1006 | 0.1583 |

## Top-k Pre-Runtime Feature Selection Ablation

| Scope | Target | Selected k* (CV R²) | Full Candidates k (CV R²) |
|---|---|---|---:|
| `ibm_fez` | `dsr` | k=7 (0.660) | k=12 (0.634) |
| `ibm_fez` | `hellinger` | k=10 (0.813) | k=13 (0.804) |
| `ibm_fez` | `tvd` | k=10 (0.809) | k=13 (0.801) |
| `ibm_fez` | `success` | k=6 (0.803) | k=13 (0.792) |
| `ibm_kingston` | `dsr` | k=7 (0.748) | k=16 (0.727) |
| `ibm_kingston` | `hellinger` | k=8 (0.895) | k=12 (0.881) |
| `ibm_kingston` | `tvd` | k=5 (0.884) | k=14 (0.869) |
| `ibm_kingston` | `success` | k=5 (0.881) | k=16 (0.879) |
| `pooled` | `dsr` | k=7 (0.715) | k=16 (0.713) |
| `pooled` | `hellinger` | k=10 (0.834) | k=14 (0.829) |
| `pooled` | `tvd` | k=8 (0.826) | k=14 (0.822) |
| `pooled` | `success` | k=10 (0.827) | k=13 (0.824) |

## Saved Trained Model Artifacts

| Scope | Target | Regime | Best Model | Features | R² | MAE | Size (KB) | Artifact |
|---|---|---|---|---:|---:|---:|---:|---|
| `ibm_fez` | `dsr` | `circuit_only` | SVR | 7 | 0.532 | 0.1197 | 13.9 | `models/ibm_fez_dsr_circuit_only.joblib` |
| `ibm_fez` | `dsr` | `mixed_submit` | RF | 15 | 0.506 | 0.1307 | 1267.0 | `models/ibm_fez_dsr_mixed_submit.joblib` |
| `ibm_fez` | `hellinger` | `circuit_only` | RF | 10 | 0.667 | 0.0826 | 1342.1 | `models/ibm_fez_hellinger_circuit_only.joblib` |
| `ibm_fez` | `hellinger` | `mixed_submit` | RF | 18 | 0.709 | 0.0805 | 1659.2 | `models/ibm_fez_hellinger_mixed_submit.joblib` |
| `ibm_fez` | `tvd` | `circuit_only` | RF | 10 | 0.683 | 0.0823 | 1350.0 | `models/ibm_fez_tvd_circuit_only.joblib` |
| `ibm_fez` | `tvd` | `mixed_submit` | XGBoost | 18 | 0.717 | 0.0850 | 83.0 | `models/ibm_fez_tvd_mixed_submit.joblib` |
| `ibm_fez` | `success` | `circuit_only` | SVR | 6 | 0.763 | 0.0751 | 11.8 | `models/ibm_fez_success_circuit_only.joblib` |
| `ibm_fez` | `success` | `mixed_submit` | RF | 14 | 0.784 | 0.0763 | 1514.8 | `models/ibm_fez_success_mixed_submit.joblib` |
| `ibm_kingston` | `dsr` | `circuit_only` | RF | 7 | 0.899 | 0.0631 | 855.8 | `models/ibm_kingston_dsr_circuit_only.joblib` |
| `ibm_kingston` | `dsr` | `mixed_submit` | Stacking (AutoML) | 15 | 0.877 | 0.0753 | 650.8 | `models/ibm_kingston_dsr_mixed_submit.joblib` |
| `ibm_kingston` | `hellinger` | `circuit_only` | SVR | 8 | 0.946 | 0.0391 | 12.1 | `models/ibm_kingston_hellinger_circuit_only.joblib` |
| `ibm_kingston` | `hellinger` | `mixed_submit` | RF | 16 | 0.922 | 0.0465 | 1515.8 | `models/ibm_kingston_hellinger_mixed_submit.joblib` |
| `ibm_kingston` | `tvd` | `circuit_only` | SVR | 5 | 0.945 | 0.0396 | 8.4 | `models/ibm_kingston_tvd_circuit_only.joblib` |
| `ibm_kingston` | `tvd` | `mixed_submit` | Stacking (AutoML) | 13 | 0.910 | 0.0499 | 920.3 | `models/ibm_kingston_tvd_mixed_submit.joblib` |
| `ibm_kingston` | `success` | `circuit_only` | SVR | 5 | 0.957 | 0.0398 | 9.0 | `models/ibm_kingston_success_circuit_only.joblib` |
| `ibm_kingston` | `success` | `mixed_submit` | LightGBM | 13 | 0.944 | 0.0443 | 70.6 | `models/ibm_kingston_success_mixed_submit.joblib` |
| `pooled` | `dsr` | `circuit_only` | XGBoost | 7 | 0.688 | 0.0943 | 74.1 | `models/pooled_dsr_circuit_only.joblib` |
| `pooled` | `dsr` | `mixed_submit` | Stacking (AutoML) | 15 | 0.694 | 0.0973 | 1099.4 | `models/pooled_dsr_mixed_submit.joblib` |
| `pooled` | `hellinger` | `circuit_only` | XGBoost | 10 | 0.760 | 0.0681 | 81.4 | `models/pooled_hellinger_circuit_only.joblib` |
| `pooled` | `hellinger` | `mixed_submit` | Stacking (AutoML) | 18 | 0.772 | 0.0668 | 1534.1 | `models/pooled_hellinger_mixed_submit.joblib` |
| `pooled` | `tvd` | `circuit_only` | XGBoost | 8 | 0.771 | 0.0677 | 82.7 | `models/pooled_tvd_circuit_only.joblib` |
| `pooled` | `tvd` | `mixed_submit` | Stacking (AutoML) | 16 | 0.793 | 0.0671 | 1571.5 | `models/pooled_tvd_mixed_submit.joblib` |
| `pooled` | `success` | `circuit_only` | XGBoost | 10 | 0.838 | 0.0608 | 81.8 | `models/pooled_success_circuit_only.joblib` |
| `pooled` | `success` | `mixed_submit` | RF | 18 | 0.836 | 0.0617 | 2512.6 | `models/pooled_success_mixed_submit.joblib` |
