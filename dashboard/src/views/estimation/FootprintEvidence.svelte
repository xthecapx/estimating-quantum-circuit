<script lang="ts">
  import EChart from "../../lib/charts/EChart.svelte";
  import SelectedFootprint from "./SelectedFootprint.svelte";
  import Icon from "../../lib/ui/Icon.svelte";
  import Select from "../../lib/ui/Select.svelte";
  import { fmt, footprintChart, type TargetReport } from "./model";

  let { report, scope, combined }: { report: TargetReport; scope: string; combined: boolean } = $props();
  const evidenceRoot = $derived("https://github.com/xthecapx/estimating-quantum-circuit/blob/main/report/ml_estimation" + (combined ? "/multi_provider" : ""));
  let showChart = $state(false);
  const rows = $derived(report.footprintAblation ?? []);
  const chosen = $derived(rows.find(row => row.selected));
  const models = $derived((report.circuitLeaderboard ?? []).filter(m => m.kind === "ml" || m.kind === "ml_ensemble"));
  let metricId = $state("");
  const metric = $derived(report.footprint.find(f => f.feature === metricId) ?? report.footprint[0]);
</script>

<header class="summary">
  <div><p class="eyebrow">{scope} · {report.label}</p>
    <h2>How was this footprint selected?</h2>
    <p class="note">Start with pre-execution metrics from the logical and compiled circuits. For each training scope and target, repeat selection inside each training fold. The final fit uses all training configurations in that scope.</p>
  </div>
  <div class="stat"><strong>{report.footprintCount} of {report.footprint.length}</strong><span>screened metrics retained</span></div>
</header>

<ol class="stages" aria-label="Footprint generation process">
  <li><h3><Icon name="filter" size={18}/> Screen for redundancy</h3><p>Order candidates by absolute Spearman correlation with the target. Add them in order, screening for missing values, near-duplicates (|r| ≥ 0.985) and collinearity (maximum allowed VIF of 10). Up to 16 metrics advance.</p></li>
  <li><h3><Icon name="compare" size={18}/> Rank predictive contributions</h3><p>XGBoost predicts held-out configurations. Shuffling one metric measures its importance as a drop in R². Mean absolute SHAP measures how much it moves predictions.</p></li>
  <li><h3><Icon name="group" size={18}/> Choose the footprint size</h3><p>Train LightGBM on successively longer prefixes of the ranking. Keep the smallest eligible size within 0.0015 R² of the best eligible score in grouped cross-validation.</p></li>
</ol>

<SelectedFootprint {report}/>

