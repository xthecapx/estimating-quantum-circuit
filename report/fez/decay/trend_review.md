# Comparing linear decay trends

Dots show the observed mean per shared resource level, with equal weight for each configuration. Lines are separate least-squares fits per workload and collection period. Each observed level has equal weight. The lines stop at the observed endpoints.

Profile ρ ranks the observed level means. Local ρ ranks the changes per unit between successive levels (at least three intervals). Slopes are target points on a ×100 scale per resource unit. For success these are percentage points. Ranges span eligible periods. Compare outcomes over the same configurations, levels and periods. Missing outcomes can change the support in future exports. All comparisons are exploratory.

| Target | Measurement | Available jobs |
| --- | --- | ---: |
| Success rate | Fraction of accepted shots | 1236 / 1236 |
| Adjusted success | Fraction of the chance-to-ideal success gap recovered | 1222 / 1236 |
| Hellinger fidelity | Squared overlap of measured and ideal outcome distributions | 1236 / 1236 |
| TVD similarity | One minus total variation distance from the ideal distribution | 1236 / 1236 |
| Differential success rate | Clipped Michelson contrast of mean expected probability against the strongest unexpected outcome | 1236 / 1236 |

For an ideal distribution concentrated on a single accepted bitstring, Hellinger fidelity and TVD similarity both equal success. Agreement across these scores can therefore reflect the same observation.

The Fez vTP configurations use specified one-qubit payload gates with inverse validation and two teleportation variants. RV uses random two-qubit layers and their inverses. Equal total width gives vTP three protocol qubits in addition to its payload. This comparison measures the two recorded workloads, including their different gates and success criteria.

- P1 = fez-dataset-v2 / window 0
- P2 = fez-dataset-v2 / window 1
- P3 = fez-dataset-v2-2026-11-05 / window 20261105
- P4 = fez-dataset-v2-pilot-r2 / window 0
- P5 = fez-full-shor-growth-v1-2026-11-06 / window 20261106
- P6 = fez-oracle-growth-v1-2026-11-07 / window 20261107
- P7 = fez-oracle-growth-v1-2026-11-07-makeup / window 20261107
- P8 = fez-oracle-growth-v1-2026-11-07-standalone / window 20261108
- P9 = fez-shor-growth-v1-2026-11-05 / window 20261105

## QFT and Phase estimation

Do QFT and phase estimation share a trend as logical two-qubit gate count grows?

Resource measured: logical two-qubit gates.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 3 × 5 | -1.12 to -1.00 | -1.81 to -1.18 | 0.60 to 0.90 | -0.60 to 0.80 | Both decline in 3/3 periods | [plot](linear_trends/qft_phase-estimation_success.png) |
| Adjusted success | 3 × 5 | -1.04 to -0.88 | -1.73 to -0.99 | 0.70 to 0.90 | -0.60 to 0.60 | Both decline in 3/3 periods | [plot](linear_trends/qft_phase-estimation_normalized.png) |
| Hellinger fidelity | 3 × 5 | -1.56 to -1.33 | -1.81 to -0.97 | 0.70 to 1.00 | -0.60 to 0.40 | Both decline in 3/3 periods. Profile ρ vs success: 2 higher, 1 tied, 0 lower | [plot](linear_trends/qft_phase-estimation_hellinger_fidelity.png) |
| TVD similarity | 3 × 5 | -1.56 to -1.33 | -1.81 to -0.97 | 0.70 to 1.00 | -0.60 to 0.40 | Both decline in 3/3 periods. Profile ρ vs success: 2 higher, 1 tied, 0 lower | [plot](linear_trends/qft_phase-estimation_tvd_similarity.png) |
| Differential success rate | 3 × 5 | -1.77 to -1.36 | -1.86 to -0.70 | -0.10 to 0.90 | -0.40 to 0.80 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 2 tied, 1 lower | [plot](linear_trends/qft_phase-estimation_dsr.png) |

## vTP and Random volumetric

Does payload preparation and inverse validation around teleportation track a random mirror circuit at equal total width?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 3 × 5 | -10.55 to -3.50 | -13.89 to -11.65 | 0.10 to 0.90 | -0.40 to 0.80 | Both decline in 3/3 periods | [plot](linear_trends/vtp_random-volumetric_success.png) |
| Adjusted success | 3 × 5 | -8.67 to -0.75 | -13.24 to -11.08 | 0.10 to 1.00 | -0.40 to 1.00 | Both decline in 3/3 periods. Profile ρ vs success: 1 higher, 2 tied, 0 lower | [plot](linear_trends/vtp_random-volumetric_normalized.png) |
| Hellinger fidelity | 3 × 5 | -10.54 to -3.51 | -13.89 to -11.65 | 0.10 to 0.90 | -0.40 to 0.80 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/vtp_random-volumetric_hellinger_fidelity.png) |
| TVD similarity | 3 × 5 | -10.52 to -3.50 | -13.89 to -11.65 | 0.10 to 0.90 | -0.40 to 0.80 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/vtp_random-volumetric_tvd_similarity.png) |
| Differential success rate | 3 × 5 | -8.17 to 2.97 | -19.15 to -1.86 | -0.40 to 1.00 | -0.40 to 0.80 | Both decline in 2/3 periods. Profile ρ vs success: 1 higher, 0 tied, 2 lower | [plot](linear_trends/vtp_random-volumetric_dsr.png) |

## Grover and BV

