# Reproduce the dashboard decay analysis

The thesis repository contains the complete offline runner and its two local
analysis dependencies. Published QWARD 0.30.0 remains the core dependency; a
QWARD source checkout or new release is not required. No QPU is contacted.

## Files and ownership

- `experiments/scalability_regression.py`: table validation, cohort selection,
  provenance, decay entry point, and the existing optional regression analysis.
- `experiments/decay_relationships.py`: exact shared resource levels and
  within-period fitted profiles for related algorithms and controls.
- `experiments/decay_groups.py`: descriptive complete-linkage grouping.
- `tests/test_scalability_regression.py`: the original 20 offline safeguards.
- `docs/decay-migration.json`: original commit, source/destination file hashes,
  and namespace adaptation. Numerical analysis logic was copied unchanged.
- `report/{fez,kingston}/decay/`: generated CSVs, figures, report, grouping JSON,
  and `provenance.json` with input hashes, package versions, cohort counts and
  analysis-source hashes. These generated analyses are separate from the final
  thesis manuscript, which remains in QWARD for a later migration.
- `dashboard/experiments/decay/ibm_{fez,kingston}.json`: compact snapshots consumed
  by the dashboard. Include these with the matching exported tables in commits.

The source copies in QWARD remain available; this migration does not remove or
rewrite them. Future thesis analysis updates belong in this repository.

## Refresh both backends

Activate this repository's `.venv`. Existing NumPy, pandas, statsmodels and
Matplotlib dependencies are supplied by the installed published QWARD package.
From the repository root:

```sh
python scripts/run.py export-ibm --out experiments/dataset_out
python scripts/run.py decay --decay-only --backend ibm_fez --out report/fez
python scripts/run.py decay --decay-only --backend ibm_kingston --out report/kingston
python dashboard/export_decay.py report/fez/decay
python dashboard/export_decay.py report/kingston/decay
python scripts/run.py dashboard
```

`python -m experiments.scalability_regression` is the equivalent direct entry
point. The default tables are `experiments/dataset_out`; `--tables PATH` can
select a complete alternative snapshot. `--campaign ID` can be repeated to
select an explicit cohort. `--no-plots` skips figures when only numerical
results are needed. `--group-tolerance` defaults to five target points.

The table export includes all completed job results, including successful
repetitions from incomplete records. The analysis retains only the selected
backend and supported algorithms. The refreshed snapshot contains 2,409 jobs:
1,236 Fez jobs and 1,173 Kingston jobs. Later runs should use their generated
provenance counts instead of assuming these values remain constant.

The dashboard validates the dataset manifest, every CSV part, and the references
table against each snapshot's hashes. A new export invalidates both snapshots,
even when only one chip gained jobs. Regenerate both before rebuilding. The
Pages workflow packages the committed snapshots; it does not fit decay models.

## Interpretation and replacement jobs

Observed configurations have equal weight within algorithm/resource/period
means, preserving repetitions as measurements rather than independent circuit
configurations. Comparisons require at least three exact shared resource levels
within a period. Grouping uses the original minimum of two supported periods
and five-point tolerance; these are descriptive criteria, not proof of a common
physical noise law.

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
