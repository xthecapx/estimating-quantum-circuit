# QAQS prospective validation run (`validation-v1`)

Prospective validation scores the frozen QAQS models on executions that did not exist
when they were trained. It is the third of the three validation tests used in the
thesis:

| Test | Question | Method |
| --- | --- | --- |
| Unseen-circuit validation | Does QAQS predict circuits it has never seen? | Repeated grouped K-fold by circuit configuration |
| Calibration-cycle validation | Does QAQS predict a later calibration cycle? | Forward temporal holdout |
| **Prospective validation** | Does QAQS predict a run that did not exist at training time? | Frozen models on a new IBM run; predictions committed before results |

## Workload

Defined in `experiments/validation_profile.py`: 42 configurations × 2 repetitions =
**84 jobs per chip**, 1,024 shots, optimization level 3, transpiler seed 11 (identical
to every training collection). Each configuration belongs to one pre-registered group:

| Group | Configs | Purpose |
| --- | ---: | --- |
| `anchor` | 20 | Already in the training data, low/mid/high size per algorithm. New calibration cycle, known circuits: calibration drift. |
| `new` | 13 | Never executed, compiled two-qubit gates within the measured range of their algorithm: H1 on unseen circuits under a new calibration cycle. |
| `extrapolation` | 9 | More compiled two-qubit gates than any measured configuration of their algorithm: H2 scaling. |

New configuration definitions (all tagged `validation-v1` in their descriptions):
BV `PAIR`/`HALF`/`EDGE` secrets, QFT round-trip inputs `IV3`–`IV7`, and RV seed-7
circuits. Extrapolation uses previously defined but never-run sizes: GHZ18/20,
PE-T9/S9/Z10, QFT SR10/SP12-P8, RV7-D14/RV9-D9. Wider BV was dropped: on Heron it
does not compile to more two-qubit gates than BV14-ONES, so it cannot test extrapolation.

Expected cost: about 2 QPU-seconds per job on Fez, so roughly 3–5 QPU-minutes per chip.

## Rules

- **Commit the frozen models and code first.** `predict` refuses to run with uncommitted
  changes under `experiments/` or `report/ml_estimation/models/`, and records the commit.
- **Predictions are committed before `submit`.** `predict` refuses to overwrite an
  existing predictions file and refuses records that already have results.
- **Scoring re-hashes everything.** `score` fails if any prepared record or frozen model
  changed after pre-registration.
- **Pre-registered criteria** (in `experiments/qaqs_prospective.py`, `CRITERIA`):
  H1 uses the `new` group with circuit-only models; pass needs the R² 95% CI lower bound
  ≥ 0.80, fail if the whole CI is below 0.80, otherwise inconclusive. `anchor` MAE is
  compared with the unseen-circuit validation MAE (no threshold). `extrapolation` is
  reported as measured.
- Same durable-submission rules as every other IBM collection: never delete a journal to
  retry, recover with the same identity, never create replacement jobs automatically.

## Steps (per chip; replace the date and backend)

Use the Bogotá collection date. The run below uses `2026-11-17` and `ibm_kingston`.

```sh
DATE=2026-11-17; BACKEND=ibm_kingston; CHIP=kingston

# 1. Offline checks: no credentials, no QPU.
python scripts/run.py ibm validate --date $DATE --backend $BACKEND --profile validation-v1
python scripts/run.py ibm plan     --date $DATE --backend $BACKEND --profile validation-v1

# 2. Prepare: reads calibration and transpiles, submits nothing.
python scripts/run.py ibm prepare  --date $DATE --backend $BACKEND --profile validation-v1

# 3. Pre-register predictions (no QPU). Fails if code/models are uncommitted, or if a
#    'new'/'extrapolation' label contradicts the compiled two-qubit-gate counts.
python -m experiments.qaqs_prospective predict --campaign $CHIP-validation-v1-$DATE

# 4. Commit the plans, prepared records and predictions BEFORE submitting.
git add experiments/*/plans/*validation-v1* experiments/*/data/qpu/v2 \
        experiments/data/quantum_specific_cache report/ml_estimation/prospective
git commit -m "data(validation): pre-register $CHIP validation-v1 $DATE"

# 5. Submit (uses QPU allocation), then recover later with the same identity.
python scripts/run.py ibm submit   --date $DATE --backend $BACKEND --profile validation-v1 --max-batches 3
python scripts/run.py ibm recover  --date $DATE --backend $BACKEND --profile validation-v1
python scripts/run.py ibm complete --date $DATE --backend $BACKEND --profile validation-v1

# 6. Export and score.
python scripts/run.py export-ibm --out experiments/dataset_out
python -m experiments.qaqs_prospective score \
  --predictions report/ml_estimation/prospective/$CHIP-validation-v1-${DATE}_predictions.json
```

Step 3 writes `report/ml_estimation/prospective/<campaign>_predictions.json`. Step 6
writes `<campaign>_scores.csv` and `<campaign>_report.md` next to it.

If `predict` reports a group-label contradiction (possible if IBM recompiles a circuit
differently from the offline dry run), do not edit the labels after seeing the
compiled circuits: stop and review the configuration with the thesis advisor first, and
record the decision.

## After scoring

- The validation export adds new campaigns to `experiments/dataset_out`. Training
  scripts read every campaign, so **do not retrain before scoring** — retraining would
  mix the validation data into the models being validated.
- After scoring, retraining on all data (including validation) gives the final thesis
  models; the frozen-model scores remain the reported prospective validation.
- The dashboard and decay snapshots are tied to the export hash; regenerate them after
  the new export as described in `docs/DECAY_ANALYSIS.md`.
