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
The same check can additionally prove preservation of the original dataset:

```sh
python scripts/verify_migration.py --source /absolute/path/to/qiskit-qward
```

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

QWARD retains its original dataset copy during this migration. New collections in
this repository do not automatically synchronize back. To refresh the QWARD-hosted
dashboard, copy a complete reviewed `experiments/dataset_out/` export into its
`qward/examples/papers/dataset_out/`, then run its `dashboard/build.py`. Copy files
without merging stale CSV parts; back up the previous complete export first.
A shared job/task ID denotes one observation even when stored in both repositories.
No original QWARD data will be removed until the migration is explicitly confirmed.

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
