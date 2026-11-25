# Scalability generalization: exploratory regression analysis

For the relationship between success decay in related algorithms, see the [matched decay profiles](decay/report.md).

Backend: **ibm_kingston**. Selected jobs: **1173**; configurations: **189**; campaigns: **3**.
Collection periods (campaign × window): **3**.

```text
         algorithm  jobs
BERNSTEIN-VAZIRANI   234
               GHZ    90
            GROVER   174
  PHASE-ESTIMATION   126
               QFT   162
 RANDOM-VOLUMETRIC    90
              SHOR   117
               VTP   180
```

## Method

Success rate is accepted shots / shots. Error rate is its complement, 1 − success; declining success means increasing error. Each model has one pre-runtime circuit metric, an intercept, and campaign/window fixed effects. OLS uses an identity link; binomial GLM uses accepted/rejected shot counts and a logit link. Standard errors cluster by algorithm/configuration across every campaign and repetition.
Exported rates are rounded to six decimals. Exact success is reconstructed from the stored histograms and frozen accepted labels, after checking the rounded rates agree; binomial counts are not obtained by rounding an approximate rate.

The descriptive model adds algorithm intercept and slope differences. Its slope contrast is algorithm 2 minus algorithm 1; coefficients are per original metric unit. BH q-values adjust all reported slope tests across families, metrics, and model types. A large p/q-value is NOT evidence of equivalent decay or generalization.

Unseen-algorithm tests train on one member of a family and predict the other without using target outcomes. Larger-configuration tests hold out the upper tail of configuration median metric values, preserving all repetitions and campaigns of a configuration. Scaling and baselines are learned from training data only. Unseen collection periods cannot be predicted by fixed effects and are explicitly counted as unsupported. Metric range overlap is reported separately from extrapolation. OLS predictions are not clipped.

## Interpretation limits

- This is exploratory metric screening, not a locked confirmatory test. Selecting the best metric using these holdouts requires a fresh campaign or nested validation for confirmation.
- The thesis pairs QFT/PE, Grover/BV, and vTP/GHZ. An oracle-based pairing does not imply BV contains Grover, nor does GHZ contain teleportation. These tests assess paradigm-level transfer, not arbitrary composition of primitives. Shor composition tests and random-volumetric controls are reported separately below; all eight algorithms enter the analysis.
- Success criteria and random-chance floors differ across algorithms/configurations. Raw-success transfer alone cannot establish a universal physical noise-decay law. Chance baselines are included in held-out predictions for sensitivity analysis, never as predictors.
- Campaign/window effects reduce observed period confounding; they do not remove within-period calibration, layout, or structural differences. One backend cannot establish cross-provider transfer.
- Missing metrics are excluded per feature, not imputed. Rank deficiency, separation, insufficient independent configurations, and convergence failures are logged in skipped_models.csv.
- Confidence bands describe fitted mean uncertainty, not prediction intervals for future jobs.
- Repeated jobs of one configuration run minutes apart. The number of independent units in a held-out score is test_configs, not test_jobs.

## Run order and calibration

Jobs run in algorithm blocks, so collection-period effects do not remove drift inside a window. The table shows, per period, the share of consecutive jobs from the same algorithm, the number of calibration snapshots, and the Spearman correlation between run time and each circuit metric within an algorithm block.

| Period | Jobs | Hours | Calibrations | Consecutive jobs, same algorithm | Median \|ρ(time, metric)\| | Blocks with \|ρ\| > 0.5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| kingston-full-oracle-growth-v1-2026-11-09 / window 20261109 | 391 | 0.86 | 2 | 94% | 0.24 | 5 / 69 |
| kingston-full-oracle-growth-v1-2026-11-10 / window 20261110 | 391 | 0.68 | 1 | 94% | 0.25 | 5 / 69 |
| kingston-full-oracle-growth-v1-2026-11-11 / window 20261111 | 391 | 4.20 | 3 | 94% | 0.43 | 31 / 69 |

Sensitivity: each slope comparison is refitted with hours since the first job of its period as a covariate. Of 52 comparisons, 38 have q < 0.05 without the time term and 38 with it; the slope difference changes sign in 0. This is a partial adjustment. A linear time term cannot separate algorithms that ran in disjoint blocks, and it is not applied to the held-out transfer scores. A calibration-snapshot fixed effect is not fitted: snapshots coincide with algorithm blocks in most periods, so it would be confounded with the algorithm terms. Randomized submission order is needed to remove this.

