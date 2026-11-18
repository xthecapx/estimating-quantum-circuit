# Estimating quantum circuit behavior

Thesis experiment protocols, recovered QPU measurements, and derived datasets for
studying quantum circuit behavior. This repository owns the collection code and
dataset. It uses **published `qiskit-qward==0.30.0`** for circuit algorithms,
metrics, schemas, and provider support. No local QWARD checkout is required.

## Repository map

| Path | Purpose |
| --- | --- |
| `experiments/*_campaign.py`, `campaign_*.py`, `*_experiment_base.py` | Thesis collection, durable submission/recovery, and frozen references |
| `experiments/{ghz,bv,vtp,qft,phase_estimation,grover,random_volumetric,shor}/` | Per-algorithm configs, runners, plans, records and circuit artifacts |
| `experiments/*/plans/` | Protocol selection and submission manifests; historical IDs preserved |
| `experiments/*/data/qpu/v2/` | Recovered IBM journals and `artifacts/` containing prepared JSON and QPY circuits |
| `experiments/data/aws_pilot/` | Convention for new local Rigetti run directories; no AWS pilot has been collected by this migration |
| `experiments/data/quantum_specific_cache/` | Copied deterministic metric cache |
| `experiments/dataset_out/` | Complete existing IBM export: **2018 rows**, numbered CSV parts, references, calibrations, schema and report |
| `experiments/qaqs_*.py`, `ml_*.py`, `footprint_analysis.py` | QAQS models: nested K-fold training, prospective validation, execution-cost model |
| `report/ml_estimation/` | Frozen models, per-target reports, `prospective/` (pre-registered predictions and scores) and `cost/` |
| `scripts/run.py` | Common collection/export/dashboard entry point |
| `dashboard/` | Optional local presentation of the IBM dataset |
| `docs/` | Protocol, schema and provider documentation |
| `tests/` | Offline regression checks for collection and exports |
| `migration-manifest.json` | Source commit, original/destination paths, byte counts and SHA-256 hashes |

Raw observations and derived tables are both included. The exported row count
is not a guarantee that all planned jobs completed, nor a final thesis inclusion
rule. Older raw/AWS formats, unrelated papers/notebooks, coin-toss results and
unlisted studies are outside the initial migration. Some auxiliary Python modules
are retained because algorithm package imports depend on them.

## Install

