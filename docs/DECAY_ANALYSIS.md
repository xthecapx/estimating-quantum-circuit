# Reproduce the dashboard decay analysis

The thesis repository contains the complete offline runner and its two local
analysis dependencies. Published QWARD 0.30.0 remains the core dependency; a
QWARD source checkout or new release is not required. No QPU is contacted.

## Files and ownership

- `experiments/scalability_regression.py`: table validation, cohort selection,
  provenance, decay entry point, and the existing optional regression analysis.
- `experiments/decay_relationships.py`: exact shared resource levels,
  within-period fitted profiles, and a bootstrap interval for every gap.
- `experiments/decay_groups.py`: descriptive complete-linkage grouping, the
  outcome each pair is read on, and the base rates by pair class.
- `tests/test_scalability_regression.py`: the offline safeguards for these modules.
- `docs/decay-migration.json`: original commit, source/destination file hashes,
  and namespace adaptation. Numerical analysis logic was copied unchanged.
- `report/{fez,kingston}/decay/`: generated CSVs, figures, report, grouping JSON,
  and `provenance.json` with input hashes, package versions, cohort counts and
  analysis-source hashes. These generated analyses are separate from the final
  thesis manuscript, which remains in QWARD for a later migration.
- `dashboard/experiments/decay/ibm_{fez,kingston,marrakesh}.json`: compact snapshots consumed
  by the dashboard. Include these with the matching exported tables in commits.

The source copies in QWARD remain available; this migration does not remove or
rewrite them. Future thesis analysis updates belong in this repository.

## Refresh the decay snapshots

Activate this repository's `.venv`. Existing NumPy, pandas, statsmodels and
Matplotlib dependencies are supplied by the installed published QWARD package.
From the repository root:

```sh
python scripts/run.py export-ibm --out experiments/dataset_out
python scripts/run.py decay --decay-only --backend ibm_fez --out report/fez
python scripts/run.py decay --decay-only --backend ibm_kingston --out report/kingston
python dashboard/export_decay.py report/fez/decay
python dashboard/export_decay.py report/kingston/decay
python scripts/run.py decay --decay-only --no-plots --backend ibm_marrakesh --campaign marrakesh-validation-v1-2026-11-16 --out report/marrakesh-validation
python dashboard/export_decay.py report/marrakesh-validation/decay
python scripts/run.py dashboard
```

`--backend` has no built-in default. Without it, the runner analyzes every chip
that has development jobs in the export and writes each to `--out/<backend>`.
The full reports, including the held-out regression study and the cross-chip
replication summary, come from the same command without `--decay-only`:

```sh
python scripts/run.py decay --backend ibm_fez --out report/fez
python scripts/run.py decay --backend ibm_kingston --out report/kingston --compare report/fez
```

`--compare` adds another chip's report directory to the replication summary and
refreshes that summary in both reports.

`python -m experiments.scalability_regression` is the equivalent direct entry
point. The default tables are `experiments/dataset_out`; `--tables PATH` can
select a complete alternative snapshot. `--campaign ID` can be repeated to
select an explicit cohort. `--no-plots` skips figures when only numerical
results are needed. `--group-tolerance` defaults to five target points.
`--bootstrap-draws` defaults to 1,000; 0 disables the gap intervals.

The table export includes all completed job results, including successful
repetitions from incomplete records. The analysis retains only the selected
backend and supported algorithms. The export contains 2,681 jobs. The
development cohort analyzed here is the 2,409 training-role jobs: 1,236 on Fez
and 1,173 on Kingston. Of the rest, 252 are validation jobs (84 on each of Fez,
Kingston and Marrakesh) and 20 belong to the exploratory Fez GHZ-to-BV transfer
window; both are analyzed only when named with `--campaign`
(see `campaign_role` in `experiments/ml_dataset.py`). Later runs should use their generated provenance counts instead of
assuming these values remain constant.

The dashboard validates the dataset manifest, every CSV part, and the references
table against each snapshot's hashes. A new export invalidates all three snapshots,
even when only one chip gained jobs. Regenerate all three before rebuilding. The
Pages workflow packages the committed snapshots; it does not fit decay models.

Marrakesh contributes its validation window to the descriptive All data counts wherever a pair shares enough levels. Chip columns and relationship rankings use the development reports. QAQS training continues to exclude validation campaigns.

## Braket development windows

Use the logical resource columns for cross-provider comparisons. Braket reports the submitted circuit; hardware-native depth and gate counts are unavailable. Run these commands from the repository root to regenerate the provider-specific decay snapshots from the recovered records.

