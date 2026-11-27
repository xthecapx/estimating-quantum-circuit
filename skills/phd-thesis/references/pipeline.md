# Pipeline commands

Run from `THESIS` root with the repository's `.venv` activated (`source .venv/bin/activate`). `scripts/run.py TARGET ...` sets `PYTHONPATH`. Commands marked **QPU** spend paid hardware time or need credentials. **Never run them unless the user asks explicitly for that run.**

## Collect (QPU)

| Step | Command |
|---|---|
| Preview the workload offline | `python scripts/run.py ibm validate --date YYYY-MM-DD --backend ibm_fez --profile full` |
| Prepare, submit, recover (**QPU**) | `python scripts/run.py ibm {prepare,submit-only,recover,complete} --date D --backend B --profile P` |
| Braket (Rigetti, IonQ) (**QPU**) | `notebooks/braket_campaign.ipynb`, `python scripts/run.py rigetti ...`; runbook `docs/aws_rigetti_pilot.md` |

Profiles and their identities are in `docs/EXPERIMENTS.md`. A new collection needs a fresh campaign identity. A recovery reuses the original identity and saved job IDs. For prospective runs, commit the frozen predictions **before** submitting.

## Export (offline)

```sh
python scripts/run.py export-ibm --out experiments/dataset_out
python -m pytest tests/test_campaign_matrix.py tests/test_dataset_export.py -q
```

Then review `experiments/dataset_out/export_report.json`.

## Analyse (offline)

| Purpose | Command | Output |
|---|---|---|
| QAQS quality models (H1–H4) | `python -m experiments.ml_estimation` | `report/ml_estimation/report.md`, CSVs, models, dashboard estimation snapshots |
| Model comparison | `python -m experiments.qaqs_compare` | `report/ml_estimation/model_comparison.md` |
| Execution-cost model | `python -m experiments.qaqs_cost` | `report/ml_estimation/cost/`, dashboard cost snapshot |
| Decay per chip | `python scripts/run.py decay --decay-only --backend ibm_fez --out report/fez` (also Kingston and Marrakesh, see `dashboard/README.md`) | `report/<chip>/decay/` |
| Prospective predict (before the run) | `python -m experiments.qaqs_prospective predict --campaign <chip>-validation-v1-DATE` | `report/ml_estimation/prospective/*_predictions.json` |
| Prospective score (after recovery) | `python -m experiments.qaqs_prospective score ...` then `summarize` | `*_scores.csv`, `*_report.md` |
| Export models to QWARD | `python scripts/export_qaqs_models.py` | Pickle-free JSON for `qward.qaqs` |

Main modules in `experiments/`: `ml_dataset.py` (loading, roles), `qaqs_kfold.py` (nested repeated grouped K-fold, `VALIDATION_NAMES`), `qaqs_models.py`, `qaqs_report.py`, `footprint_analysis.py`, `scalability_regression.py` and `decay_*.py` (decay), `qaqs_cost.py`, `qaqs_prospective.py`.

## Evaluation design (do not weaken)

- Default split: repeated grouped K-fold by configuration (5 folds × 3 repeats, folds shared across chips). Footprint selection, tuning, and model choice happen **inside** each training fold.
- Intervals: 95% cluster bootstrap that resamples configurations. H1 PASS requires the whole interval to be at or above 0.80. Otherwise the verdict is INCONCLUSIVE, or FAIL when the interval lies below.
- Every footprint score is reported against a size baseline (two-qubit gates, depth, width, measurements) and a repeat ceiling.
- Shor is excluded from raw targets because it sits at chance level. `success_adj` scores all jobs.
- Final models are frozen on 100% of training-role data.

## Validation names

Use these in all user-facing text, code labels, and papers. Avoid "grouped CV" and "temporal holdout".

| Name | Meaning |
|---|---|
| Unseen-circuit validation | Repeated grouped K-fold by circuit configuration |
| Calibration-cycle validation | Train on earlier windows, test on the latest (forward temporal) |
| Prospective validation | Frozen models on a new IBM run, predictions committed first. Groups: `anchor`, `new`, `extrapolation` |

Runbooks: `docs/prospective_validation.md`, `docs/execution_cost.md`, `docs/DECAY_ANALYSIS.md`.
