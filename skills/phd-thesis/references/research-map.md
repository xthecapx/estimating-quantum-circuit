# Research map

Snapshot: 2026-11-26. Source of truth for the proposal: `THESIS/report/thesis/main.tex`, identical to `qiskit-qward/qward/examples/thesis.tex`. The committee's qualifying-exam comments are in `qiskit-qward/qward/examples/thesis_comments.md`, in Spanish. Two of them remain open: relate the work to cloud-computing proposals, and smooth the link from hypotheses to objectives to experiments.

## Research question

> To what extent can a compact set of pre-runtime metrics, the "circuit footprint," serve as a reliable predictor for the quality of quantum software across different algorithm paradigms, at different problem sizes, and across diverse quantum service providers?

## Objectives

- **O1.** Select the pre-runtime metrics that form the circuit footprint.
- **O2.** Train ML models that map the footprint to quality (DSR, HF, TVD) across providers.
- **O3.** Validate the models against new hardware executions of unseen configurations.
- **O4.** Determine whether paradigm circuits add predictive information beyond random volumetric circuits.

Hypotheses H1–H4 are in `SKILL.md`. Proposal threshold: R² ≥ 0.80, with MAE and RMSE minimized. Proposed model families: linear, decision tree, random forest, KNN, SVR, XGBoost, LightGBM. Inputs are compared in three configurations: circuit-only, hardware-only, and mixed.

## Prior work: what is already established

Cite these rather than re-deriving them. Each row states the claim the work supports, so a new paper can reference it instead of repeating it. DOIs here were checked against the bib files, `CITATION.cff`, README badges, or Crossref. Do not add a DOI you cannot trace to one of those, because a wrong DOI in a submitted paper is costly to fix.

| Work | Venue / status | Establishes | Identifier |
|---|---|---|---|
| Quality concerns when integrating quantum and classical computing: a systematic mapping study (Marquez, Ojeda, Garcés) | CIbSE 2025 poster | Research gap: quality attributes and metrics for hybrid systems; motivates the pre/post-runtime taxonomy | DOI 10.5753/cibse.2025.35330 |
| qWard: A Unified Toolkit for Pre- and Post-Runtime Quantum Circuit Metrics (Marquez Barrios, Garcés, Sierra-Sosa) | IEEE CHILECON 2025 | The metric tooling and its temporal classification | Paper DOI 10.1109/CHILECON66915.2025.11476435 (checked on Crossref; older bib files still say "forthcoming"). Software DOI 10.5281/zenodo.18773713, which is the v0.18.0 record, so cite the version actually used if Zenodo has one |
| A Teleportation Protocol Variant for Single-QPU Benchmarking (Márquez, Sierra-Sosa, Garcés) | IEEE Access vol. 13, pp. 209266–209281, 2025 | First evidence that pre-runtime structure (payload size, depth) correlates with success; IBM Sherbrooke and Rigetti Ankaa-3 | DOI 10.1109/ACCESS.2025.3639914; ieeexplore 11275619 |
| Dataset: Quantum Circuit Reliability on IBM Sherbrooke | IEEE DataPort 2025 | 292 vTP pilot jobs | DOI 10.21227/z95f-g888 |
| Dataset: QPU Measurement Histograms and Fidelity Metrics for Quantum Circuit Validation | IEEE DataPort 2026 | 1,281 jobs (Grover, QFT, vTP) on IBM and Rigetti | DOI 10.21227/b6jm-zd11 |
| Differential Success Rate (DSR): A Distribution-Aware Score for Validating Quantum Algorithm Outputs (Marquez, Sierra, Garcés) | **Under review** at EPJ Quantum Technology, no decision yet (confirmed by the user 2026-11-26). Cite it as "under review", never "accepted" or "in press". One line in `on-limitation-metrics/HANDOFF.md` says "accepted DSR manuscript"; that wording is wrong | DSR definition (Michelson contrast of mean expected peak vs strongest competitor), its comparison with HF and TVD, and histogram screening | Repo `dsr-quantum-validation`; no paper DOI; artifact DOI 10.5281/zenodo.22679268 |
| A Representational Analysis of Quantum Execution Success Measures | Draft for EPJ Quantum Technology; not public, no DOI | Classifies task success, distribution agreement, and peak dominance using representational measurement theory and GQM (reference classes R0–R4); histogram-only screening rule | Repo `on-limitation-metrics`, `draft.tex`. Cite only once it is public or submitted |
| Quantum Error Management in Practice: A Cross-Stack Benchmark (Sierra-Sosa, Garcia-Zapirain, Marquez, Garcés) | Co-authored manuscript (Springer template), no paper DOI | Error suppression and mitigation (Q-CTRL Fire Opal, Qedma QESEM) on ibm_pittsburgh. Not part of the QAQS hypotheses; cite only when mitigation matters as a confounder | Repo `~/Documents/code/Quantum_Benchmark_26`; dataset DOI 10.21227/z94n-8n82; code DOI 10.5281/zenodo.22695798 |
| This thesis repository (`estimating-quantum-circuit`) | Zenodo archive | Data and code availability for the new papers, not prior work | DOI 10.5281/zenodo.24486377 (README badge) |

Related drafts in `qiskit-qward/qward/examples/papers/`: `main.tex` and `main-springer.tex` (DSR, kept in sync with the artifact by `sync_paper.py`) and `main-dsr-profile.tex` (DSR evaluation profile, an alternative framing). Treat these as working copies. The artifact repository holds the version under review.

Co-supervised undergraduate theses that are cited as subproducts: Torres Bermejo (post-runtime visualizations), Baldion Castillo (pre-runtime metrics with Grover), and Rodríguez Castillo (scalability of circuits).

## What the new work adds

The regenerated dataset (see `data.md`) supports claims that earlier work did not make:

- A footprint selected inside cross-validation folds, with leak-free unseen-circuit validation.
- Prospective validation with predictions committed before the run, including an unseen QPU (Marrakesh).
- H2 scaling tests, using an analytical M2 prior plus a learned residual.
- H4 with a size-matched control.
- An execution-cost model for billed QPU time.
- The dashboard as the public presentation of findings.

## Papers still to write

These are undecided. The user will define one, two, or three papers after the dashboard is finished. When asked, propose a split based on which hypotheses have enough evidence, and state which ones are blocked by missing provider data (H3 cross-provider).
