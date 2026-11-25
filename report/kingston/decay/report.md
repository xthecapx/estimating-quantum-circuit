# Do related circuits lose success in the same way?

Backend ibm_kingston. The cohort contains 1,173 jobs and 189 configurations in 3 collection periods.

[Linear fits, target definitions, and comparison table](trend_review.md)

[All algorithm pairs and exploratory decay groups](groups/report.md)

Each comparison uses exact resource values observed for both algorithms in the same campaign and window. At each resource value we average repetitions within each configuration, then give each configuration equal weight. At least three shared values are required. Each value has equal weight in the descriptive straight-line slope.

Spearman rho measures whether the observed success means rank the shared resource values similarly. The slopes show the direction and average size of change per unit. Step-rate Spearman rho ranks the observed changes per resource unit between adjacent levels and compares those ranks when at least three intervals exist. The adjacent-interval counts show how often both workloads actually decline or rise over the same step. A high rho can accompany very different slopes. Correlating two fitted nonconstant straight lines on the same grid would always give +1 or −1.

Error is one minus success, so the raw error slopes have the opposite signs and the same magnitudes. Normalized comparisons use (success − chance) / (ideal success − chance) wherever the denominator exceeds 1e-8.

## How far apart are the fitted losses?

The gap is 100 × |slope A − slope B| × (largest − smallest shared level): the difference in fitted change over the shared range, in target points. Each pair is read on success, except pairs involving Shor, which are read on chance-corrected success because Shor's raw success falls with its chance floor. The table gives the median gap across eligible periods with a 95% bootstrap interval and the bootstrap probability that this median is within 5 points. An interval that straddles 5 supports neither similar nor different decay.

Bootstrap: 1000 draws; jobs are resampled with replacement within each configuration at each resource level (algorithm × level × configuration × period), so the set of configurations and levels stays fixed; deviations of a resampled configuration mean are scaled by sqrt(n/(n-1)) to offset the small number of repetitions, and a configuration with one job contributes no variation. This is not binomial shot resampling: it reflects job-to-job variation, which includes shot noise. Intervals are 2.5th to 97.5th percentiles.

### Total logical qubits

| Pair | Role | Outcome | Periods | Median gap [95% interval] | P(gap ≤ 5) |
| --- | --- | --- | ---: | ---: | ---: |
| QFT / SHOR | composition | chance_corrected | 3 | 1.93 [0.53, 11.77] | 0.56 |
| SHOR / VTP | other | chance_corrected | 3 | 3.37 [0.56, 6.10] | 0.94 |
| BERNSTEIN-VAZIRANI / VTP | other | success | 3 | 6.09 [4.04, 8.30] | 0.14 |
| GHZ / SHOR | other | chance_corrected | 3 | 7.25 [1.30, 10.33] | 0.30 |
| VTP / GHZ | entanglement | success | 3 | 7.60 [5.38, 10.11] | 0.01 |
| QFT / PHASE-ESTIMATION | fourier | success | 3 | 7.89 [6.09, 9.79] | 0.00 |
| PHASE-ESTIMATION / VTP | other | success | 3 | 8.63 [3.95, 11.62] | 0.08 |
| BERNSTEIN-VAZIRANI / SHOR | other | chance_corrected | 3 | 10.42 [7.16, 13.07] | 0.00 |
| BERNSTEIN-VAZIRANI / QFT | other | success | 3 | 14.17 [9.83, 16.96] | 0.00 |
| PHASE-ESTIMATION / SHOR | composition | chance_corrected | 3 | 14.96 [12.13, 22.08] | 0.00 |
| BERNSTEIN-VAZIRANI / GHZ | other | success | 3 | 20.45 [18.23, 22.46] | 0.00 |
| SHOR / RANDOM-VOLUMETRIC | control | chance_corrected | 3 | 20.75 [15.65, 27.38] | 0.00 |
| GHZ / QFT | other | success | 3 | 21.68 [19.50, 23.91] | 0.00 |
| BERNSTEIN-VAZIRANI / PHASE-ESTIMATION | other | success | 3 | 22.65 [19.78, 24.61] | 0.00 |
| VTP / RANDOM-VOLUMETRIC | mirror_protocol | success | 3 | 23.42 [20.92, 25.76] | 0.00 |
| QFT / VTP | other | success | 3 | 25.06 [23.83, 26.26] | 0.00 |
| PHASE-ESTIMATION / RANDOM-VOLUMETRIC | control | success | 3 | 25.55 [21.35, 28.32] | 0.00 |
| QFT / RANDOM-VOLUMETRIC | control | success | 3 | 27.41 [24.78, 29.81] | 0.00 |
| GHZ / PHASE-ESTIMATION | other | success | 3 | 27.78 [26.32, 30.44] | 0.00 |
| GROVER / RANDOM-VOLUMETRIC | control | success | 3 | 28.74 [25.67, 32.01] | 0.00 |
| BERNSTEIN-VAZIRANI / RANDOM-VOLUMETRIC | control | success | 3 | 37.84 [35.32, 40.25] | 0.00 |
| GHZ / RANDOM-VOLUMETRIC | control | success | 3 | 52.24 [50.62, 53.91] | 0.00 |
| GROVER / BERNSTEIN-VAZIRANI | oracle | success | 3 | 56.16 [54.76, 57.71] | 0.00 |
| GROVER / PHASE-ESTIMATION | other | success | 3 | 56.19 [55.04, 57.26] | 0.00 |
| GROVER / QFT | other | success | 3 | 73.04 [71.22, 74.87] | 0.00 |
| GHZ / GROVER | other | success | 3 | 73.46 [71.26, 74.56] | 0.00 |

