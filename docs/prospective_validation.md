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
**84 jobs per chip**, 252 jobs on three chips, 1,024 shots, optimization level 3, transpiler seed 11 (identical
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

Expected cost: about 2 QPU-seconds per job on Fez, so roughly 3–5 QPU-minutes per chip
(10–15 for all three).

## Rules

- **Commit the frozen models and code first.** `predict` refuses to run with uncommitted
  tracked changes under `experiments/`, `scripts/` or `report/frozen_v1/models/`, and
  records the commit. New untracked files from `prepare` are expected.
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

## Chips: seen and unseen QPU

The same workload runs on three chips on the same day, as three collections:

| Chip | QPU | Models that predict it |
| --- | --- | --- |
| `ibm_fez` | seen (training data) | Fez model, pooled model |
| `ibm_kingston` | seen (training data) | Kingston model, pooled model |
| `ibm_marrakesh` | **unseen** (no training data) | pooled model, Fez model, Kingston model (all zero-shot) |

Seen and unseen QPU results are reported separately and never pooled. All three are
IBM Heron (156 qubits, CZ basis), so Marrakesh tests an unseen *chip*, not an unseen
*provider*. **Never add Marrakesh (or any validation) data to training before scoring.**

## Steps

Use one Bogotá date for all three chips. Run each block in order; every command is
separate on purpose (one failed path in a combined `git add` can leave files unstaged).

### A. Prepare all three chips (no QPU)

```sh
DATE=2026-11-16
python scripts/run.py ibm prepare --date $DATE --backend ibm_kingston --profile validation-v1
python scripts/run.py ibm prepare --date $DATE --backend ibm_fez --profile validation-v1
python scripts/run.py ibm prepare --date $DATE --backend ibm_marrakesh --profile validation-v1
```

### B. Pre-register all three (no QPU)

```sh
python -m experiments.qaqs_prospective predict --campaign kingston-validation-v1-$DATE
python -m experiments.qaqs_prospective predict --campaign fez-validation-v1-$DATE
python -m experiments.qaqs_prospective predict --campaign marrakesh-validation-v1-$DATE
git add report/frozen_v1/prospective/
git add experiments/*/plans/*validation-v1-d$DATE*
git add experiments/*/data/qpu/v2
git add experiments/data/quantum_specific_cache
git status --short            # must print nothing
git commit -m "data(validation): pre-register validation-v1 $DATE on kingston, fez, marrakesh"
git push                      # timestamps the pre-registration before any execution
```

`predict` refuses uncommitted tracked code or models, an existing predictions file, a
record that already has results, and any `new`/`extrapolation` label contradicted by
the compiled two-qubit-gate count (for Marrakesh, against Fez and Kingston combined).
If it refuses a label, stop and review; do not relabel after seeing compiled circuits.

### C. Submit all three without waiting (QPU)

`submit-only` offers every part to IBM, saves all job IDs and exits without waiting for
results. Do not cancel the Batches afterwards; they keep running with the laptop off.

```sh
CAMPAIGN_PROGRESS=1 python scripts/run.py ibm submit-only --date $DATE --backend ibm_marrakesh --profile validation-v1
CAMPAIGN_PROGRESS=1 python scripts/run.py ibm submit-only --date $DATE --backend ibm_fez --profile validation-v1
CAMPAIGN_PROGRESS=1 python scripts/run.py ibm submit-only --date $DATE --backend ibm_kingston --profile validation-v1
git add experiments/*/plans/*validation-v1-d$DATE*
git add experiments/*/data/qpu/v2
git commit -m "data(validation): submit validation-v1 $DATE on kingston, fez, marrakesh"
git push
```

Each `submit-only` must end with `84 distinct IBM job IDs saved`. If one stops with an
error, paste it before re-running anything: an interrupted send leaves a `submitting`
journal entry that has to be checked against IBM first.

### D. Later: recover, export, score

```sh
for B in ibm_kingston ibm_fez ibm_marrakesh; do
  python scripts/run.py ibm recover  --date $DATE --backend $B --profile validation-v1
  python scripts/run.py ibm complete --date $DATE --backend $B --profile validation-v1
done
python scripts/run.py export-ibm --out experiments/dataset_out
for C in kingston fez marrakesh; do
  python -m experiments.qaqs_prospective score \
    --predictions report/frozen_v1/prospective/$C-validation-v1-${DATE}_predictions.json
done
python -m experiments.qaqs_prospective summarize report/frozen_v1/prospective/*-validation-v1-${DATE}_scores.csv
```

`summarize` writes `validation-v1_summary.md` with seen and unseen QPU side by side.

Then refresh the dashboard's **Model validation** tab (the prospective results are its
headline; the **Model training** tab keeps the training-data validation for reference):

```sh
python dashboard/export_prospective.py     # writes dashboard/experiments/prospective/validation-v1.json
python scripts/run.py dashboard            # rebuilds public data; snapshots must match the export hash
```

## After scoring

- The validation export adds new campaigns to `experiments/dataset_out`. Training
  scripts read every campaign, so **do not retrain before scoring** — retraining would
  mix the validation data into the models being validated.
- After scoring, retraining on all data (including validation) gives the final thesis
  models; the frozen-model scores remain the reported prospective validation.
- The dashboard and decay snapshots are tied to the export hash; regenerate them after
  the new export as described in `docs/DECAY_ANALYSIS.md`.