## Held-out performance

The thesis R² ≥ 0.80 criterion is displayed per prespecified candidate. Every R² carries a 95% interval (r2_ci_low, r2_ci_high) from 1000 bootstrap draws of whole target configurations, with predictions held fixed. An interval that includes the criterion neither passes nor fails it. Negative R² values and out-of-bounds OLS predictions are retained.

rmse_skill is 1 − RMSE / baseline RMSE, where the baseline predicts the per-period mean success of the largest third of the training configurations. The earlier baseline, the per-period mean of all training configurations, overpredicts larger targets by construction; it remains in period_mean_rmse_skill for comparison.

<!-- replication-summary:start -->
Replication across chips and directions (ibm_fez, ibm_kingston), unseen-algorithm transfer, R² ≥ 0.80: 6 of 210 candidates pass. 0 combination(s) pass in the same direction on every chip, 0 pass in both directions on at least one chip, and 0 candidate(s) keep the lower end of their 95% interval at or above 0.80. **No family, metric and model combination reaches the criterion in both directions on every chip.**
<!-- replication-summary:end -->

```text
                                      tests  median_r2  median_mae  median_rmse  beats_largest_tercile  beats_period_mean
protocol              model                                                                                              
larger_configurations binomial_logit     52     -1.343       0.106        0.122                  0.808              0.923
                      ols                52     -0.700       0.096        0.117                  0.846              0.962
unseen_algorithm      binomial_logit     53     -0.222       0.112        0.146                  0.604              0.491
                      ols                53     -0.229       0.125        0.141                  0.585              0.472
```

Candidates reaching the R² criterion: 6 / 210; with the whole 95% interval at or above it: 0 / 210. These are candidate-level results, not acceptance of H2.

Best observed binomial transfer scores among the explored metrics (post hoc screening; use a fresh holdout to confirm):

```text
      family             source             target                                                 metric  test_configs    r2  r2_ci_low  r2_ci_high   mae  rmse_skill
entanglement                VTP                GHZ a.ComplexityMetrics.gate_based_metrics.two_qubit_count            15 0.839      0.736       0.879 0.028       0.698
     fourier                QFT   PHASE-ESTIMATION                             a.StructuralMetrics.volume            21 0.833      0.748       0.897 0.044       0.616
     fourier   PHASE-ESTIMATION                QFT a.ComplexityMetrics.gate_based_metrics.two_qubit_count            27 0.555     -0.450       0.784 0.081       0.565
entanglement                GHZ                VTP a.ComplexityMetrics.gate_based_metrics.two_qubit_count            30 0.260     -0.050       0.433 0.063       0.348
      oracle BERNSTEIN-VAZIRANI             GROVER                  a.quantum_specific.entanglement_ratio            29 0.151     -0.176       0.315 0.185       0.223
      oracle             GROVER BERNSTEIN-VAZIRANI                  a.quantum_specific.entanglement_ratio            18 0.114     -1.013       0.505 0.056       0.850
```

## Artifacts

- `provenance.json`: hashed inputs, selected campaigns, software versions, and settings.
- `slope_comparisons.csv`: slopes, cluster-robust contrast intervals, p/q-values, missingness, and the time-adjusted contrast.
- `run_order_confounding.csv`: run order against algorithm, calibration and circuit size.
- `replication_summary.csv`: which chips and directions reach the criterion per metric.
- `summaries/`: full statsmodels descriptive fit summaries and coefficient tables. Their residual normality diagnostics are descriptive; they do not account for clustering.
- `heldout_scores.csv`: all algorithm-transfer and larger-configuration evaluations.
- `heldout_predictions.csv`: per-job held-out predictions, chance floors, baselines, support.
- `skipped_models.csv`: 38 explicitly unsupported fits/evaluations.


## Shor composition and random-volumetric controls

QFT → Shor and PE → Shor hold all Shor outcomes out of training. Random-volumetric models predict each of the seven algorithmic workloads as a generic hardware control. Shor and random volumetric also receive separate larger-configuration holdouts.

Raw success uses OLS and binomial GLM. A separate OLS sensitivity analysis uses (success − chance) / (ideal success − chance), with both reference probabilities taken from frozen circuit definitions, never measured target outcomes. Zero means chance and one means ideal task success. Undefined denominators are excluded and counted; values are never clipped. This response is not binomial. Normalized scores and raw-success scores have different units; raw_* columns score the normalized model after converting its predictions back to each target's raw probability scale.

