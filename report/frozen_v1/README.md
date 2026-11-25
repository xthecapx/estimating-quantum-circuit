# Frozen v1 models and prospective validation

Do not regenerate or edit anything in this directory.

- `models/`: the models frozen on 2026-11-16 (commit `7ea6cf6`), trained on the Fez and
  Kingston campaigns available that day, with the composite anchor (Shor) included.
- `prospective/`: predictions committed before the validation-v1 run (2026-11-16, Kingston,
  Fez, Marrakesh) and their scores.
- `cost/`: the execution-cost model frozen on 2026-11-17.

The prospective result is valid only for these exact artifacts. Models written to
`report/ml_estimation/models` by `python -m experiments.ml_estimation` are **v2**: a
different procedure, with no prospective score until a new pre-registered run.

`scripts/export_qaqs_models.py` and `dashboard/export_prospective.py` read from here.