Do the two oracle workloads respond similarly to increasing width?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 4 × 3 | -35.83 to -32.62 | -2.83 to -1.25 | 1.00 | undefined | Both decline in 4/4 periods | [plot](linear_trends/grover_bernstein-vazirani_success.png) |
| Adjusted success | 4 × 3 | -37.62 to -35.30 | -2.57 to -0.46 | 0.50 to 1.00 | undefined | Both decline in 4/4 periods | [plot](linear_trends/grover_bernstein-vazirani_normalized.png) |
| Hellinger fidelity | 4 × 3 | -41.36 to -37.96 | -2.83 to -1.25 | 1.00 | undefined | Both decline in 4/4 periods. Profile ρ vs success: 0 higher, 4 tied, 0 lower | [plot](linear_trends/grover_bernstein-vazirani_hellinger_fidelity.png) |
| TVD similarity | 4 × 3 | -39.04 to -36.46 | -2.83 to -1.25 | 1.00 | undefined | Both decline in 4/4 periods. Profile ρ vs success: 0 higher, 4 tied, 0 lower | [plot](linear_trends/grover_bernstein-vazirani_tvd_similarity.png) |
| Differential success rate | 4 × 3 | -39.08 to -16.03 | -1.02 to 1.24 | -1.00 to 1.00 | undefined | Both decline in 2/4 periods. Profile ρ vs success: 0 higher, 2 tied, 2 lower | [plot](linear_trends/grover_bernstein-vazirani_dsr.png) |

## vTP and GHZ

Does vTP track GHZ state preparation as width increases?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 3 × 5 | -10.55 to -3.50 | -1.98 to -1.41 | 0.20 to 1.00 | -0.40 to 0.00 | Both decline in 3/3 periods | [plot](linear_trends/vtp_ghz_success.png) |
| Adjusted success | 3 × 5 | -8.67 to -0.75 | -1.85 to -1.18 | 0.10 to 0.90 | -0.40 to 0.00 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 1 tied, 2 lower | [plot](linear_trends/vtp_ghz_normalized.png) |
| Hellinger fidelity | 3 × 5 | -10.54 to -3.51 | -1.99 to -1.44 | 0.20 to 1.00 | -0.40 to 0.00 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/vtp_ghz_hellinger_fidelity.png) |
| TVD similarity | 3 × 5 | -10.52 to -3.50 | -1.83 to -1.40 | 0.20 to 1.00 | -0.40 to 0.00 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/vtp_ghz_tvd_similarity.png) |
| Differential success rate | 3 × 5 | -8.17 to 2.97 | -0.39 to 0.37 | -0.10 to 0.60 | -0.20 to 0.40 | Both decline in 1/3 periods. Profile ρ vs success: 1 higher, 0 tied, 2 lower | [plot](linear_trends/vtp_ghz_dsr.png) |

## QFT and Shor

Does QFT track Shor order finding, which uses an inverse QFT?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 1 × 4 | -5.98 | -6.50 | 0.60 | -0.50 | Both decline in 1/1 periods | [plot](linear_trends/qft_shor_success.png) |
| Adjusted success | 1 × 4 | -4.16 | 0.80 | -0.20 | -1.00 | Both decline in 0/1 periods. Profile ρ vs success: 0 higher, 0 tied, 1 lower | [plot](linear_trends/qft_shor_normalized.png) |
| Hellinger fidelity | 1 × 4 | -12.05 | -14.11 | 0.80 | -0.50 | Both decline in 1/1 periods. Profile ρ vs success: 1 higher, 0 tied, 0 lower | [plot](linear_trends/qft_shor_hellinger_fidelity.png) |
| TVD similarity | 1 × 4 | -12.05 | -14.11 | 0.80 | -0.50 | Both decline in 1/1 periods. Profile ρ vs success: 1 higher, 0 tied, 0 lower | [plot](linear_trends/qft_shor_tvd_similarity.png) |
| Differential success rate | 1 × 4 | -7.74 | 0.08 | 0.32 | 1.00 | Both decline in 0/1 periods. Profile ρ vs success: 0 higher, 0 tied, 1 lower | [plot](linear_trends/qft_shor_dsr.png) |

## Phase estimation and Shor

Does phase estimation track Shor order finding at shared widths?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 1 × 4 | -13.42 | -6.50 | 1.00 | 1.00 | Both decline in 1/1 periods | [plot](linear_trends/phase-estimation_shor_success.png) |
| Adjusted success | 1 × 4 | -12.82 | 0.80 | -0.40 | 0.50 | Both decline in 0/1 periods. Profile ρ vs success: 0 higher, 0 tied, 1 lower | [plot](linear_trends/phase-estimation_shor_normalized.png) |
| Hellinger fidelity | 1 × 4 | -13.31 | -14.11 | 1.00 | 0.50 | Both decline in 1/1 periods. Profile ρ vs success: 0 higher, 1 tied, 0 lower | [plot](linear_trends/phase-estimation_shor_hellinger_fidelity.png) |
| TVD similarity | 1 × 4 | -13.31 | -14.11 | 1.00 | 0.50 | Both decline in 1/1 periods. Profile ρ vs success: 0 higher, 1 tied, 0 lower | [plot](linear_trends/phase-estimation_shor_tvd_similarity.png) |
| Differential success rate | 1 × 4 | -12.37 | 0.08 | -0.74 | -1.00 | Both decline in 0/1 periods. Profile ρ vs success: 0 higher, 0 tied, 1 lower | [plot](linear_trends/phase-estimation_shor_dsr.png) |

¹ Number of eligible periods and distinct shared-level counts per period.

Machine-readable outputs: [review table](trend_review.csv) and [observations and fitted lines](linear_trends.json).
