# validation-v1 on Kingston, collection `2026-11-17`: abandoned before execution

Collection `kingston-validation-v1-2026-11-17` (prepared and pre-registered on
2026-11-16, Bogotá) was abandoned before any job ran. It is kept as provenance and must
not be recovered, resumed, scored or exported. The prospective validation uses a fresh
collection under a new date instead; nothing from this attempt is resubmitted.

## What happened

The first `submit` used `--max-batches 3`, which waits for each Batch to finish before
opening the next. To send every part without waiting, the operator cancelled the open
Batches on IBM and restarted with a fresh collection (`submit-only`).

Six Batches had been opened. IBM reports every job in them as cancelled or failed with
error 1217 (session closed); none completed and no results exist.

| Part | Batch | Jobs on IBM |
| --- | --- | --- |
| GHZ | `c9c410a7-a783-41be-9c41-840317072d5c` | 8 cancelled |
| BV part 1 | `1bfa58e3-b365-41c7-9af6-01ed35342bdc` | 8 cancelled, 2 error 1217 |
| BV part 2 | `21a727e0-99e6-4741-b7ac-c76ad4a3fe1b` | 3 cancelled, 1 error 1217 |
| VTP | `1a1d420e-0c79-4983-bdee-b30abc381d48` | 6 cancelled |
| QFT part 1 | `98200957-7566-4490-9ff0-f983aaf510d5` | 10 cancelled |
| QFT part 2 | `e3b2f367-1ce7-4cc9-bf68-4b57b5fde235` | 4 cancelled, 3 error 1217 |

The journals hold 44 job IDs. One further job, `dbtmfp3rto6s73ft1nj0` (SP12-P8,
second repetition, cancelled), was accepted by IBM while its journal entry was still
`submitting`; it is recorded here because the journal has no ID for it. Grover, PE, RV
and Shor parts were never submitted.

## Status of the files

Plans, manifests, journals, prepared records and the pre-registered predictions file
(`report/ml_estimation/prospective/kingston-validation-v1-2026-11-17_predictions.json`)
are committed unchanged as they were when the Batches were cancelled. The journals were
not edited. Because `recover` was never run, the exporter produces no rows for this
collection.
