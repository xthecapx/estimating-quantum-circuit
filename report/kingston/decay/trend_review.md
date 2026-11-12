# Comparing linear decay trends

Dots show the observed mean per shared resource level, with equal weight for each configuration. Lines are separate least-squares fits per workload and collection period. Each observed level has equal weight. The lines stop at the observed endpoints.

Profile ρ ranks the observed level means. Local ρ ranks the changes per unit between successive levels (at least three intervals). Slopes are target points on a ×100 scale per resource unit. For success these are percentage points. Ranges span eligible periods. Compare outcomes over the same configurations, levels and periods. Missing outcomes can change the support in future exports. All comparisons are exploratory.

| Target | Measurement | Available jobs |
| --- | --- | ---: |
| Success rate | Fraction of accepted shots | 1173 / 1173 |
| Adjusted success | Fraction of the chance-to-ideal success gap recovered | 1161 / 1173 |
| Hellinger fidelity | Squared overlap of measured and ideal outcome distributions | 1173 / 1173 |
| TVD similarity | One minus total variation distance from the ideal distribution | 1173 / 1173 |
| Differential success rate | Clipped Michelson contrast of mean expected probability against the strongest unexpected outcome | 1173 / 1173 |

For an ideal distribution concentrated on a single accepted bitstring, Hellinger fidelity and TVD similarity both equal success. Agreement across these scores can therefore reflect the same observation.

The Fez vTP configurations use specified one-qubit payload gates with inverse validation and two teleportation variants. RV uses random two-qubit layers and their inverses. Equal total width gives vTP three protocol qubits in addition to its payload. This comparison measures the two recorded workloads, including their different gates and success criteria.

- P1 = kingston-full-oracle-growth-v1-2026-11-09 / window 20261109
- P2 = kingston-full-oracle-growth-v1-2026-11-10 / window 20261110
- P3 = kingston-full-oracle-growth-v1-2026-11-11 / window 20261111

## QFT and Phase estimation

Do QFT and phase estimation share a trend as logical two-qubit gate count grows?

Resource measured: logical two-qubit gates.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 3 × 5 | -0.93 to -0.78 | -1.11 to -0.96 | 0.90 | -0.20 to 0.40 | Both decline in 3/3 periods | [plot](linear_trends/qft_phase-estimation_success.png) |
| Adjusted success | 3 × 5 | -0.87 to -0.58 | -1.01 to -0.82 | 0.70 to 0.90 | -0.40 to 0.80 | Both decline in 3/3 periods | [plot](linear_trends/qft_phase-estimation_normalized.png) |
| Hellinger fidelity | 3 × 5 | -1.35 to -1.08 | -1.18 to -0.91 | 0.90 to 1.00 | -0.80 to 0.00 | Both decline in 3/3 periods. Profile ρ vs success: 1 higher, 2 tied, 0 lower | [plot](linear_trends/qft_phase-estimation_hellinger_fidelity.png) |
| TVD similarity | 3 × 5 | -1.35 to -1.08 | -1.18 to -0.91 | 0.90 to 1.00 | -0.80 to 0.00 | Both decline in 3/3 periods. Profile ρ vs success: 1 higher, 2 tied, 0 lower | [plot](linear_trends/qft_phase-estimation_tvd_similarity.png) |
| Differential success rate | 3 × 5 | -1.69 to -0.98 | -1.04 to -0.91 | 0.80 to 0.90 | -0.60 to 0.40 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 2 tied, 1 lower | [plot](linear_trends/qft_phase-estimation_dsr.png) |

## vTP and Random volumetric

Does payload preparation and inverse validation around teleportation track a random mirror circuit at equal total width?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 3 × 5 | -6.12 to -2.97 | -10.42 to -5.52 | 0.60 to 0.70 | 0.20 to 0.80 | Both decline in 3/3 periods | [plot](linear_trends/vtp_random-volumetric_success.png) |
| Adjusted success | 3 × 5 | -5.13 to -0.40 | -9.96 to -5.05 | 0.10 to 0.60 | 0.20 to 0.80 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 1 tied, 2 lower | [plot](linear_trends/vtp_random-volumetric_normalized.png) |
| Hellinger fidelity | 3 × 5 | -6.12 to -2.96 | -10.42 to -5.52 | 0.60 to 0.70 | 0.20 to 0.80 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/vtp_random-volumetric_hellinger_fidelity.png) |
| TVD similarity | 3 × 5 | -6.07 to -2.96 | -10.42 to -5.52 | 0.60 to 0.70 | 0.20 to 0.80 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/vtp_random-volumetric_tvd_similarity.png) |
| Differential success rate | 3 × 5 | -3.95 to 2.29 | -1.41 to 1.93 | -0.30 to 0.60 | -0.40 to 0.20 | Both decline in 0/3 periods. Profile ρ vs success: 0 higher, 1 tied, 2 lower | [plot](linear_trends/vtp_random-volumetric_dsr.png) |

## Grover and BV

