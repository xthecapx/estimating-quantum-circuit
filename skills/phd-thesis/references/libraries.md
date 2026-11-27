# Libraries and environment

## QWARD (`~/Documents/code/qiskit-qward`)

QWARD is the user's library. The thesis installs a **published** version pinned in `THESIS/pyproject.toml` (`qiskit-qward==0.30.0` at the snapshot). The sibling checkout is ahead of that version (`qward/VERSION.txt`). Check which version the code imports:

```sh
.venv/bin/python -c "import qward; print(qward.__version__, qward.__file__)"
```

| Module | Contents |
|---|---|
| `qward/scanner.py` | `Scanner`: runs several metric classes on a circuit and returns DataFrames |
| `qward/metrics/` | Pre-runtime: `qiskit_metrics`, `complexity_metrics`, `structural_metrics`, `behavioral_metrics`, `element_metrics`, `quantum_specific_metrics`. Post-runtime: `differential_success_rate` (DSR), `fidelity_metrics`, `histogram_assessment`, `output_screening`, `circuit_performance`. Hardware: `backend_calibration`, `gate_error_characterization`, `circuit_error_prediction` (M1/M2 baselines) |
| `qward/algorithms/` | Circuit factories: `ghz`, `bernstein_vazirani`, `grover`, `qft`, `phase_estimation`, `v_tp`, `random_volumetric`, `shor`, plus `executor`, `experiment` |
| `qward/schemas/` | Pydantic result schemas with `to_flat_dict()` |
| `qward/qaqs/` | Thesis inference: frozen models as JSON, NumPy only |
| `qward/examples/papers/` | Older paper experiments, plotting, and data (prior evidence only) |

The thesis repository's `experiments/<algo>/` adds its own `*_configs.py` and `*_ibm.py` on top of the QWARD factories. Success sets and references are defined there.

### `qward.qaqs`

```python
from qward.qaqs import predict, compute_footprint, available_models, model_card
result = predict(circuit, backend)        # a real IBM backend or FakeFez()
result.footprint                          # pre-runtime metrics
result.quality["ibm_fez/success"]         # prediction with its validation score
result.cost                               # billed QPU time and resource units
```

Models: Fez and Kingston quality models (circuit-only) and one cost model validated at 1,024 shots. The footprint is barrier-sensitive: every training circuit had a barrier, so `predict()` adds one if it is missing. The models are exported by `THESIS/scripts/export_qaqs_models.py` and parity-tested against sklearn and XGBoost. QWARD 1.0.0 is not released yet. The user releases it.

### Rules for QWARD

- Prefer QWARD-native APIs (`Scanner`, metric classes) over reimplementing metrics.
- Do not change QWARD's public API for a paper or analysis task unless the user asks. Paper repositories reference QWARD by recorded revision and source hashes (`qward_reference.json`, `provenance/source.json`).
- QWARD has its own `CLAUDE.md` and `AGENTS.md`. Follow them inside that repository.

## Other libraries

The QAQS pipeline uses pandas, NumPy, scikit-learn, XGBoost, LightGBM, and SHAP (see `THESIS/pyproject.toml` and `.venv`). Hardware access uses `qiskit-ibm-runtime` and Amazon Braket. The dashboard uses Node 22.12+, Svelte 5, Vite, ECharts 6, Zustand, Vitest, and Playwright. Papers use LaTeX with `latexmk`. The DSR and representational-analysis papers use the Springer Nature `sn-jnl` class.

## Environment setup

```sh
cd ~/Documents/code/estimating-quantum-circuit
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Python 3.11 or newer. The paper repositories record Python 3.13.3 and have their own `requirements.txt`.
