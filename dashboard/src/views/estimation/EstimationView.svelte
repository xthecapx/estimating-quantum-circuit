<script lang="ts">
  import EChart from "../../lib/charts/EChart.svelte";
  import Select from "../../lib/ui/Select.svelte";
  import { palette } from "../../lib/charts/echarts";
  import type { Explorer } from "../../lib/state/explorer.svelte";
  import {
    ALGO_COLORS,
    ALGO_SHORT,
    SCOPE_LABELS,
    SPLIT_LABELS,
    VALIDATION,
    sortTargetsByScore,
    targetScore,
    TARGET_LABELS,
    VIEW_LABELS,
    fmt,
    footprintChart,
    leaderboardChart,
    pickSplit,
    regimeBarChart,
    scatterChart,
    type EstimationSnapshot,
  } from "./model";

  export interface EstimationChoices {
    scope: string;
    target: string;
    split: string;
    view: string;
  }

  let {
    explorer,
    reports,
    choices,
    onchange,
  }: {
    explorer: Explorer;
    reports: Record<string, string>;
    choices: EstimationChoices;
    onchange: (v: EstimationChoices) => void;
  } = $props();

  let data = $state<EstimationSnapshot>();
  let error = $state("");

  const availableScopes = $derived.by(() => {
    const keys = Object.keys(reports);
    const ordered = ["pooled", ...explorer.backends].filter((k) => keys.includes(k));
    const extras = keys.filter((k) => !ordered.includes(k)).sort();
    return [...ordered, ...extras];
  });

  const activeScope = $derived(
    availableScopes.includes(choices.scope) ? choices.scope : (availableScopes[0] ?? explorer.backend),
  );

  $effect(() => {
    const scope = activeScope;
    const filename = reports[scope];
    const controller = new AbortController();
    data = undefined;
    error = "";
    if (filename) {
      fetch(new URL("data/" + filename, document.baseURI), { signal: controller.signal })
        .then(async (r) => {
          if (!r.ok) throw Error("fetch");
          const s: EstimationSnapshot = await r.json();
          if (s.schemaVersion !== 1 || s.backend !== scope || !s.targets) throw Error("schema");
          if (!controller.signal.aborted) data = s;
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            error = "The estimation results could not be loaded. Reload to try again.";
          }
        });
    }
    return () => controller.abort();
  });

  const hasHoldout = $derived(Boolean(data && data.holdoutJobs > 0));
  const targetKeys = $derived(
    data ? sortTargetsByScore(data.targets, choices.split === "cv" || !hasHoldout ? "cv" : "holdout") : [],
  );
  const targetKey = $derived(
    targetKeys.includes(choices.target) ? choices.target : (targetKeys[0] ?? ""),
  );
  const report = $derived(data?.targets[targetKey]);
  const split = $derived<"holdout" | "cv">(
    choices.split === "cv" || (data && data.holdoutJobs === 0) ? "cv" : "holdout",
  );
  const viewMode = $derived(
    choices.view in VIEW_LABELS ? choices.view : "h1",
  );

  const combinedLeaderboard = $derived(
    report ? [...report.leaderboard, ...report.baselines] : [],
  );
  const topMlRow = $derived(report?.leaderboard[0]);
  const temporal = $derived(report?.h3.temporal ?? null);
  const topMetrics = $derived(topMlRow ? pickSplit(topMlRow, split) : undefined);

  const algoPointsLegend = $derived.by(() => {
    if (!report) return [];
    const seen = new Set(report.points.map((p) => p.algorithm));
    return Object.keys(ALGO_SHORT).filter((a) => seen.has(a));
  });

  const h3ChartItems = $derived(
    (report?.h3.regimes ?? []).map((r, i) => ({
      label: r.label.replace("Mixed · ", ""),
      r2: pickSplit(r, split).r2,
      mae: pickSplit(r, split).mae,
      color: i === 2 || i === 4 ? palette.teal : i === 1 ? palette.accent : palette.blue,
    })),
  );

  const h4ChartItems = $derived(
    (report?.h4 ?? []).map((r, i) => ({
      label: r.label,
      r2: r.r2,
      mae: r.mae,
      color: i === 2 ? palette.teal : i === 1 ? palette.blue : palette.muted,
    })),
  );

  const transferBackends = $derived.by(() => {
    const cells = report?.h3.transferMatrix ?? [];
    return [...new Set(cells.map((c) => c.sourceBackend))];
  });

  let transferRegime = $state("mixed_submit");

  function findTransfer(src: string, dst: string) {
    return report?.h3.transferMatrix.find(
      (c) => c.sourceBackend === src && c.targetBackend === dst && c.regime === transferRegime,
    );
  }

  function change(v: Partial<EstimationChoices>) {
    onchange({ ...choices, ...v });
  }