Do the two oracle workloads respond similarly to increasing width?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 3 × 3 | -33.26 to -27.94 | -4.86 to -1.84 | 0.87 to 1.00 | undefined | Both decline in 3/3 periods | [plot](linear_trends/grover_bernstein-vazirani_success.png) |
| Adjusted success | 3 × 3 | -36.02 to -30.37 | -4.55 to -1.35 | 0.50 to 1.00 | undefined | Both decline in 3/3 periods | [plot](linear_trends/grover_bernstein-vazirani_normalized.png) |
| Hellinger fidelity | 3 × 3 | -37.93 to -32.28 | -4.86 to -1.84 | 1.00 | undefined | Both decline in 3/3 periods. Profile ρ vs success: 1 higher, 2 tied, 0 lower | [plot](linear_trends/grover_bernstein-vazirani_hellinger_fidelity.png) |
| TVD similarity | 3 × 3 | -36.58 to -31.23 | -4.86 to -1.84 | 1.00 | undefined | Both decline in 3/3 periods. Profile ρ vs success: 1 higher, 2 tied, 0 lower | [plot](linear_trends/grover_bernstein-vazirani_tvd_similarity.png) |
| Differential success rate | 3 × 3 | -15.74 to -10.43 | -3.16 to 0.85 | -0.50 to 1.00 | undefined | Both decline in 2/3 periods. Profile ρ vs success: 0 higher, 1 tied, 2 lower | [plot](linear_trends/grover_bernstein-vazirani_dsr.png) |

## vTP and GHZ

Does vTP track GHZ state preparation as width increases?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 3 × 5 | -6.12 to -2.97 | -2.66 to -0.91 | 0.50 to 0.90 | -0.80 to 0.60 | Both decline in 3/3 periods | [plot](linear_trends/vtp_ghz_success.png) |
| Adjusted success | 3 × 5 | -5.13 to -0.40 | -2.56 to -0.58 | 0.40 to 0.70 | -0.80 to 0.60 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 1 tied, 2 lower | [plot](linear_trends/vtp_ghz_normalized.png) |
| Hellinger fidelity | 3 × 5 | -6.12 to -2.96 | -2.70 to -0.81 | 0.50 to 0.90 | -0.80 to 0.60 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/vtp_ghz_hellinger_fidelity.png) |
| TVD similarity | 3 × 5 | -6.07 to -2.96 | -2.66 to -0.70 | 0.50 to 0.90 | -0.80 to 0.60 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/vtp_ghz_tvd_similarity.png) |
| Differential success rate | 3 × 5 | -3.95 to 2.29 | -3.82 to 4.55 | -0.50 to 0.10 | 0.00 to 0.60 | Both decline in 0/3 periods. Profile ρ vs success: 0 higher, 0 tied, 3 lower | [plot](linear_trends/vtp_ghz_dsr.png) |

## QFT and Shor

Does QFT track Shor order finding, which uses an inverse QFT?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 3 × 4 | -6.40 to -4.26 | -10.36 to -8.37 | 0.60 | 0.50 | Both decline in 3/3 periods | [plot](linear_trends/qft_shor_success.png) |
| Adjusted success | 3 × 4 | -5.73 to -3.96 | -13.98 to -6.27 | 0.00 to 0.60 | -0.50 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 1 tied, 2 lower | [plot](linear_trends/qft_shor_normalized.png) |
| Hellinger fidelity | 3 × 4 | -10.70 to -8.10 | -21.34 to -17.12 | 0.80 | 0.50 | Both decline in 3/3 periods. Profile ρ vs success: 3 higher, 0 tied, 0 lower | [plot](linear_trends/qft_shor_hellinger_fidelity.png) |
| TVD similarity | 3 × 4 | -10.70 to -8.10 | -21.33 to -17.11 | 0.80 | 0.50 | Both decline in 3/3 periods. Profile ρ vs success: 3 higher, 0 tied, 0 lower | [plot](linear_trends/qft_shor_tvd_similarity.png) |
| Differential success rate | 3 × 4 | -18.51 to -9.46 | -0.07 to 0.02 | -0.40 to 0.11 | -0.50 to 0.50 | Both decline in 1/3 periods. Profile ρ vs success: 0 higher, 0 tied, 3 lower | [plot](linear_trends/qft_shor_dsr.png) |

## Phase estimation and Shor

Does phase estimation track Shor order finding at shared widths?

Resource measured: total logical qubits.

| Target | Periods × levels¹ | Slope A | Slope B | Profile ρ | Local ρ | Conclusion | Figure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Success rate | 3 × 4 | -10.10 to -9.00 | -10.36 to -8.37 | 1.00 | -1.00 to 0.50 | Both decline in 3/3 periods | [plot](linear_trends/phase-estimation_shor_success.png) |
| Adjusted success | 3 × 4 | -9.77 to -8.53 | -13.98 to -6.27 | 0.20 to 1.00 | -0.50 to 1.00 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 1 tied, 2 lower | [plot](linear_trends/phase-estimation_shor_normalized.png) |
| Hellinger fidelity | 3 × 4 | -10.36 to -9.14 | -21.34 to -17.12 | 1.00 | -1.00 to 0.50 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/phase-estimation_shor_hellinger_fidelity.png) |
| TVD similarity | 3 × 4 | -10.36 to -9.14 | -21.33 to -17.11 | 1.00 | -1.00 to 0.50 | Both decline in 3/3 periods. Profile ρ vs success: 0 higher, 3 tied, 0 lower | [plot](linear_trends/phase-estimation_shor_tvd_similarity.png) |
| Differential success rate | 3 × 4 | -10.82 to -9.39 | -0.07 to 0.02 | -0.40 to 0.32 | -1.00 to 0.50 | Both decline in 1/3 periods. Profile ρ vs success: 0 higher, 0 tied, 3 lower | [plot](linear_trends/phase-estimation_shor_dsr.png) |

¹ Number of eligible periods and distinct shared-level counts per period.

Machine-readable outputs: [review table](trend_review.csv) and [observations and fitted lines](linear_trends.json).
