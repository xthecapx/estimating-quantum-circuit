# Experiment catalog and ownership

This catalog distinguishes the thesis collection protocols from older paper
experiments. Commands below are launcher targets: `python scripts/run.py TARGET ...`.
Counts identify workload versions, not numbers of successfully recovered jobs.
Review generated plans whenever the workload changes.

| Experiment family | Entry point and configuration | Identity and outputs | Use |
| --- | --- | --- | --- |
| Current IBM collection | `ibm`; `scripts/ibm_campaign_ci.py`; `--profile full` | Backend + date + resolved profile; algorithm `plans/*-dDATE*.json`, `data/qpu/v2/` | Current full protocol; `full` resolves to `full-oracle-growth`, 391 planned jobs |
| Oracle growth | `ibm --profile oracle-growth` | Same dated identity, Grover/BV subset | 68 jobs; investigate oracle/width growth |
| Shor growth | `ibm --profile shor-growth` | Same dated identity, Shor subset | 39 jobs; growth/degradation study |
| Original Fez pilot/main windows | `ibm-windows`; `campaign_matrix.py`, per-algorithm `plans/*-w*.json` | `fez-dataset-v2`, windows 0 and 1–3; separate `0-rN` pilot repeats | Original pilot: 15 configs × 2 executions = 30 tasks; do not confuse with dated full profiles |
| Historical dated IBM profiles | `legacy-full`, `full-shor-growth`, `full-oracle-growth` | Preserve original profile identity for recovery | Compatibility/recovery; inspect existing manifests before choosing |
| Kingston BV failure replacements | `scripts/prepare_kingston_bv_replacements.py`; per-algorithm `--submit-plan` / `--recover-plan` | `kingston-full-oracle-growth-2026-11-11-bv-replacements-r1`; frozen `payload.replacement_of` | Exactly four jobs replacing terminal error-1217 second repetitions; see [recovery note](kingston-2026-11-11-submission-recovery.md) |
| Rigetti comparison pilot | `rigetti`; `aws_campaign.py`, `aws_pilot_data.py`; same supported window-0 configs | Unique run UUID; entire caller-selected directory, convention `experiments/data/aws_pilot/CONFIG-rN/` | First milestone: BV3-ALT, 1,024 shots, one task; separate CSV comparison export |

IBM algorithms: GHZ, Bernstein–Vazirani, VTP, QFT, phase estimation, Grover,
random volumetric, and Shor. Rigetti initially supports the pilot configurations
for BV, GHZ, QFT, phase estimation, Grover, and RV. VTP and Shor are deferred on
that path. Both providers reuse IBM circuit factories and shared target metrics;
compiled layouts, calibrations and compiler behavior differ.

## Files by responsibility

| Responsibility | Implementation |
| --- | --- |
| Human entry point and portable handoff | `scripts/run.py`, `README.md` |
| Dated IBM orchestration | `scripts/ibm_campaign_ci.py` (local collection) |
| Original IBM window selection/driver | `experiments/campaign_matrix.py`, `run_campaign.sh` |
| IBM immutable records, jobs, batches, resume | `ibm_campaign.py`, `campaign_parts.py`, `campaign_submit.py`, `ibm_experiment_base.py` |
| AWS pilot preparation, submission, recovery | `aws_campaign.py`, `aws_pilot_data.py` |
| Algorithm definitions and success/reference rules | Each algorithm directory's `*_configs.py`, `*_ibm.py`, plus the installed QWARD algorithms |
| Shared measurements and feature groups | `dataset_features.py`, `experiment_helpers.py`, installed QWARD metrics and schemas |
| IBM training tables and calibration export | `dataset_export.py`, `calibration_tables.py` |
| Dashboard projection | `dashboard/build.py`, then `dashboard/src/` |

Paths in the lower rows are relative to `experiments/` unless otherwise
specified. Keep the portable namespace intact for now: moving a provider runner
alone leaves its factories, config registries, metric calculators and relative
record paths behind.

## Existing studies outside the default collection

The original QWARD repository also contains legacy `*_aws.py`/`*_ibm.py` direct-run modes,
`run_aws_experiments.sh`, `run_ibm_experiments.sh`, `run_opt3*`, signal/background
BV studies, BV calibration-prediction studies, enrichment scripts, older
`data/qpu/raw` and `data/qpu/aws` results, notebooks, and manuscript-specific plots.
They are not automatically the new thesis collection protocol or inputs to the
v2 dashboard. Some auxiliary algorithm Python modules are copied for import
compatibility; their presence in a snapshot does not select their experiments.

Promote a study into the thesis by adding its scientific purpose, config/plan,
command, provider, output path, metric/reference definitions, and inclusion rule
to this catalog before including its results. The original QWARD thesis-dataset plan
and older paper plans are historical design notes; use prepared metadata and this
catalog to identify what actually ran. The previous `on-limitations` repository
was mentioned as a precedent but is not present here, so no files from it are
claimed to be included.

## Data identity for the thesis

Keep the original job/task and run IDs when copying results. One raw job may appear
in both the thesis snapshot and the dashboard; that is one observation with two
copies, not two independent samples. Join on IDs, retain repetitions separately,
and report backend, execution/calibration observation times, shots, logical circuit
hash, transpiler/compiler policy, accepted outcome set, reference distribution,
and available hardware fields. Separate pilot validation from final analysis via
explicit campaign/run selection; the exporter includes all completed local records
unless filtered. Do not infer a final thesis cohort from directory presence alone.
