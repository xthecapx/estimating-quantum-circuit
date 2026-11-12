# Kingston collection: 2026-11-11 client failure and recovery

Collection: `kingston-full-oracle-growth-v1-2026-11-11`, 391 planned jobs,
1,024 shots per job, 42 manifest parts. This note describes a submission-client
incident; it is not a new scientific workload or additional repetition.

## Observed failure

The new dedicated environment installed Qiskit 2.6.2 and IBM Runtime 0.52.0.
Runtime 0.52 uses the client-side Executor sampler for its top-level SamplerV2
import. On SHOR-N15-A4-M4, samplomatic rejected RZ Pauli propagation while
building the gate-twirled program. The user traceback stops inside preparation,
before Executor is constructed or invoked. The exact exception was reproduced
offline using the frozen ISA circuit and runtime options without a service.

At interruption, 118 unique job IDs had been saved: 116 in 13 full parts and
two in Shor part 01. The third Shor attempt had no ID; its journal conservatively
said `submission_unknown`. The remaining workload consists of 273 unsent jobs.

## Reconciliation and compatibility fix

Only the proven pre-send failure was reclassified as `submission_rejected`, with
an evidence/timestamp annotation. Its manifest was marked `resume_ready`. The
two existing Shor IDs remain unchanged. Original files were backed up locally to
`/private/tmp/eqc-runtime-fix/state-before`; reconciliation hashes are in the
manifest. The backup is temporary machine-local recovery material.

The runner explicitly selects IBM's server-side SamplerV2 for gate-twirled
records when the installed default is the new Executor implementation. Frozen
circuits, runtime options (including Shor gate twirling and dynamical decoupling),
shots, references, and budgets remain unchanged. Non-twirled jobs continue to use
the installed default. This client/processing distinction must be retained when
interpreting the dataset: the first two Shor IDs used the client-side path;
subsequent Shor jobs use the server-side primitive. Per-attempt implementation
and package versions are now journaled for new submissions.

Explicitly reconciled parts validate artifact hashes, collection identity,
repetition indices and journal/manifest ID agreement before resuming. Saved
repetitions are skipped. Missing repetitions use a new Batch, and the original
Batch ID and job IDs remain in `previous_batches`. Usage reporting includes both
batches. Rejected attempts remain in the audit trail and do not count as QPU
executions; recovery requires their replacement job results. Unknown sends
continue to block automatic retries.

## Continue manually

From the repository root, with the dedicated environment active:

```sh
CAMPAIGN_PROGRESS=1 python scripts/run.py ibm submit-only \
  --date 2026-11-11 \
  --backend ibm_kingston \
  --profile full-oracle-growth
```

No `--max-batches` means offer all parts to IBM, subject to its admission limits.
The runner must finish with 391 distinct saved job IDs. No additional QPU jobs
were submitted while diagnosing, testing, or reconciling this failure.

Recover later using the same identity:

```sh
CAMPAIGN_PROGRESS=1 python scripts/run.py ibm recover \
  --date 2026-11-11 \
  --backend ibm_kingston \
  --profile full-oracle-growth
```

Offline verification: 96 lifecycle, scheduler, orchestration and resume tests
passed, including known-ID preservation, unknown-send rejection, replacement
recovery, and original/new Batch usage accounting.

IBM describes the new default in its
[Runtime 0.52 announcement](https://www.ibm.com/quantum/blog/dev-tools-qdc-2026).

## Recovery outcome: four terminal IBM failures

After all 391 job IDs were saved, recovery produced 387 result rows. Four
records have only their first repetition recovered. Read-only live queries
confirmed the following second-repetition jobs are in IBM's terminal `ERROR`
state with error 1217, `Session has been closed`:

| Configuration | Failed original job ID |
| --- | --- |
| BV2-ALT | dbqdr6fv5hds73dft7vg |
| BV2-SINGLE | dbqdr6fv5hds73dft810 |
| BV3-ONES | dbqdr6habdes73fo3l50 |
| BV3-ALT | dbqdr6mjjaos73ah4ij0 |

All four belong to Batch `1c000ad4-59a3-43c3-9394-d965e8e92972`.
IBM reports `max_time=600` and `active_timeout=600`, although the saved manifest
records `requested_batch_max_time_seconds=3600`. The Batch started at
2026-11-11 21:51:37.140 UTC and closed at 22:02:16.050 UTC. All four jobs have
`running=null` and failure timestamps immediately after that closure. This is
consistent with expiration of the effective Batch lifetime before those jobs
ran. The reason IBM's effective limit differs from the requested limit has
not been established; do not label it a confirmed client or service bug.

The collection therefore has 185 complete records, four incomplete records,
391 saved job IDs and 387 recovered job results. Repeating recovery does not
replace terminal failures. The strict completion check correctly refuses to
call this collection complete. Original IDs, successful results and failed
attempts remain preserved. No replacement QPU jobs were submitted during this
investigation. Any deliberate replacement must keep these failures and link
new job IDs explicitly; it must not overwrite the original attempt or silently
count as an additional independent repetition.

See IBM's [error registry](https://quantum.cloud.ibm.com/docs/en/errors) for 1217.

## Prepared four-job replacement campaign

Replacement identity: `kingston-full-oracle-growth-2026-11-11-bv-replacements-r1`.
The source collection date remains in the identity for linkage; actual preparation
and execution timestamps identify when replacements were collected. The plan is
`experiments/bv/plans/bv-kingston-full-oracle-growth-d2026-11-11-replacements-r1.json`.
It contains exactly BV2-ALT, BV2-SINGLE, BV3-ONES and BV3-ALT, one execution each,
1,024 shots each. Preparation uses fresh IBM calibration and transpiles anew at
optimization level 3 and seed 11; logical hashes, reference distributions and
runtime options were verified against the originals. Compiled layouts and
calibration can differ, and the new metadata retains those differences.

The reproducible preparation entry point is
`scripts/prepare_kingston_bv_replacements.py`. It never submits jobs. An existing
manifest is validated and reused without contacting IBM; conflicting plans are
rejected. Each new record's hashed `payload.replacement_of` identifies the original
campaign, source record/hash, failed job ID, and original zero-based run index 1.
The replacement's own run index is 0 within its separate one-run campaign.

From the activated thesis environment, submit the four-job manifest manually:

```sh
REPLACEMENT_MANIFEST=experiments/bv/plans/bv-kingston-full-oracle-growth-d2026-11-11-replacements-r1_manifest.json

CAMPAIGN_PROGRESS=1 python -m experiments.bv.bv_ibm \
  --submit-plan "$REPLACEMENT_MANIFEST" \
  --batch-max-time 3600
```

The lifetime is a request, not proof of IBM's effective limit. This replacement
has four jobs in one Batch; the original request/effective-limit discrepancy
remains unresolved. Submission records job IDs durably and refuses an already
submitted manifest. If interrupted, inspect the journal rather than resetting it.

Retrieve the replacement results later:

```sh
CAMPAIGN_PROGRESS=1 python -m experiments.bv.bv_ibm \
  --recover-plan "$REPLACEMENT_MANIFEST"
```

Rebuild the shared export only after recovery succeeds:

```sh
python scripts/run.py export-ibm --out experiments/dataset_out
```

The original campaign remains incomplete by design: its four failed attempts
are historical observations. For the completed scientific cohort, resolve those
four slots to their explicitly linked replacement jobs. Do not rewrite original
job IDs, present the collection as a single calibration window, or count failed
attempts as successful measurements. The combined recovered cohort can have 391
results once all four replacements complete; the full repository export also
contains earlier campaigns.