### Logical two-qubit gates

| Pair | Role | Outcome | Periods | Median gap [95% interval] | P(gap ≤ 5) |
| --- | --- | --- | ---: | ---: | ---: |
| QFT / PHASE-ESTIMATION | fourier | success | 3 | 6.61 [4.68, 7.90] | 0.06 |
| VTP / GHZ | entanglement | success | 3 | 7.27 [5.94, 10.76] | 0.00 |
| BERNSTEIN-VAZIRANI / VTP | other | success | 3 | 8.14 [5.15, 9.91] | 0.01 |
| QFT / VTP | other | success | 3 | 9.87 [5.74, 13.96] | 0.01 |
| GHZ / QFT | other | success | 3 | 13.96 [10.64, 17.89] | 0.00 |
| BERNSTEIN-VAZIRANI / GHZ | other | success | 3 | 19.12 [16.64, 21.75] | 0.00 |
| BERNSTEIN-VAZIRANI / QFT | other | success | 3 | 25.93 [19.72, 29.53] | 0.00 |

## Do related pairs agree more often than unrelated ones?

Base rates over every resource, on each pair's primary outcome. A window is a point match when both fitted lines fall and the gap is at most 5 points. Mean P(match) averages the bootstrap probability of that event. A cell is one pair on one resource with at least two eligible windows; it repeats when two or more of its windows are point matches. Family = QFT/PE, Grover/BV, vTP/GHZ and QFT or PE with Shor. Control = any workload with random volumetric. Agreement within a family is evidence of family-specific decay only to the extent that it exceeds the unrelated and control rates.

| Pair class | Pairs | Windows | Point matches | Mean P(match) | Cells | Repeated matches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| family | 5 | 54 | 10 (18.5%) | 0.181 | 18 | 3 (16.7%) |
| random-volumetric control | 7 | 51 | 8 (15.7%) | 0.156 | 17 | 2 (11.8%) |
| unrelated | 15 | 130 | 27 (20.8%) | 0.205 | 43 | 7 (16.3%) |

[Base rates as a table](base_rates.csv)

## Width comparisons

Ranges below span eligible collection periods and describe variation across periods. Repeated configurations recur across periods. Width is total logical qubits and may represent different computational resources across workloads.

![Observed success at shared widths](shared_widths.png)

Each line connects observed means within one collection period.

Pairs involving Shor use chance-corrected success; all others use success.