Python 3.11+ is required. From this repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[aws,torch,dev]'
python -c "import qward, importlib.metadata; print(importlib.metadata.version('qiskit-qward')); print(qward.__file__)"
```

For reading/exporting existing data without AWS or Torch computations, use
`python -m pip install -e '.[dev]'`. The experiment code lives under the
`experiments` namespace; `qward` must resolve to the installed public package,
not a neighboring checkout or a custom PYTHONPATH. Use `pip freeze` or a reviewed
lockfile to freeze the full analysis environment before final thesis results;
pinning QWARD alone does not pin all transitive dependencies. The complete
research data is intentionally kept in the Git repository, not in a Python wheel.

## First checks: no credentials or QPU usage

```sh
python scripts/verify_migration.py
python scripts/run.py ibm validate --date 2026-11-10 --backend ibm_fez --profile full
python scripts/run.py rigetti --help
python dashboard/build.py --tables experiments/dataset_out --data-out dashboard/public/data
```

`verify_migration.py` checks the retained migrated files. Intentional post-migration
removals and test adaptations are recorded in the manifest, preserving original
hashes for provenance. Source changes made after
migration will be reported as changes, not silently accepted. This baseline is a
migration record; keep subsequent scientific updates in new commits/snapshots.
It does not hash files newly created for this repository, such as this README.
For a pre-cleanup QWARD checkout restored from the recovery bundle, the same
check can additionally compare the original dataset. The current cleaned QWARD
checkout no longer contains those files:

```sh
python scripts/verify_migration.py --source /absolute/path/to/qiskit-qward
```

## Plan and collect on Amazon Braket

Clone the repository and open the [Rigetti and IonQ notebook](notebooks/braket_campaign.ipynb).
Section 1 installs the pinned experiment stack and checks the active kernel. The
notebook and `python scripts/run.py braket` use the same Python campaign code.
The 108 Rigetti tasks and 14 IonQ tasks cost an estimated $195.60 in QPU charges.
If a device reports `PAUSED` or `OFFLINE`, the notebook displays its status and
submits the selected tasks on the available device. Leave the submission cell
running to recheck every minute, or interrupt and resume from the same checkout.

From the repository root, these offline commands inspect the schedule and
rebuild the AWS dataset after pulling the professor’s recovered records:

```sh
python scripts/run.py braket plan
python scripts/run.py braket export
```

| Files to commit | Repository location |
|---|---|
| Manifest, prediction template and frozen predictions | `experiments/data/braket-repetitions-v1/` |
| Prepared circuits, task journals, raw results and device snapshots | `experiments/<algorithm>/data/qpu/aws/braket-repetitions-v1/<task>/` |
| Derived table, one row per recovered task | `experiments/dataset_out/braket-repetitions-v1/dataset.csv` |

### One SR8 chip-metadata test

Run this command from the repository root with the name of an existing Braket
results bucket in **us-east-1**. It submits one eight-qubit QFT round trip to
IonQ Forte-1 at 100 shots ($8.30 on demand), prints its ARN, waits, and recovers
the data. While Forte-1 is `PAUSED` or `OFFLINE`, keep the terminal open. The command checks
again every minute and submits once preflight sees `ONLINE` and passes the other
device checks. Omitting `--submit` prepares and simulates the circuit offline.

```sh
.venv/bin/python scripts/run.py braket ionq-chip-pilot --bucket YOUR_US_EAST_1_BUCKET --submit
```

The record is `experiments/data/aws_pilot/ionq-sr8-r1/`. Repeating the command
in that checkout resumes the same task. Commit the directory to share the result.
The two `profile_at_*.json` files contain the full Braket device responses.
`task_metadata.json`, `raw_result.json` and `result.json` contain the job metadata,
provider output, decoded histogram and quality targets. `chip_inventory.json`
identifies which device and calibration fields the service actually exposed,
alongside the earlier Rigetti BV3-ALT pilot and archived IBM SR8 examples.
Compare logical SR8 outcomes against IBM with the shot counts shown; the Rigetti
pilot supplies a device-metadata reference from a different circuit.

This independent pilot uses $8.30 of the shared $200 QPU budget. Before a later
full collection, reduce its $195.60 schedule by at least $3.91 (or by $4.64
including the earlier $0.7352 Rigetti pilot). Omitting one $8.30 IonQ task would
cover the pilot.

### Scheduled IonQ training check

To check live IonQ submission and recovery first, run the scheduled six-qubit
QFT round trip (`SR6`) on Forte-1 with 100 shots. Supply an existing Braket
result bucket in **us-east-1**. The ideal output is `011001`. The command
submits one $8.30 task and waits for the result. Omit `--submit` for offline
preparation. Rerun the same command in the same checkout after an interruption.

```sh
python scripts/run.py braket ionq-check --bucket YOUR_US_EAST_1_BUCKET --submit
```

Commit and push the recovered
`experiments/qft/data/qpu/aws/braket-repetitions-v1/ionq-1-SR6-r1/`
directory before the professor prepares the full campaign. With that record in
the clone, the workflow uses its measurements as one of the 14 IonQ tasks.

Section 8 gives the Git commands for checkpointing. Commit and push the frozen
predictions before submitting prospective validation. Pull the latest checkpoint
before continuing in another checkout. Only one checkout should submit paid tasks
for a campaign. Rebuilding the CSV requires the tracked records and local Python
environment.

## Collect on IBM

Choose a backend/date/profile explicitly; first inspect the bounded workload.
The `full` profile resolves to `full-oracle-growth` (391 planned jobs). Other
current profiles are `oracle-growth` (68) and `shor-growth` (39).

```sh
python scripts/run.py ibm validate --date YYYY-MM-DD --backend ibm_fez --profile full
python scripts/run.py ibm plan --date YYYY-MM-DD --backend ibm_fez --profile full
python scripts/run.py ibm prepare --date YYYY-MM-DD --backend ibm_fez --profile full
python scripts/run.py ibm submit --date YYYY-MM-DD --backend ibm_fez --profile full --max-batches 3
python scripts/run.py ibm recover --date YYYY-MM-DD --backend ibm_fez --profile full
python scripts/run.py ibm complete --date YYYY-MM-DD --backend ibm_fez --profile full
```

Replace the date placeholder. Preparation reads calibration but submits no jobs;
`submit` and the combined `run` mode consume QPU allocation. Recovery uses saved
IDs and never creates replacement jobs. Use the original identity when recovering;
use a fresh identity for a deliberate new collection. Existing plans/manifests
are provenance and must not be overwritten. Imported manifests may contain the
original machine's absolute paths; the lifecycle rebases supported historical
record paths against their local plan directories.

Supply IBM credentials through the normal environment/.env configuration:
`IBM_QUANTUM_TOKEN`, `IBM_QUANTUM_INSTANCE`, optionally `IBM_QUANTUM_CHANNEL`.
Credentials are not included. Leave `CAMPAIGN_CHECKPOINT` unset unless explicitly
using the driver's automatic git commit/push behavior.

For the original Fez pilot/window protocol, use
`python scripts/run.py ibm-windows status` and the documented prepare/submit/recover
commands in `experiments/run_campaign.sh`. That legacy shell driver uses `uv`.
Window 0 and dated full campaigns are different protocols; see
[the experiment catalog](docs/EXPERIMENTS.md).

## Collect the first Rigetti comparison

```sh
python scripts/run.py rigetti prepare --out experiments/data/aws_pilot/bv3-alt-r1 --bucket YOUR_BRAKET_BUCKET
python scripts/run.py rigetti preflight --record experiments/data/aws_pilot/bv3-alt-r1
python scripts/run.py rigetti submit --record experiments/data/aws_pilot/bv3-alt-r1
python scripts/run.py rigetti recover --record experiments/data/aws_pilot/bv3-alt-r1
python scripts/run.py rigetti export --record experiments/data/aws_pilot/bv3-alt-r1
```

Default: one BV3-ALT task, 1,024 shots on Cepheus-1-108Q. Only `submit` creates the
paid task. Preparation is offline; preflight reads AWS identity, device profile,
and existing result-bucket configuration. Use an existing us-west-1 bucket and
normal boto3 credentials (`--profile` is supported on AWS commands). The frozen
request, task ARN, raw result, compiled-program metadata, reference distribution,
and evaluation remain in the run directory. Never delete a journal to retry an
uncertain submission; use the [Rigetti runbook](docs/aws_rigetti_pilot.md).
AWS comparison exports currently have their own schema and are separate from
the IBM dashboard inputs. Unsupported VTP/Shor AWS studies remain deferred.

## Rebuild the dataset and dashboard

```sh
python scripts/run.py export-ibm --out experiments/dataset_out
python scripts/run.py decay --decay-only --backend ibm_fez --out report/fez
python scripts/run.py decay --decay-only --backend ibm_kingston --out report/kingston
python dashboard/export_decay.py report/fez/decay
python dashboard/export_decay.py report/kingston/decay
python scripts/run.py dashboard
npm ci --prefix dashboard
npm run dev --prefix dashboard
```

The exporter reads copied local records; it requires no cloud access. Omit
`--backend` to include all IBM backends, or supply it for a deliberate device
subset. The historical `ibm-windows export` shortcut filters to Fez.
Keep **all files from one export together**: `dataset-*.csv`,
`dataset_manifest.json`, `references.csv`, `calibrations.csv`, `schema.json`, and
`export_report.json`. Do not combine parts from different exports. Building from
the existing tables uses only Python's standard library. See
[dashboard setup](dashboard/README.md) for Node requirements and production build.
See [the decay runbook](docs/DECAY_ANALYSIS.md) for report provenance, matching
periods, replacement jobs, and refreshing both chip snapshots after an export.

This repository is the authoritative home for the migrated experiments, dataset,
and dashboard. QWARD's current branches no longer contain the migrated files;
its cleanup commit is `789e6575aaa62b1b39b522c7852db8a888c68e32`. Existing QWARD
release tags were deliberately preserved and still expose historical snapshots.
The manuscript/report and its assets remain in QWARD pending a later migration.
Publish new measurements through this repository's export and Pages workflow;
there is no longer a second current dashboard dataset to synchronize back.

`migration-manifest.json` describes the initial migration and its original source
hashes. Its original commit/file references are historical provenance, not paths
that must exist in the cleaned QWARD checkout. Duplicate historical job/task IDs
still denote the same observations, not independent samples.

## Publish the website on GitHub Pages

The workflow `.github/workflows/dashboard.yml` validates the committed export,
generates dashboard JSON, runs Svelte/TypeScript checks and unit tests, and builds
the static site. One Pages deployment publishes these paths:

- Research home: https://xthecapx.github.io/estimating-quantum-circuit/
- Dashboard: https://xthecapx.github.io/estimating-quantum-circuit/dashboard/
- Presentations: https://xthecapx.github.io/estimating-quantum-circuit/slides/

To enable the first publication:

1. Commit and push the repository, including the workflow and complete dataset export.
2. In GitHub **Settings → Pages → Build and deployment**, select **GitHub Actions** as the source.
3. Push dashboard/export changes to `main`, or run **Website checks and Pages publication** from the Actions tab on `main`.

Pull requests run the build checks without publishing. Manual runs on other
branches also build without publishing. Relevant pushes watch `dashboard/**`, `site/**`,
`experiments/dataset_out/**`, and the workflow itself. New raw records must first
be exported and the complete export committed; raw-record changes alone do not
publish new measurements. No QWARD installation or QPU credentials are needed
for publication. The `_site/` artifact combines `site/` with the built dashboard
at `_site/dashboard/`; raw records, account metadata,
and the repository's experiment source are not part of the Pages artifact.

The frontend uses relative asset/data URLs, so the same build works at the
repository URL and in local preview. The existing QWARD-hosted dashboard has its
own deployment and remains available during migration. This workflow publishes
only this repository's site. If the `github-pages` environment has required
reviewers, its deployment follows those repository rules.

### Add slides or another page

Put ready-to-publish HTML, PDF, images, and other static assets under `site/`.
For a deck at `/estimating-quantum-circuit/slides/defense/`, add
`site/slides/defense/index.html` and its assets, then link it from
`site/slides/index.html`. That index currently contains an unpublished-content
placeholder; no slides were copied automatically. Add other pages in the same
way, for example `site/methods/index.html`, and link them from `site/index.html`.
Use relative links so pages work under the repository prefix. Reserve
`/dashboard/` for the generated application; keep its source under `dashboard/`.
The workflow publishes the assembled site together, so adding pages will not
replace the dashboard or deploy a second Pages site.

To preview the exact site layout after building dashboard data and running
`npm run build --prefix dashboard`:

```sh
mkdir -p _site/dashboard
cp -R site/. _site/
cp -R dashboard/dist/. _site/dashboard/
touch _site/.nojekyll
python3 -m http.server 8790 --directory _site
# Home: http://localhost:8790/
# Dashboard: http://localhost:8790/dashboard/
# Slides: http://localhost:8790/slides/
```

`_site/` is generated and ignored by Git. Start with a fresh `_site/` directory
when rebuilding after deleting or renaming pages, to avoid retaining old files.

## Quality and cost models (QAQS)

The thesis predicts a circuit's execution quality (success rate, Hellinger fidelity, TVD, DSR) and
its billed QPU cost from the circuit alone, before running it.

```sh
python -m experiments.ml_estimation              # nested repeated grouped K-fold: unseen-circuit validation
python -m experiments.qaqs_prospective predict --campaign kingston-validation-v1-2026-11-16   # pre-register
python -m experiments.qaqs_prospective score --predictions report/ml_estimation/prospective/<campaign>_predictions.json
python -m experiments.qaqs_cost                  # billed-time model (1 RU = 1 minute of QPU time)
python dashboard/export_prospective.py           # dashboard snapshot of the prospective results
```

* **Three validation tests**, defined in [`docs/prospective_validation.md`](docs/prospective_validation.md):
  unseen-circuit validation (grouped K-fold), calibration-cycle validation (forward temporal
  holdout) and prospective validation (frozen models on a new IBM run: Fez, Kingston and the
  never-seen Marrakesh, predictions committed before execution).
* **Execution cost:** [`docs/execution_cost.md`](docs/execution_cost.md).
* **Dashboard:** *Model validation*, *Execution cost* and *Model training* tabs show these results;
  the validation tab is the headline and the training tab is kept for reference.
* **Using the models:** they ship in QWARD as `qward.qaqs` (`predict(circuit, backend)`), as plain
  JSON that runs on NumPy. `python scripts/export_qaqs_models.py --qward ../qiskit-qward`
  regenerates those files and the parity fixtures from the frozen models here. The usage guide is
  in the QWARD repository (`docs/qaqs.md`).
* Training reads the export without any `-validation-v` campaign, so validation data can never
  reach training; only the scoring code and the cost model opt in.

## Reproduce or extend the thesis

```sh
python -m pytest tests/test_aws_campaign.py tests/test_campaign_matrix.py -q
```

These tests are offline. Additional copied IBM/export tests use local fake backends
and provide more detailed lifecycle checks. Final analysis must record the selected
campaign IDs/job IDs, backend/date, shots, circuit hashes, metric schema, software
versions, references/success criteria, calibration coverage, exclusions and failed
jobs. Preserve repetitions separately. The manuscript/model-training/final report
pipeline is future work; this repository already holds the collection and dataset
contribution, not an automatically generated final thesis.

The source and initial data provenance are in `migration-manifest.json` and
[NOTICE.md](NOTICE.md). Identifiers, calibration metadata and historical absolute
paths are retained in raw provenance; review those before public publication.
The copied software retains QWARD's license and notices.
