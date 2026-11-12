# Do related circuits lose success in the same way?

Backend ibm_kingston. The cohort contains 1,173 jobs and 189 configurations in 3 collection periods.

[Linear fits, target definitions, and comparison table](trend_review.md)

[All algorithm pairs and exploratory decay groups](groups/report.md)

Each comparison uses exact resource values observed for both algorithms in the same campaign and window. At each resource value we average repetitions within each configuration, then give each configuration equal weight. At least three shared values are required. Each value has equal weight in the descriptive straight-line slope.

Spearman rho measures whether the observed success means rank the shared resource values similarly. The slopes show the direction and average size of change per unit. Step-rate Spearman rho ranks the observed changes per resource unit between adjacent levels and compares those ranks when at least three intervals exist. The adjacent-interval counts show how often both workloads actually decline or rise over the same step. A high rho can accompany very different slopes. Correlating two fitted nonconstant straight lines on the same grid would always give +1 or −1.

Error is one minus success, so the raw error slopes have the opposite signs and the same magnitudes. Normalized comparisons use (success − chance) / (ideal success − chance) wherever the denominator exceeds 1e-8.

## Width comparisons

Ranges below span eligible collection periods and describe variation across periods. Repeated configurations recur across periods. Width is total logical qubits and may represent different computational resources across workloads.

![Observed success at shared widths](shared_widths.png)

Each line connects observed means within one collection period.

| Pair | Periods | Shared widths per period | Spearman ρ | Success change A (pp/qubit) | Success change B (pp/qubit) |
| --- | ---: | ---: | ---: | ---: | ---: |
| BERNSTEIN-VAZIRANI / GHZ | 3 | 13 | 0.86 to 0.98 | -3.79 to -3.26 | -2.09 to -1.38 |
| GROVER / BERNSTEIN-VAZIRANI | 3 | 3 | 0.87 to 1.00 | -33.26 to -27.94 | -4.86 to -1.84 |
| BERNSTEIN-VAZIRANI / PHASE-ESTIMATION | 3 | 7 | 0.96 to 0.99 | -6.41 to -3.11 | -7.16 to -6.55 |
| BERNSTEIN-VAZIRANI / QFT | 3 | 7 | 0.68 to 0.81 | -6.41 to -3.11 | -5.81 to -5.24 |
| BERNSTEIN-VAZIRANI / RANDOM-VOLUMETRIC | 3 | 6 | 0.81 to 1.00 | -3.49 to -2.33 | -11.08 to -6.26 |
| BERNSTEIN-VAZIRANI / SHOR | 3 | 5 | 0.90 to 1.00 | -6.36 to -3.84 | -8.13 to -6.86 |
| BERNSTEIN-VAZIRANI / VTP | 3 | 5 | 0.70 to 0.90 | -3.66 to -2.59 | -6.12 to -2.97 |
| GHZ / GROVER | 3 | 4 | 0.40 to 1.00 | -2.50 to -1.09 | -25.73 to -23.76 |
| GHZ / PHASE-ESTIMATION | 3 | 7 | 0.71 to 0.96 | -2.34 to -0.84 | -7.16 to -6.55 |
| GHZ / QFT | 3 | 8 | 0.79 to 0.93 | -2.26 to -1.42 | -5.34 to -4.97 |
| GHZ / RANDOM-VOLUMETRIC | 3 | 7 | 0.54 to 0.96 | -2.29 to -1.51 | -11.49 to -7.91 |
| GHZ / SHOR | 3 | 5 | 0.80 to 1.00 | -1.52 to -1.08 | -8.13 to -6.86 |
| VTP / GHZ | 3 | 5 | 0.50 to 0.90 | -6.12 to -2.97 | -2.66 to -0.91 |
| GROVER / PHASE-ESTIMATION | 3 | 3 | 1.00 | -33.26 to -27.94 | -5.16 to -3.93 |
| GROVER / QFT | 3 | 4 | -0.40 to 0.40 | -25.73 to -23.76 | -1.38 to 1.16 |
| GROVER / RANDOM-VOLUMETRIC | 3 | 4 | 1.00 | -25.73 to -23.76 | -16.15 to -13.49 |
| QFT / PHASE-ESTIMATION | 3 | 7 | 0.64 to 0.82 | -5.81 to -5.24 | -7.16 to -6.55 |
| PHASE-ESTIMATION / RANDOM-VOLUMETRIC | 3 | 6 | 0.83 to 1.00 | -5.97 to -5.57 | -11.08 to -6.26 |
| PHASE-ESTIMATION / SHOR | 3 | 4 | 1.00 | -10.10 to -9.00 | -10.36 to -8.37 |
| PHASE-ESTIMATION / VTP | 3 | 5 | 0.70 to 0.90 | -6.72 to -5.71 | -6.12 to -2.97 |
| QFT / RANDOM-VOLUMETRIC | 3 | 7 | 0.54 to 0.71 | -7.32 to -6.39 | -11.49 to -7.91 |
| QFT / SHOR | 3 | 4 | 0.60 | -6.40 to -4.26 | -10.36 to -8.37 |
| QFT / VTP | 3 | 5 | 0.90 | -11.40 to -9.23 | -6.12 to -2.97 |
| SHOR / RANDOM-VOLUMETRIC | 3 | 3 | 1.00 | -13.32 to -7.98 | -20.48 to -10.64 |
| VTP / RANDOM-VOLUMETRIC | 3 | 5 | 0.60 to 0.70 | -6.12 to -2.97 | -10.42 to -5.52 |
| SHOR / VTP | 3 | 3 | 0.50 to 1.00 | -13.32 to -7.98 | -6.45 to -3.90 |

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