<div class="evidence">
<details><summary>Why each metric was kept or left out</summary>
  <p class="note">The first {report.footprintCount} ranked metrics form the final footprint. “Folds selected” shows how often each metric also survived selection when the training configurations changed.</p>
  {#if metric}
    <div class="inspection settings">
      <Select label="Inspect a metric" value={metric.feature} options={report.footprint.map(f=>f.feature)}
        format={id=>report.footprint.find(f=>f.feature===id)?.label ?? id} onchange={id=>metricId=id}/>
      <p aria-live="polite">Rank <strong>{metric.rank ?? report.footprint.indexOf(metric)+1}</strong>
        {metric.selected === false ? "falls outside" : "falls inside"} the selected top {report.footprintCount}.
        Shuffling this metric {metric.permutationImportance >= 0 ? "lowered" : "raised"} XGBoost’s R² by
        {fmt(Math.abs(metric.permutationImportance), 4)} on average. Its mean absolute contribution to a prediction was {fmt(metric.shapMeanAbs, 4)} in target units.</p>
    </div>
  {/if}
  <div class="scroll"><table aria-label="Metric selection evidence"><thead><tr>
    <th>Rank</th><th>Metric</th><th>Decision</th><th>Spearman ρ</th><th>VIF</th><th>Permutation ΔR²</th><th>Mean |SHAP|</th><th>Folds selected</th>
  </tr></thead><tbody>
    {#each report.footprint as f, i (f.feature)}
      <tr><td>{f.rank ?? i + 1}</td><th scope="row">{f.label}<small>{f.feature}</small></th>
        <td>{f.selected === false ? "Outside cutoff" : "Retained"}</td>
        <td>{fmt(f.spearmanRho, 3)}</td><td>{fmt(f.vif, 2)}</td>
        <td>{fmt(f.permutationImportance, 4)}</td><td>{fmt(f.shapMeanAbs, 4)}</td>
        <td>{f.selectionFrequency == null ? "—" : (100 * f.selectionFrequency).toFixed(0) + "%"}</td></tr>
    {/each}
  </tbody></table></div>
</details>
<details bind:open={showChart}><summary>Ranking formula and SHAP contributions</summary>
    <p class="note">Metrics with permutation ΔR² ≤ 0 and mean |SHAP| below 0.005 rank last. Within each group, the score is mean |SHAP| + 0.5 × max(0, permutation ΔR²). Ties use mean |SHAP|, then absolute Spearman ρ.</p>
    {#if showChart && report.footprint.length}
      <EChart option={footprintChart(report.footprint)} replace label="Mean absolute SHAP by circuit metric" style="height:400px;width:100%"/>
    {/if}
  </details>

  <details><summary>How many metrics were enough?</summary>
    {#if chosen}<p class="note">The selected {chosen.k}-metric footprint reached R² {fmt(chosen.cvR2, 4)} and mean absolute error {fmt(chosen.cvMae, 4)}. The search caps the final footprint at ten metrics and can also score larger sets for comparison.</p>{/if}
    {#if rows.length}
      <table aria-label="LightGBM footprint size experiment"><thead><tr><th>Top metrics</th><th>CV R²</th><th>CV MAE</th></tr></thead><tbody>
        {#each rows as r}<tr class:chosen={r.selected}><th scope="row">{r.k}{r.selected ? " · Selected" : ""}</th><td>{fmt(r.cvR2, 4)}</td><td>{fmt(r.cvMae, 4)}</td></tr>{/each}
      </tbody></table>
    {:else}<p>No footprint-size scores were saved for this target.</p>{/if}
  </details>
  <details><summary>How did the regressors perform?</summary>
    <p class="note">Each regressor used the circuit metrics selected within its training fold. R² and mean absolute error measure the whole footprint on held-out configurations. Individual metric contributions above come from XGBoost.</p>
    {#if models.length}
      <table aria-label="Circuit-only regressor performance"><thead><tr><th>Regressor</th><th>CV R²</th><th>CV MAE</th></tr></thead><tbody>
        {#each models as model}<tr><th scope="row">{model.label}</th><td>{fmt(model.cv.r2, 4)}</td><td>{fmt(model.cv.mae, 4)}</td></tr>{/each}
      </tbody></table>
    {:else}<p>No circuit-only leaderboard was saved for this target.</p>{/if}
  </details>
</div>
<p class="sources"><a href="https://github.com/xthecapx/estimating-quantum-circuit/blob/main/experiments/footprint_analysis.py">Selection method</a>
  · <a href="{evidenceRoot}/footprint.csv">Metric evidence (CSV)</a>
  · <a href="{evidenceRoot}/footprint_ablation.csv">Footprint-size results (CSV)</a></p>

<style>
  .summary { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:1rem; padding:0; }
  .summary h2 { font:500 clamp(1.6rem,3vw,2.4rem) Georgia,serif; }
  .summary .note { max-width:64ch; }
  .stat { display:grid; border-inline-start:3px solid var(--teal); padding-inline-start:1rem; }
  .stat strong { font-size:1.5rem; } .stat span { font-size:.8rem; color:var(--muted); }
  .stages { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:26px; list-style:none; margin:0; padding:0; }
  .stages li { position:relative; border:1px solid var(--line); border-radius:9px; padding:1rem; background:#f4f8f5; }
  .stages li + li::before { content:"→"; position:absolute; top:calc(50% - .8em); left:-23px; color:var(--teal); font-size:1.1rem; }
  .stages h3 { display:flex; align-items:center; gap:8px; }
  .stages h3 :global(svg) { flex:none; color:var(--teal); }
  .stages p,.note { margin:.4rem 0; font-size:.85rem; line-height:1.5; color:var(--muted); }
  .evidence { min-width:0; border-block-start:1px solid var(--line); }
  .evidence details { border-block-end:1px solid var(--line); padding-block:7px; }
  .evidence details[open] { padding-bottom:15px; }
  @media (max-width:760px) {
    .stages { grid-template-columns:minmax(0,1fr); gap:20px; }
    .stages li + li::before { content:"↓"; top:-23px; left:calc(50% - .5em); }
  }
  .inspection { align-items:center; padding:12px; border:1px solid var(--line); border-radius:8px; }
  .inspection :global(label) { min-width:0; flex:1 1 210px; }
  .inspection p { flex:2 1 275px; font-size:.86rem; line-height:1.5; }
  .sources { font-size:.8rem; }
  .scroll { overflow-x:auto; } .scroll table { min-width:760px; }
  th { text-align:left; } table { width:100%; font-variant-numeric:tabular-nums; }
  td,th { vertical-align:top; } small { display:block; overflow-wrap:anywhere; font-weight:400; color:var(--muted); }
  .chosen { background:#e6f2ed; } summary { cursor:pointer; font-weight:600; }
</style>