Current Shor references have ideal order-recovery success 0.5, versus 1.0 for the mirror circuits. Shor success means order recovery, not completed factorization. The exported Shor configurations all use N=15: width scaling does not demonstrate generalization to larger integers. The Shor runner requests dynamical decoupling and gate twirling; algorithm-specific execution settings are not removed by period effects. Mirror circuits have inverse correlations and a fixed seed in these configurations, so this control is not a universal noise benchmark.

Collection periods absent from the source remain unsupported, including the Shor-only growth campaign for QFT/PE/RV transfer. All jobs remain in the cohort; unsupported prediction counts are explicit. A failure on raw success alone cannot distinguish structural transfer failure from task-definition and execution-setting differences.

`control_comparisons.csv` compares family/composition models with RV models using the same target job IDs, metric, outcome, and model. Positive control_minus_family_rmse favors the family model. Shared jobs and jobs within both training ranges are reported separately. These are descriptive error differences, not significance tests or evidence that circuit-family membership causes an improvement.

Best observed Shor-transfer candidates (exploratory selection):

```text
          source                 outcome          model       metric         r2      mae  test_jobs  unseen_period_jobs
PHASE-ESTIMATION             raw_success binomial_logit       a.size  -0.660919 0.102775        117                   0
             QFT             raw_success binomial_logit       a.size  -2.095862 0.143730        117                   0
PHASE-ESTIMATION ideal_chance_normalized            ols a.num_qubits -11.221867 0.544500        117                   0
             QFT ideal_chance_normalized            ols a.num_qubits -12.671520 0.579624        117                   0
PHASE-ESTIMATION             raw_success            ols a.num_qubits -23.262475 0.488385        117                   0
             QFT             raw_success            ols a.num_qubits -32.102859 0.570070        117                   0
```

Extension evaluations: 405; paired control comparisons: 297; unsupported cases: 105.

Tables: `extension_scores.csv`, `extension_predictions.csv`, `extension_skipped_models.csv`, and `control_comparisons.csv`. The original six-algorithm tables and slope tests retain their original scope.

## Decay curves

![fourier-ols-a_num_qubits.png](figures/fourier-ols-a_num_qubits.png)

![fourier-binomial_logit-a_num_qubits.png](figures/fourier-binomial_logit-a_num_qubits.png)

![fourier-ols-a_depth.png](figures/fourier-ols-a_depth.png)

![fourier-binomial_logit-a_depth.png](figures/fourier-binomial_logit-a_depth.png)

![fourier-ols-a_size.png](figures/fourier-ols-a_size.png)

![fourier-binomial_logit-a_size.png](figures/fourier-binomial_logit-a_size.png)

![fourier-ols-a_ComplexityMetrics_gate_based_metrics_two_qubit_count.png](figures/fourier-ols-a_ComplexityMetrics_gate_based_metrics_two_qubit_count.png)

![fourier-binomial_logit-a_ComplexityMetrics_gate_based_metrics_two_qubit_count.png](figures/fourier-binomial_logit-a_ComplexityMetrics_gate_based_metrics_two_qubit_count.png)

![fourier-ols-a_StructuralMetrics_volume.png](figures/fourier-ols-a_StructuralMetrics_volume.png)

![fourier-binomial_logit-a_StructuralMetrics_volume.png](figures/fourier-binomial_logit-a_StructuralMetrics_volume.png)

![fourier-ols-a_quantum_specific_entanglement_ratio.png](figures/fourier-ols-a_quantum_specific_entanglement_ratio.png)

![fourier-binomial_logit-a_quantum_specific_entanglement_ratio.png](figures/fourier-binomial_logit-a_quantum_specific_entanglement_ratio.png)

![fourier-ols-b_depth.png](figures/fourier-ols-b_depth.png)

![fourier-binomial_logit-b_depth.png](figures/fourier-binomial_logit-b_depth.png)

![fourier-ols-b_two_qubit_depth.png](figures/fourier-ols-b_two_qubit_depth.png)

![fourier-binomial_logit-b_two_qubit_depth.png](figures/fourier-binomial_logit-b_two_qubit_depth.png)

![fourier-ols-b_two_qubit_gates.png](figures/fourier-ols-b_two_qubit_gates.png)