```sh
python scripts/run.py braket export
python scripts/run.py decay --decay-only --no-plots --tables experiments/dataset_out/braket-repetitions-v1 --out report/braket-decay --metrics a.num_qubits a.depth a.size a.ComplexityMetrics.gate_based_metrics.two_qubit_count a.StructuralMetrics.volume a.BehavioralMetrics.program_communication a.quantum_specific.entanglement_ratio
python dashboard/export_decay.py report/braket-decay/Cepheus-1-108Q/decay
python dashboard/export_decay.py report/braket-decay/Forte-1/decay
python dashboard/build.py
```

Rigetti and IonQ have distinct campaign IDs and device reports. Compare decay fits algorithm pairs within a single device and window. Each snapshot is validated against the Braket CSV used to generate it.

## Interpretation and replacement jobs

Observed configurations have equal weight within algorithm/resource/period
means, preserving repetitions as measurements rather than independent circuit
configurations. Comparisons require at least three exact shared resource levels
within a period. Grouping uses the original minimum of two supported periods
and five-point tolerance; these are descriptive criteria, not proof of a common
physical noise law.

### What a pair in Compare decay means

The runner fits every observed algorithm pair on each chip. Family names
annotate the comparison after the pairs are enumerated. Within one campaign
window and one resource, each algorithm gets its own straight line through
its mean outcomes at the **same exact resource levels**. The outcome belongs
to the whole circuit. For success rate, a five-percentage-point fall means
five more shots per hundred missed that algorithm’s acceptance criterion.
These fits cannot isolate the contribution of a gate or subcircuit.

The loss gap in a window is
`100 × |slope A − slope B| × (largest − smallest shared level)`. Read every gap
with its interval. The reports give a 95% bootstrap interval for each window's
gap and for the median gap across windows, and the bootstrap probability that
the gap is at most the tolerance, `P(gap ≤ 5)`. An interval that straddles the
tolerance supports neither similar nor different decay.

**Bootstrap.** 1,000 draws. Jobs are resampled with replacement within each
configuration at each resource level, so the configurations and levels stay
fixed. Deviations of a resampled configuration mean are scaled by
`sqrt(n / (n − 1))` because most configurations have two or three jobs. This
is job resampling, not binomial shot resampling: it reflects job-to-job
variation, which includes shot noise. A configuration with one job contributes
no variation, so its interval is too narrow. The interval does not cover the
choice of configurations or the difference between windows; the per-window
gaps show that directly.

A window is a *point match* when both slopes are negative and the gap is at most
the tolerance. Two such windows, each with at least three shared levels, make a
repeated match. The dashboard still counts point matches. A point match with
`P(gap ≤ 5)` near one half is a coin toss, so the count is a summary of the
gaps, not a finding. The report’s complete-linkage clustering uses the *median*
absolute gap across eligible windows and also depends on the other algorithms
in a group.

**Outcome for Shor.** Pairs that involve Shor are read on chance-corrected
success, `f.fidelity.chance_corrected_success` = (success − chance) / (1 − chance),
floored at zero. Eight of the thirteen Shor configurations stay at their chance
floor, and that floor falls from 0.25 to 0.03 as counting qubits are added. Raw
Shor success therefore falls with width even where the circuit returns noise.
All other pairs are read on raw success. Two limits apply. The zero floor
raises the mean of configurations that scatter around chance. Ideal Shor
success is 0.5, so this score cannot reach one for Shor.

**Circuit construction.** The IBM QFT builder runs round trips or period
detection. Both use an inverse QFT. Phase estimation applies controlled
unitary powers followed by an inverse QFT on the counting register.
Shor order finding uses that phase-estimation construction with controlled
modular multiplication. The common transform decomposes into Hadamard and
controlled phase gates with qubit reordering. Shared logical operations can
compile differently on each chip.
[QFT builder](../experiments/qft/qft_ibm.py) · [Phase-estimation builder](../experiments/phase_estimation/pe_ibm.py) · [Shor builder](../experiments/shor/shor_ibm.py)

Grover and Bernstein–Vazirani share an oracle model. Grover marks bitstrings
by phase and applies diffusion. Bernstein–Vazirani queries a secret-dependent
CNOT network. Neither invokes the other. GHZ and vTP share entangling gates,
and vTP and random volumetric share an inverse-validation pattern. Those
relationships concern operations or protocols rather than an embedded algorithm.

**Examples from the committed fits.** Gaps are points on the outcome × 100
scale over the shared resource range, with 95% bootstrap intervals. Spearman ρ
ranks observed level means independently of the fitted loss.