| Pair | Outcome | Periods | Shared widths per period | Spearman ρ | Change A (points/qubit) | Change B (points/qubit) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| BERNSTEIN-VAZIRANI / GHZ | success | 3 | 13 | 0.86 to 0.98 | -3.79 to -3.26 | -2.09 to -1.38 |
| GROVER / BERNSTEIN-VAZIRANI | success | 3 | 3 | 0.87 to 1.00 | -33.26 to -27.94 | -4.86 to -1.84 |
| BERNSTEIN-VAZIRANI / PHASE-ESTIMATION | success | 3 | 7 | 0.96 to 0.99 | -6.41 to -3.11 | -7.16 to -6.55 |
| BERNSTEIN-VAZIRANI / QFT | success | 3 | 7 | 0.68 to 0.81 | -6.41 to -3.11 | -5.81 to -5.24 |
| BERNSTEIN-VAZIRANI / RANDOM-VOLUMETRIC | success | 3 | 6 | 0.81 to 1.00 | -3.49 to -2.33 | -11.08 to -6.26 |
| BERNSTEIN-VAZIRANI / VTP | success | 3 | 5 | 0.70 to 0.90 | -3.66 to -2.59 | -6.12 to -2.97 |
| GHZ / GROVER | success | 3 | 4 | 0.40 to 1.00 | -2.50 to -1.09 | -25.73 to -23.76 |
| GHZ / PHASE-ESTIMATION | success | 3 | 7 | 0.71 to 0.96 | -2.34 to -0.84 | -7.16 to -6.55 |
| GHZ / QFT | success | 3 | 8 | 0.79 to 0.93 | -2.26 to -1.42 | -5.34 to -4.97 |
| GHZ / RANDOM-VOLUMETRIC | success | 3 | 7 | 0.54 to 0.96 | -2.29 to -1.51 | -11.49 to -7.91 |
| VTP / GHZ | success | 3 | 5 | 0.50 to 0.90 | -6.12 to -2.97 | -2.66 to -0.91 |
| GROVER / PHASE-ESTIMATION | success | 3 | 3 | 1.00 | -33.26 to -27.94 | -5.16 to -3.93 |
| GROVER / QFT | success | 3 | 4 | -0.40 to 0.40 | -25.73 to -23.76 | -1.38 to 1.16 |
| GROVER / RANDOM-VOLUMETRIC | success | 3 | 4 | 1.00 | -25.73 to -23.76 | -16.15 to -13.49 |
| QFT / PHASE-ESTIMATION | success | 3 | 7 | 0.64 to 0.82 | -5.81 to -5.24 | -7.16 to -6.55 |
| PHASE-ESTIMATION / RANDOM-VOLUMETRIC | success | 3 | 6 | 0.83 to 1.00 | -5.97 to -5.57 | -11.08 to -6.26 |
| PHASE-ESTIMATION / VTP | success | 3 | 5 | 0.70 to 0.90 | -6.72 to -5.71 | -6.12 to -2.97 |
| QFT / RANDOM-VOLUMETRIC | success | 3 | 7 | 0.54 to 0.71 | -7.32 to -6.39 | -11.49 to -7.91 |
| QFT / VTP | success | 3 | 5 | 0.90 | -11.40 to -9.23 | -6.12 to -2.97 |
| VTP / RANDOM-VOLUMETRIC | success | 3 | 5 | 0.60 to 0.70 | -6.12 to -2.97 | -10.42 to -5.52 |
| BERNSTEIN-VAZIRANI / SHOR | chance_corrected | 3 | 5 | 0.60 to 0.90 | -6.28 to -3.76 | -3.06 to -1.49 |
| GHZ / SHOR | chance_corrected | 3 | 5 | 0.50 to 0.90 | -1.45 to -0.99 | -3.06 to -1.49 |
| PHASE-ESTIMATION / SHOR | chance_corrected | 3 | 4 | 0.80 to 1.00 | -9.77 to -8.53 | -4.79 to -1.94 |
| QFT / SHOR | chance_corrected | 3 | 4 | 0.00 to 1.00 | -5.73 to -3.96 | -4.79 to -1.94 |
| SHOR / RANDOM-VOLUMETRIC | chance_corrected | 3 | 3 | 0.50 to 1.00 | -7.91 to -1.04 | -20.33 to -10.45 |
| SHOR / VTP | chance_corrected | 3 | 3 | -0.50 to 1.00 | -7.91 to -1.04 | -5.89 to -2.73 |

## QFT and phase estimation by logical two-qubit gate count

| Period | Shared levels | Profile ρ | QFT loss (pp/gate) | PE loss (pp/gate) | Correlation of local rates |
| --- | ---: | ---: | ---: | ---: | ---: |
| kingston-full-oracle-growth-v1-2026-11-09 / window 20261109 | 5 | 0.90 | 0.93 | 1.11 | 0.40 |
| kingston-full-oracle-growth-v1-2026-11-10 / window 20261110 | 5 | 0.90 | 0.78 | 0.96 | 0.20 |
| kingston-full-oracle-growth-v1-2026-11-11 / window 20261111 | 5 | 0.90 | 0.91 | 1.05 | -0.20 |

## Interpretation

These are descriptive comparisons. With three shared sizes, even perfect rank agreement uses only three points. Changing configuration mix across widths, different success criteria, and shared hardware noise can affect trends. Random-volumetric profiles provide a generic comparator. Interpreting differences between pairs requires checking the common levels used by each pair. [Matched controls](matched_controls.csv) compare both family members with the mirror circuit at the same levels in the same period.

The comparison does not assign a predictive R² threshold or infer slope equivalence. The existing family interaction models provide configuration-clustered uncertainty for slope differences across their fitted ranges, which can extend beyond the exact shared levels used here.

See [all metric comparisons](decay_comparisons.csv), [observed level means](matched_levels.csv), and [coverage including unsupported comparisons](overlap.csv).
