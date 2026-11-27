# Rules

These rules come from the user. A repository's own `AGENTS.md`, `CLAUDE.md`, or `HANDOFF.md` adds to them for that repository.

## Scientific integrity

- **No leakage.** Validation and exploratory campaigns never enter training, footprint selection, tuning, or model choice. Select models inside folds, never on a holdout. `d.*` (execution-time hardware) is not a pre-runtime feature. `c.*` encodes circuit size, so do not call it "hardware-only".
- **Pre-registration.** Prospective predictions are committed before the run. Do not regenerate or overwrite committed predictions, and do not train on a validation campaign before it is scored.
- **Report failures.** Keep FAIL and INCONCLUSIVE verdicts, negative controls, incorrect candidates, and abandoned campaigns visible. Do not delete them to make results look stronger.
- **Intervals over point estimates.** Two overlapping intervals do not show equality. Compare regimes with paired differences on the same test jobs.
- **Old data is prior evidence only** (see `data.md`).

## No paid or remote execution without explicit request

Do not submit IBM, Rigetti, or IonQ jobs, or anything that spends QPU time or credits, unless the user asks for that specific run. Offline commands (`validate`, export, analysis, dashboard) are fine.

## Code and versions

- Until the user declares v1, there is no backward compatibility. Replace superseded models and code paths instead of keeping legacy or versioned copies; git history is the archive. This does not cover deleting evidence a claim rests on, such as pre-registered predictions: ask first.
- English for code, comments, filenames, reports, papers, and slides. Author-written Spanish prompts and frozen historical material may remain Spanish.
- Paper repositories: preserve the author's voice. Make local edits, avoid word1-word2 compounds and repeated "phrase: explanation" sentences, and do not add plots or expand the text unless asked.

## Git

- Work on `main`. Do not create branches.
- **Never `git push`.** Pushing publishes the dashboard through GitHub Pages. The user pushes.
- Commit only when the user allows it for the current task. Otherwise, give the staged paths and a ready-to-paste message. Use one `git add` per path group.
- Do not commit secrets (`.env`, credentials).