</script>

<section class="surface estimation" aria-label="Quality estimation results">
  <div class="settings controls">
    {#if availableScopes.length}
      <Select
        label="Chip / Scope"
        value={activeScope}
        options={availableScopes}
        format={(s) => SCOPE_LABELS[s] ?? s}
        onchange={(scope) => change({ scope })}
      />
    {/if}
    {#if targetKeys.length}
      <Select
        label="Target quality metric"
        value={targetKey}
        options={targetKeys}
        format={(k) => {
          const r2 = data ? targetScore(data.targets[k], split) : null;
          return `${TARGET_LABELS[k] ?? k}${r2 === null ? "" : ` · R² ${r2.toFixed(2)}`}`;
        }}
        onchange={(target) => change({ target })}
      />
    {/if}
    {#if hasHoldout}
      <Select
        label="Evaluation split"
        value={split}
        options={["holdout", "cv"]}
        format={(s) => SPLIT_LABELS[s] ?? s}
        onchange={(s) => change({ split: s })}
      />
    {/if}
    <Select
      label="Thesis view"
      value={viewMode}
      options={Object.keys(VIEW_LABELS)}
      format={(v) => VIEW_LABELS[v] ?? v}
      onchange={(view) => change({ view })}
    />
  </div>

  {#if error}
    <p class="error" role="alert">{error}</p>
  {:else if !reports[activeScope]}
    <p role="status">
      No quality estimation snapshot is bundled yet for {activeScope}. Run
      <code>python -m experiments.ml_estimation</code> and rebuild dashboard data.
    </p>
  {:else if !data || !report}
    <p role="status">Loading estimation results…</p>
  {:else}
    <div class="heading">
      <div>
        <p class="eyebrow">
          {SCOPE_LABELS[data.backend] ?? data.backend} · {data.jobs} jobs ·
          {#if data.split?.mode === "kfold"}
            {VALIDATION.unseenCircuit.name} ({data.split.nSplits}-fold × {data.split.nRepeats} repeats over
            {data.split.totalConfigs} configurations)
          {:else}
            {data.trainJobs} train, {data.holdoutJobs} held out
          {/if}
        </p>
        <h2>{TARGET_LABELS[targetKey] ?? report.label}</h2>
        <p class="note">
          Best model: <strong>{report.bestModel}</strong> using {report.footprintCount} best
          {#if report.candidateFootprintCount && report.candidateFootprintCount > report.footprintCount}
            (of {report.candidateFootprintCount} VIF-screened)
          {/if}
          pre-runtime footprint features + {report.hardwareFeatureCount} hardware calibration features.
          {#if report.savedModels?.mixed_submit}
            Saved artifact: <code>{report.savedModels.mixed_submit.path}</code>
            ({report.savedModels.mixed_submit.sizeKb.toFixed(1)} KB).
          {/if}
          {#if data.holdoutPeriods.length}
            Unseen holdout: {data.holdoutPeriods.join(", ")}.
          {/if}
        </p>
      </div>
      {#if topMetrics}
        <div class="stat" class:pass={(topMetrics.h1Verdict ?? (topMetrics.meetsH1 ? "pass" : "fail")) === "pass"}>
          <strong>
            R² = {fmt(topMetrics.r2, 3)}
            {#if topMetrics.r2CiLow != null && topMetrics.r2CiHigh != null}
              [{fmt(topMetrics.r2CiLow, 2)}, {fmt(topMetrics.r2CiHigh, 2)}]
            {/if}
          </strong>
          <span>
            MAE {fmt(topMetrics.mae, 4)} · RMSE {fmt(topMetrics.rmse, 4)} ·
            {#if topMetrics.h1Verdict === "inconclusive"}
              H1 inconclusive (95% CI straddles 0.80)
            {:else if (topMetrics.h1Verdict ?? (topMetrics.meetsH1 ? "pass" : "fail")) === "pass"}
              Meets H1 (CI &ge; 0.80)
            {:else}
              Below H1 (0.80)
            {/if}
          </span>
        </div>
      {/if}
    </div>

    {#if viewMode === "h1"}
      <div class="two-col">
        <article class="card">
          <h3>Model leaderboard ({SPLIT_LABELS[split]})</h3>
          <EChart
            option={leaderboardChart(combinedLeaderboard, split, report.r2Threshold)}
            replace
            label="Model R2 leaderboard"
            style="height:310px;width:100%"
          />
        </article>
        <article class="card">
          <h3>Predicted vs. observed ({report.bestModel})</h3>
          <EChart
            option={scatterChart(report.points, split, report.label)}
            replace
            label="Predicted vs observed scatter plot"
            style="height:310px;width:100%"
          />
          <div class="algo-legend">
            {#each algoPointsLegend as algo}
              <span><i style:background={ALGO_COLORS[algo] ?? palette.blue}></i>{ALGO_SHORT[algo] ?? algo}</span>
            {/each}
          </div>
        </article>
      </div>

      <h3>All 7 thesis models + AutoML ensemble &amp; analytical baselines</h3>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Type</th>
              {#if hasHoldout}
                <th>{VALIDATION.calibrationCycle.short} R²</th>
                <th>{VALIDATION.calibrationCycle.short} MAE</th>
                <th>{VALIDATION.calibrationCycle.short} RMSE</th>
              {/if}
              <th>{VALIDATION.unseenCircuit.short} R²</th>
              <th>{VALIDATION.unseenCircuit.short} MAE</th>
              <th>Spearman ρ</th>
              <th>H1 (&ge; 0.80)</th>
            </tr>
          </thead>
          <tbody>
            {#each combinedLeaderboard as row}
              {@const activeM = pickSplit(row, split)}
              <tr>
                <td><strong>{row.label}</strong></td>
                <td>{row.kind === "procedure" ? "QAQS procedure (nested)" : row.kind === "analytical_baseline" ? "Analytical baseline" : row.kind === "ml_ensemble" ? "AutoML Ensemble" : "ML Regressor"}</td>
                {#if hasHoldout}
                  <td>{fmt(row.holdout?.r2, 3)}</td>
                  <td>{fmt(row.holdout?.mae, 4)}</td>
                  <td>{fmt(row.holdout?.rmse, 4)}</td>
                {/if}
                <td>{fmt(row.cv.r2, 3)}</td>
                <td>{fmt(row.cv.mae, 4)}</td>
                <td>{fmt(activeM.spearmanRho, 3)}</td>
                <td><span class="badge" class:ok={activeM.meetsH1}>{activeM.meetsH1 ? "PASS" : "FAIL"}</span></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if report.baselines.length === 0}
        <p class="note">
          Analytical M1/M2 baselines predict success rate and full TVD directly; switch Target to
          Total Variation Distance or Success Rate to compare ML against M1/M1-mixture/M2.
        </p>
      {/if}

    {:else if viewMode === "footprint"}
      <article class="card">
        <h3>Curated Quantum Circuit Footprint (O2 · post-VIF SHAP ranking)</h3>
        <EChart
          option={footprintChart(report.footprint)}
          replace
          label="Curated circuit footprint SHAP importance"
          style="height:360px;width:100%"
        />
      </article>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Metric</th>
              <th>Category</th>
              <th>Spearman ρ</th>
              <th>VIF</th>
              <th>Permutation ΔR²</th>
              <th>Mean |SHAP|</th>
            </tr>
          </thead>
          <tbody>
            {#each report.footprint as f}
              {@const isSelected = f.selected !== false}
              <tr>
                <td>
                  <span class="badge" class:ok={isSelected}>
                    {isSelected ? "Selected" : "Pruned (Noise)"}
                  </span>
                </td>
                <td><strong>{f.label}</strong><br /><small class="muted">{f.feature}</small></td>
                <td>{f.category}</td>
                <td>{fmt(f.spearmanRho, 3)}</td>
                <td>{f.vif == null ? "—" : fmt(f.vif, 2)}</td>
                <td>{fmt(f.permutationImportance, 4)}</td>
                <td>{fmt(f.shapMeanAbs, 4)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

    {:else if viewMode === "h3"}
      <article class="card">
        <h3>H3 · Circuit-Only vs. Hardware-Only vs. Mixed Calibration ({SPLIT_LABELS[split]})</h3>
        <EChart
          option={regimeBarChart(h3ChartItems, "r2")}
          replace
          label="H3 feature boundary R2 comparison"
          style="height:280px;width:100%"
        />
      </article>

      {#if temporal}
        <dl class="tests">
          <div>
            <dt>{VALIDATION.unseenCircuit.name}</dt>
            <dd>
              {VALIDATION.unseenCircuit.question} Every circuit configuration is predicted by a model that
              never saw it; calibration windows are shared with training ({VALIDATION.unseenCircuit.method}).
            </dd>
          </div>
          <div>
            <dt>{VALIDATION.calibrationCycle.name}</dt>
            <dd>
              {VALIDATION.calibrationCycle.question} Trained on earlier windows, tested on
              {temporal.holdoutPeriods.join(", ")}. {temporal.holdoutConfigsSeenInTrain} of
              {temporal.holdoutConfigs} test circuits were also in training, so this isolates calibration drift.
            </dd>
          </div>
        </dl>
      {/if}
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>Input Configuration</th>
              <th>Features</th>
              <th>{VALIDATION.unseenCircuit.short} R²</th>
              <th>{VALIDATION.unseenCircuit.short} MAE</th>
              <th>{VALIDATION.calibrationCycle.short} R²</th>
              <th>{VALIDATION.calibrationCycle.short} MAE</th>
              <th>{VALIDATION.calibrationCycle.short} RMSE</th>
            </tr>
          </thead>
          <tbody>
            {#each report.h3.regimes as reg}
              {@const ho = temporal ? temporal.regimes.find((t) => t.regime === reg.regime)?.holdout : reg.holdout}
              <tr>
                <td><strong>{reg.label}</strong></td>
                <td>{reg.featureCount}</td>
                <td>{fmt(reg.cv.r2, 3)}</td>
                <td>{fmt(reg.cv.mae, 4)}</td>
                <td>{fmt(ho?.r2, 3)}</td>
                <td>{fmt(ho?.mae, 4)}</td>
                <td>{fmt(ho?.rmse, 4)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if report.h3.drift.available}
        <h3>Calibration Drift Impact (`c.*` Submit vs. `d.*` Execution Snapshot)</h3>
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>{VALIDATION.calibrationCycle.short} subset</th>
                <th>Jobs</th>
                <th>Submit R²</th>
                <th>Submit MAE</th>
                <th>Exec R²</th>
                <th>Exec MAE</th>
                <th>MAE Δ (Exec − Submit)</th>
              </tr>
            </thead>
            <tbody>
              {#each report.h3.drift.rows as d}
                <tr>
                  <td><strong>{d.subset}</strong></td>
                  <td>{d.jobs}</td>
                  <td>{fmt(d.submitR2, 3)}</td>
                  <td>{fmt(d.submitMae, 4)}</td>
                  <td>{fmt(d.execR2, 3)}</td>
                  <td>{fmt(d.execMae, 4)}</td>
                  <td>{fmt(d.maeDeltaExecMinusSubmit, 4)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      {#if transferBackends.length >= 2}
        <div class="matrix-head">
          <h3>Cross-Chip / Cross-Provider Transfer Matrix (Train Row → Test Column)</h3>
          <div class="settings compact-select">
            <Select
              label="Transfer features"
              value={transferRegime}
              options={["circuit_only", "hardware_only", "mixed_submit"]}
              format={(r) =>
                r === "circuit_only"
                  ? "Circuit Footprint Only"
                  : r === "hardware_only"
                    ? "Hardware Only"
                    : "Mixed (Footprint + HW)"}
              onchange={(v) => (transferRegime = v)}
            />
          </div>
        </div>
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>Train \ Test</th>
                {#each transferBackends as dst}
                  <th>{dst}</th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each transferBackends as src}
                <tr>
                  <th>{src}</th>
                  {#each transferBackends as dst}
                    {@const c = findTransfer(src, dst)}
                    <td>
                      {#if c}
                        <strong>R² {fmt(c.r2, 3)}</strong>
                        <br />
                        <small class="muted">MAE {fmt(c.mae, 4)} ({c.mode === "within_chip_cv" ? "CV" : "0-shot"})</small>
                      {:else}
                        —
                      {/if}
                    </td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

    {:else if viewMode === "h2_h4"}
      <h3>H2 · Scalability Extrapolation &amp; Zero-Shot Generalization</h3>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>Protocol / Task</th>
              <th>Training Scope</th>
              <th>Held-Out Target</th>
              <th>Train / Test</th>
              <th>R²</th>
              <th>MAE</th>
              <th>RMSE</th>
              <th>Spearman ρ</th>
            </tr>
          </thead>
          <tbody>
            {#each report.h2 as row}
              <tr>
                <td><strong>{row.task}</strong></td>
                <td>{row.trainScope}</td>
                <td>{row.testTarget}</td>
                <td>{row.nTrain} / {row.nTest}</td>
                <td>{fmt(row.r2, 3)}</td>
                <td>{fmt(row.mae, 4)}</td>
                <td>{fmt(row.rmse, 4)}</td>
                <td>{fmt(row.spearmanRho, 3)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <h3>H4 · Complementary Benchmarking Signal (Random Volumetric vs. Paradigm Circuits)</h3>
      <article class="card">
        <EChart
          option={regimeBarChart(h4ChartItems, "r2")}
          replace
          label="H4 benchmarking regime R2"
          style="height:260px;width:100%"
        />
      </article>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>Training Regime</th>
              <th>Train / Test</th>
              <th>R²</th>
              <th>MAE</th>
              <th>RMSE</th>
              <th>Fourier R²</th>
              <th>Oracle R²</th>
              <th>Entanglement R²</th>
            </tr>
          </thead>
          <tbody>
            {#each report.h4 as row}
              <tr>
                <td><strong>{row.label}</strong></td>
                <td>{row.nTrain} / {row.nTest}</td>
                <td>{fmt(row.r2, 3)}</td>
                <td>{fmt(row.mae, 4)}</td>
                <td>{fmt(row.rmse, 4)}</td>
                <td>{fmt(row.byFamily?.fourier?.r2, 3)}</td>
                <td>{fmt(row.byFamily?.oracle?.r2, 3)}</td>
                <td>{fmt(row.byFamily?.entanglement?.r2, 3)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</section>

<style>
  .estimation { padding: clamp(12px, 2.3vw, 28px); display: grid; gap: 16px; min-width: 0; }
  .controls { border-bottom: 1px solid var(--line); padding-bottom: 16px; margin: 0; }
  .controls :global(label) { flex: 1 1 165px; min-width: 0; }
  .controls :global(select) { width: 100%; min-width: 0; }
  .heading { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
  .tests { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 0.6rem 1.4rem; margin: 0.6rem 0 1rem; }
  .tests dt { font-weight: 600; }
  .tests dd { margin: 0.15rem 0 0; color: var(--muted, #52615c); font-size: 0.9rem; line-height: 1.4; }
  .heading h2 { font: 500 clamp(1.5rem, 2.8vw, 2.3rem) Georgia, serif; }
  .stat { border-left: 3px solid #c44d16; padding-left: 14px; display: grid; gap: 2px; }
  .stat.pass { border-left-color: var(--teal); }
  .stat strong { font-size: 1.55rem; font-variant-numeric: tabular-nums; }
  .stat span { font-size: 0.78rem; color: var(--muted); }
  .two-col { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr)); gap: 14px; }
  .card { border: 1px solid var(--line); border-radius: 10px; padding: 14px; min-width: 0; }
  .card h3 { font-size: 0.96rem; margin-bottom: 8px; }
  .algo-legend { display: flex; flex-wrap: wrap; gap: 8px 14px; margin-top: 6px; font-size: 0.76rem; color: var(--muted); }
  .algo-legend span { display: inline-flex; align-items: center; gap: 5px; }
  .algo-legend i { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
  .badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; background: #fae5dc; color: #9a3412; }
  .badge.ok { background: #dcfce7; color: #166534; }
  .muted { color: var(--muted); font-size: 0.75rem; font-weight: 400; }
  .matrix-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
  .compact-select { margin: 0; width: min(100%, 15rem); }
</style>
