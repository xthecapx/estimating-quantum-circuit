# Dashboard

The dashboard is the tool for presenting findings. It is a static Svelte 5 + TypeScript + Vite site with ECharts, published by GitHub Pages at https://xthecapx.github.io/estimating-quantum-circuit/dashboard/ when the user pushes to `main`. The full guide is `THESIS/dashboard/README.md`.

## Sections (`dashboard/src/lib/state/dashboard.ts`)

| Group | Tab id | Label | Data |
|---|---|---|---|
| Summary | `findings` | Findings | Landing page with headline results |
| Experiment plots | `range` | Operating range | Jobs, histograms, calibration explorer (`views/range`, `views/job`, `views/calibration`) |
| Experiment plots | `decay` | Compare decay | `dashboard/experiments/decay/*.json` |
| Prediction models | `footprint` | Footprint | Estimation snapshots |
| Prediction models | `validation` | Model validation | `experiments/prospective/`, `experiments/comparison/` |
| Prediction models | `estimation` | Model training | `experiments/estimation/{ibm_fez,ibm_kingston,pooled}.json` |
| Prediction models | `cost` | Execution cost model | `experiments/cost/cost-v1.json` |

## Data flow

```
experiments/dataset_out/  --dashboard/build.py-->  dashboard/public/data/*.json  (generated, ignored)
report/...                --export_*.py / ml_estimation / qaqs_cost-->  dashboard/experiments/*.json  (committed, hash-stamped)
```

Snapshots carry the input export hash. `build.py` includes a snapshot only when its hash matches the current export. After a re-export, regenerate the snapshots or check them with `scripts/restamp_snapshots.py`.

To change a data shape, edit three places together: `build.py`, `src/lib/data/types.ts`, and `SCHEMA_VERSION` (in both).

## Code rules

- Calculations live in `src/lib/domain` and `src/lib/stats`, with unit tests. Components only display.
- Heavy and publication statistics are computed in Python at build time, so the page matches the thesis numbers. The browser computes only interactive values.
- Shared state belongs in the dashboard store. View state lives in the URL hash (`lib/state/url.ts`).
- Charts go through `EChart.svelte`. Register new chart types in `lib/charts/echarts.ts`.

## Run and check

```sh
npm ci --prefix dashboard
python3 dashboard/build.py
npm run dev --prefix dashboard           # http://localhost:5173
cd dashboard && npm run check && npm test && npm run build && npm run e2e
```

None of these need QPU credentials. CI (`.github/workflows/dashboard.yml`) runs `build.py`, `check`, `test`, and `build`, but **not** `e2e`, so run the Playwright flows locally before the user pushes. A broken browser flow would otherwise reach GitHub Pages.

## Before adding a panel or tab

- Most results are already in the snapshots. For example, `dashboard/experiments/estimation/<scope>.json` holds `targets.<target>.h2[]` with `variant` = `footprint`, `m2_only`, `m2_residual`. Read the snapshot and its TypeScript type (`src/views/<view>/model.ts`) before proposing a Python change. A missing field in the type is a front-end change, not a schema change.
- Prefer extending an existing view (for example `estView=h2_h4` in Model training) over a new tab, so shared links keep working. A new tab goes in `sectionGroups` in `lib/state/dashboard.ts`.
- Check the Findings page (`views/findings/`) for claims the new panel would contradict, and update both together.
- Show intervals, coverage, and n. Do not imply that one variant beats another unless a paired difference on the same jobs supports it.
