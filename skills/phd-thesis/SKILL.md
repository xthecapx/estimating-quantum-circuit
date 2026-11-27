---
name: phd-thesis
description: Research context for Cristian Marquez's PhD thesis on QAQS (Quality-Aware Quantum Software), which predicts a quantum circuit's execution quality and billed cost from pre-runtime metrics. Covers the hypotheses H1–H4, prior papers (CIbSE mapping study, qWard/CHILECON, vTP/IEEE Access, DSR, representational analysis), the sibling repositories, the regenerated latest-chip IBM dataset and how to load it, the QWARD library, the QAQS model pipeline, and the dashboard. Use whenever a task touches the thesis, its data, its dashboard, QWARD metrics used by the thesis, or writing that draws on earlier thesis work. Use it even when the user names only a piece, such as "the footprint", "DSR", "Kingston data", "validation-v1", or "the Findings tab".
---

# PhD thesis: QAQS

This skill is the entry point for any session working on the thesis. It is written for any coding agent (Claude Code, Codex, Antigravity), so it uses plain paths and shell commands only.

## Thesis in one paragraph

**Pre-runtime Structural Analysis for Quantum Software Quality** (Universidad de los Andes, PhD; advisor Kelly Garcés, co-advisor Daniel Sierra-Sosa, Catholic University of America). The central question is whether a compact *circuit footprint* of pre-runtime metrics, computed by QWARD on the transpiled circuit, predicts execution quality (success rate, DSR, Hellinger fidelity, TVD) on real QPUs. A second model predicts billed QPU time. The framework is **QAQS**, and the methodology follows Fenton & Bieman's Goal-Based Measurement Framework with GQM.

| ID | Hypothesis | How it is tested now |
|---|---|---|
| H1 | The footprint predicts execution quality | Unseen-circuit validation; PASS requires the whole 95% CI to be at or above R² 0.80 |
| H2 | Models generalize to unseen configurations in the same paradigm | Scaling extrapolation, leave-algorithm-out, prospective `extrapolation` group |
| H3 | One footprint model transfers across providers | Circuit-only vs calibration-only vs mixed; cross-chip zero-shot; cross-provider waits for data |
| H4 | Paradigm circuits add signal beyond random-volumetric circuits | RV-only vs paradigm-only vs combined, with size-matched control and paired differences |

Paradigms: Fourier (QFT, phase estimation), Oracle (Grover, Bernstein–Vazirani), Entanglement (vTP, GHZ). Random volumetric is the H4 control. Shor is included for growth studies.

## Where things are

All repositories are siblings under `~/Documents/code/`. In this skill, `THESIS` means `estimating-quantum-circuit/`, the repository this skill lives in.

| Repository | Role | Read first |
|---|---|---|
| `estimating-quantum-circuit` | **Active.** Current data collection, regenerated dataset, QAQS models, reports, dashboard | `README.md`, `docs/EXPERIMENTS.md` |
| `qiskit-qward` | QWARD library: metrics, algorithms, `qward.qaqs` inference. Holds older paper data | `CLAUDE.md`, `AGENTS.md` |
| `dsr-quantum-validation` | DSR paper artifact (Zenodo 0.1.0); paper under review at EPJ Quantum Technology | `README.md`, `KNOWN_ISSUES.md` |
| `on-limitation-metrics` | Representational-analysis paper on success measures (EPJ QT target) | `HANDOFF.md`, `AGENTS.md`, `EXPERIMENTS.md` |
| `Quantum_Benchmark_26` | Co-authored cross-stack error-management benchmark (Sierra-Sosa et al.); outside the QAQS hypotheses | `main.tex` |

Load references on demand:

- `references/research-map.md`: hypotheses, objectives, publications with DOIs, and the evidence each one already establishes. Read before writing anything that cites earlier work.
- `references/data.md`: the dataset, column groups, campaign roles, joins, and the rule for old data. Read before any data analysis.
- `references/pipeline.md`: commands to collect, export, model, validate, and score cost, and the validation names to use.
- `references/dashboard.md`: dashboard tabs, build flow, data snapshots, and checks.
- `references/libraries.md`: QWARD modules, the `qward.qaqs` inference API, and environment setup.
- `references/rules.md`: integrity and workflow rules. **Read it before changing data, models, or git state.**

## Live state, not remembered state

Numbers in these references are a snapshot dated in each file. Before quoting a count or score, regenerate it:

```sh
cd ~/Documents/code/estimating-quantum-circuit
.venv/bin/python skills/phd-thesis/scripts/data_summary.py   # jobs per chip/algorithm/campaign/role
sed -n 1,40p report/ml_estimation/report.md                   # current model verdicts
git log --oneline -10                                         # what changed recently
```

The report and dashboard snapshots are regenerated from the export, so they win over this skill when they disagree. Note the disagreement and update the reference file.

## Default workflow

1. Identify which repository owns the task, using the table above. Read that repository's own `AGENTS.md`, `CLAUDE.md`, or `HANDOFF.md`, which override this skill on local conventions.
2. For data or model work, read `references/data.md` and `references/rules.md`, then run `data_summary.py`.
3. For writing, read `references/research-map.md`. Use the thesis validation names: *unseen-circuit validation*, *calibration-cycle validation*, *prospective validation*.
4. Report results with their scope (chip, campaign role, target, validation type) and their interval, not as bare point estimates. Repeated runs of one configuration are not independent, so resample configurations rather than jobs.
5. Publication status matters in writing: the DSR paper is under review with no decision, and the representational-analysis paper is an unpublished draft. Never call either accepted or published.

## Install and maintain

The canonical copy is `estimating-quantum-circuit/skills/phd-thesis/`. Run `sh skills/phd-thesis/scripts/install.sh` to symlink it into `~/.claude/skills`, `~/.codex/skills`, and `~/.gemini/config/skills` (Antigravity). Any other agent can read this file directly. When a fact changes (new chip, provider, campaign, verdict, paper status), update the matching reference file and its snapshot date in the same change.

## Current status (snapshot 2026-11-26)

- The data is IBM only: Fez and Kingston for training, plus Marrakesh as an unseen QPU in prospective validation. Rigetti (Braket) and IonQ have one pilot task each under `experiments/data/aws_pilot/`.
- H1: Kingston passes on Hellinger and TVD; Fez and pooled are inconclusive; DSR fails everywhere. Prospective `new` group: R² of about 0.93–0.94 for per-chip models.
- H2: Plain extrapolation fails. An M2 analytical prior plus a learned residual partly recovers Fourier and Oracle scaling, but not Entanglement.
- H3: Device calibration alone does not predict quality. The circuit footprint transfers zero-shot between IBM chips. Cross-provider validation is WAITING FOR DATA.
- H4: Paradigm circuits add a large gain over RV-only. At matched training size, no difference is shown.
- Papers for H1–H4 are not yet defined. The user will decide on one, two, or three papers after the dashboard is finished. Do not start a paper scaffold unless asked.