![fourier-binomial_logit-b_two_qubit_gates.png](figures/fourier-binomial_logit-b_two_qubit_gates.png)

![oracle-ols-a_num_qubits.png](figures/oracle-ols-a_num_qubits.png)

![oracle-binomial_logit-a_num_qubits.png](figures/oracle-binomial_logit-a_num_qubits.png)

![oracle-ols-a_depth.png](figures/oracle-ols-a_depth.png)

![oracle-binomial_logit-a_depth.png](figures/oracle-binomial_logit-a_depth.png)

![oracle-ols-a_size.png](figures/oracle-ols-a_size.png)

![oracle-binomial_logit-a_size.png](figures/oracle-binomial_logit-a_size.png)

![oracle-ols-a_StructuralMetrics_volume.png](figures/oracle-ols-a_StructuralMetrics_volume.png)

![oracle-binomial_logit-a_StructuralMetrics_volume.png](figures/oracle-binomial_logit-a_StructuralMetrics_volume.png)

![oracle-ols-a_quantum_specific_entanglement_ratio.png](figures/oracle-ols-a_quantum_specific_entanglement_ratio.png)

![oracle-binomial_logit-a_quantum_specific_entanglement_ratio.png](figures/oracle-binomial_logit-a_quantum_specific_entanglement_ratio.png)

![oracle-ols-b_depth.png](figures/oracle-ols-b_depth.png)

![oracle-binomial_logit-b_depth.png](figures/oracle-binomial_logit-b_depth.png)

![oracle-ols-b_two_qubit_depth.png](figures/oracle-ols-b_two_qubit_depth.png)

![oracle-binomial_logit-b_two_qubit_depth.png](figures/oracle-binomial_logit-b_two_qubit_depth.png)

![oracle-ols-b_two_qubit_gates.png](figures/oracle-ols-b_two_qubit_gates.png)

![oracle-binomial_logit-b_two_qubit_gates.png](figures/oracle-binomial_logit-b_two_qubit_gates.png)

![entanglement-ols-a_num_qubits.png](figures/entanglement-ols-a_num_qubits.png)

![entanglement-binomial_logit-a_num_qubits.png](figures/entanglement-binomial_logit-a_num_qubits.png)

![entanglement-ols-a_depth.png](figures/entanglement-ols-a_depth.png)

![entanglement-binomial_logit-a_depth.png](figures/entanglement-binomial_logit-a_depth.png)

![entanglement-ols-a_size.png](figures/entanglement-ols-a_size.png)

![entanglement-binomial_logit-a_size.png](figures/entanglement-binomial_logit-a_size.png)

![entanglement-ols-a_ComplexityMetrics_gate_based_metrics_two_qubit_count.png](figures/entanglement-ols-a_ComplexityMetrics_gate_based_metrics_two_qubit_count.png)

![entanglement-binomial_logit-a_ComplexityMetrics_gate_based_metrics_two_qubit_count.png](figures/entanglement-binomial_logit-a_ComplexityMetrics_gate_based_metrics_two_qubit_count.png)

![entanglement-ols-a_StructuralMetrics_volume.png](figures/entanglement-ols-a_StructuralMetrics_volume.png)

![entanglement-binomial_logit-a_StructuralMetrics_volume.png](figures/entanglement-binomial_logit-a_StructuralMetrics_volume.png)

![entanglement-ols-a_quantum_specific_entanglement_ratio.png](figures/entanglement-ols-a_quantum_specific_entanglement_ratio.png)

![entanglement-binomial_logit-a_quantum_specific_entanglement_ratio.png](figures/entanglement-binomial_logit-a_quantum_specific_entanglement_ratio.png)

![entanglement-ols-b_depth.png](figures/entanglement-ols-b_depth.png)

![entanglement-binomial_logit-b_depth.png](figures/entanglement-binomial_logit-b_depth.png)

![entanglement-ols-b_two_qubit_depth.png](figures/entanglement-ols-b_two_qubit_depth.png)

![entanglement-binomial_logit-b_two_qubit_depth.png](figures/entanglement-binomial_logit-b_two_qubit_depth.png)

![entanglement-ols-b_two_qubit_gates.png](figures/entanglement-ols-b_two_qubit_gates.png)

![entanglement-binomial_logit-b_two_qubit_gates.png](figures/entanglement-binomial_logit-b_two_qubit_gates.png)
