# Estimating quantum circuit behavior

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24486377.svg)](https://doi.org/10.5281/zenodo.24486377)

How accurately can we predict a quantum circuit’s output quality and billed execution time before running it on hardware? This thesis repository brings together the circuits, hardware measurements, and prediction models used to study that question.

[Explore the dashboard](https://xthecapx.github.io/estimating-quantum-circuit/dashboard/) · [Browse the IBM data](experiments/dataset_out/) · [Read the model results](report/ml_estimation/report.md)

## Explore the data

The [IBM dataset](experiments/dataset_out/) contains 2,681 rows across eight circuit families, including GHZ, Bernstein–Vazirani, Grover, and Shor. To analyze it, read the numbered CSV files in [manifest order](experiments/dataset_out/dataset_manifest.json). Keep the parts, references, and calibrations from the same export together.

The [Amazon Braket export](experiments/dataset_out/braket-repetitions-v1/dataset.csv) adds 48 Rigetti Cepheus-1-108Q runs and 10 IonQ Forte-1 runs from development window 1. Select either device in the dashboard’s chip filter. Each provider has its own collection window and frozen circuit references.

| Research question | Where to look |
| --- | --- |
| What does each column measure? | [Dataset schema](docs/ibm_fez_dataset_schema.md) |
| Which circuits ran, and under which protocols? | [Experiment catalog](docs/EXPERIMENTS.md) |
| How does quality change as circuits grow? | [Decay analysis](docs/DECAY_ANALYSIS.md) |
| How well do predictions hold up on new hardware runs? | [Prospective validation](docs/prospective_validation.md) |
| What determines billed QPU time? | [Execution-cost model](docs/execution_cost.md) |

## Reproduce an IBM export

From the repository root, use Python 3.11 or newer. The project installs QWARD 0.30.0 for circuit definitions and metrics. The following commands rebuild the IBM tables from the checked-in measurements and check the campaign definitions. They require no cloud credentials.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/run.py export-ibm --out experiments/dataset_out
python -m pytest tests/test_campaign_matrix.py -q
```

To run the dashboard locally from the committed tables, follow the [dashboard quick start](dashboard/README.md#quick-start).

## Collect new measurements

- **IBM Quantum.** Choose a backend, date, and profile from the [experiment catalog](docs/EXPERIMENTS.md). Preview the workload offline, for example with `python scripts/run.py ibm validate --date 2026-11-10 --backend ibm_fez --profile full`. For a new collection, use a fresh campaign identity. For recovery, reuse the original identity and saved job IDs.
- **Rigetti and IonQ on Amazon Braket.** The [campaign notebook](notebooks/braket_campaign.ipynb) walks through setup, device availability, paid submission, and recovery. Use a single checkout for submissions and commit frozen predictions before prospective runs. For the standalone Rigetti comparison, follow the [pilot runbook](docs/aws_rigetti_pilot.md).

## Publish the website on GitHub Pages

The [Pages workflow](.github/workflows/dashboard.yml) builds the [research site](https://xthecapx.github.io/estimating-quantum-circuit/) and dashboard. To publish new measurements, commit the complete rebuilt export and push to `main` with **GitHub Actions** selected as the Pages source. Pull requests run the build checks.

## Agent skills

Repository-specific AI agent context lives under [`skills/`](skills/) (starting with [phd-thesis](skills/phd-thesis/SKILL.md)) and is registered via [`.agents/skills.json`](.agents/skills.json) for automatic discovery.

## Provenance and license

The [migration manifest](migration-manifest.json) records the original QWARD source paths and file hashes. For attribution and reuse, see the [project notices](NOTICE.md) and [license](LICENSE.txt).