| Pair and resource | Fez | Kingston |
| --- | --- | --- |
| QFT and phase estimation, logical two-qubit gates, success | Window gaps 31.01 [29.27, 32.73], 2.25 [0.10, 6.15] and 4.34 [1.08, 7.89]. Median 4.34 [1.66, 7.89], P(gap ≤ 5) = 0.58. The windows disagree by far more than any interval. | Window gaps 6.86 [4.78, 8.83], 6.61 [4.42, 8.62] and 5.28 [2.87, 7.62]. Median 6.61 [4.68, 7.90], P(gap ≤ 5) = 0.06, with ρ = 0.90 in every window. |
| Phase estimation and Shor, total logical qubits, chance-corrected success | One eligible window with four shared widths. Gap 40.09 [37.47, 42.68]. | Window gaps 22.77 [20.81, 24.87], 13.50 [11.66, 15.29] and 14.96 [5.25, 22.54]. Median 14.96 [12.13, 22.08], P(gap ≤ 5) = 0.00. |
| Grover and Bernstein–Vazirani, total logical qubits, success | Median 64.89 [63.76, 65.98] over 4 windows, with ρ = 1 in every window. | Median 56.16 [54.76, 57.71] over 3 windows. |

Phase estimation and Shor show why the outcome matters. On raw success the
three Kingston gaps are 4.86, 2.59 and 0.76, a median of 2.59 [1.31, 5.47],
and every window is a point match. That agreement comes from Shor's falling
chance floor. On chance-corrected success no window is within the tolerance on
either chip.

**Base rates.** A family pair agreeing is informative only if unrelated pairs
agree less often. Over every resource, on each pair's primary outcome:

| Chip | Pair class | Windows | Point matches | Mean P(match) | Cells | Repeated matches |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Fez | Family | 53 | 11 (20.8%) | 0.203 | 16 | 4 (25.0%) |
| Fez | Random-volumetric control | 46 | 3 (6.5%) | 0.078 | 16 | 0 (0.0%) |
| Fez | Unrelated | 131 | 14 (10.7%) | 0.113 | 42 | 4 (9.5%) |
| Kingston | Family | 54 | 10 (18.5%) | 0.181 | 18 | 3 (16.7%) |
| Kingston | Random-volumetric control | 51 | 8 (15.7%) | 0.156 | 17 | 2 (11.8%) |
| Kingston | Unrelated | 130 | 27 (20.8%) | 0.205 | 43 | 7 (16.3%) |

Family = QFT/PE, Grover/BV, vTP/GHZ, and QFT or PE with Shor. A cell is one
pair on one resource with at least two eligible windows. On Fez, family pairs
match about twice as often as unrelated pairs. On Kingston they match no more
often than unrelated pairs. These counts cover five family pairs on two chips
and carry no significance test. They do not show family-specific decay.
Each chip's `decay/report.md` and `decay/base_rates.csv` hold the current table.

The five shared logical two-qubit gate counts on both chips are 10, 16, 22,
30 and 48. At 22, the QFT side contains only the period-detection circuit
`SP5-P4`. Phase estimation contributes `PE-S5`, `PE-T5` and `PE-Z5`.
The period-4 controlled rotations encode the same quarter-cycle phase as the
S-gate case before inverse QFT decoding. At 16 and 48 the QFT side also
includes round trips. The fitted QFT line therefore combines different
circuit constructions as the gate count increases.
[QFT configurations](../experiments/qft/qft_configs.py) · [Phase-estimation configurations](../experiments/phase_estimation/pe_configs.py)

Neither chip has three gate-count levels also shared by
the random-volumetric control in one of those windows. Repeated agreement
describes the measured workloads. It leaves the cause of that agreement open.
[Fez fits and controls](../report/fez/decay/) · [Kingston fits and controls](../report/kingston/decay/)

The four successful BV replacements fill the original November 11 collection's
missing second repetitions. The exporter resolves their verified `replacement_of`
links into the original `meta.campaign_id`, `meta.window`, and `meta.run_index`.
Thus both the dashboard period picker and decay fits use one 391-result window
3, with two repetitions for each affected BV configuration. A replacement must
reference an unsuccessful original job with matching circuit/protocol metadata;
duplicate successful replacements are rejected.

Raw journals and frozen artifacts retain their acquisition campaign and actual
collection/calibration times. The export preserves that identity in
`g.source_campaign_id`, `g.source_window`, and `g.source_run_index`, and records
the failed job ID in `g.replaces_job_id`. New job IDs, run IDs, layouts and
execution timestamps remain those of the replacements. Grouping them into the
original collection is an explicit cohort decision; it does not claim a common
calibration or simultaneous execution. Original failures and links remain in
the [Kingston recovery note](kingston-2026-11-11-submission-recovery.md).

## Verify and publish

```sh
python -m pytest tests/test_scalability_regression.py -q
npm ci --prefix dashboard
npm run check --prefix dashboard
npm test --prefix dashboard
npm run build --prefix dashboard
```

Commit the migrated modules/tests/docs, matching `experiments/dataset_out/`,
generated `report/` outputs, and `dashboard/experiments/decay/` snapshots.
`dashboard/public/data/` and `dashboard/dist/` are ignored generated outputs.
Push to `main` to trigger website publication. For local preview, run
`npm run dev --prefix dashboard`.
