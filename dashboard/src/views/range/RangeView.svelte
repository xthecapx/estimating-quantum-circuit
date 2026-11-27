<script lang="ts">
  import type { AxisKey, QuestionKey } from "../../lib/data/types";
  import { axes, questionKeys, questions } from "../../lib/domain/catalog";
  import { comparator, format, lowerIsBetter, plural } from "../../lib/domain/format";
  import type { Explorer } from "../../lib/state/explorer.svelte";
  import RegressionView from "../regression/RegressionView.svelte";
  import { averageQuestion, resourceUnit } from "../regression/questions";
  import TargetInput from "../TargetInput.svelte";
  import Findings from "./Findings.svelte";
  import SweepTable from "./SweepTable.svelte";
  import TrendChart from "./TrendChart.svelte";

  let { explorer }: { explorer: Explorer } = $props();
  const key = $derived(explorer.question);
  const details = $derived(explorer.mode === "details");
  const axisKeys = Object.keys(axes) as AxisKey[];
</script>

{#snippet xPicker()}
  <label class="axis-picker x-picker">X-axis
    <select value={explorer.axis} onchange={e => { explorer.axis = e.currentTarget.value as AxisKey; explorer.readAt = null; }}>
      {#each axisKeys as a}<option value={a}>{explorer.axisLabels[a]}</option>{/each}
    </select>
  </label>
{/snippet}

<div id="plot-view">
  <div class="plot-caption">
    <h2 id="plot-title" tabindex="-1">{averageQuestion(explorer.axis, key, explorer.threshold)}</h2>
  </div>
  <div class:analysis={details}>
    <section class="range-plot" aria-label="Operating range plot">
      <div class="chart-header">
        <div class="metric-group">
          <label class="axis-picker">Y-axis
            <span class="metric-picker">
              <span aria-hidden="true">{questions[key].label}: {questions[key].prompt}</span>
              <select aria-label="Y-axis" value={key} onchange={e => explorer.setQuestion(e.currentTarget.value as QuestionKey)}>
                {#each questionKeys as q}<option value={q}>{questions[q].label}: {questions[q].prompt}</option>{/each}
              </select>
            </span>
          </label>
          {#if details}
            <div class="legend">
              <span class="legend-item"><i class="dot-key"></i><strong>One dot per run</strong> · {lowerIsBetter(key) ? "Lower" : "Higher"} is better</span>
              <span class="pointer-hint">Hover for details · Click for histogram</span>
              <span class="touch-hint">Tap for histogram</span>
            </div>
          {:else if explorer.levels.length}
            <div class="legend">
              <span class="legend-item"><i class="range-key"></i>Observed range (worst to best)</span>
              <span class="legend-item"><i class="average-key"></i>Average · {lowerIsBetter(key) ? "0" : key === "success" ? "100%" : "1"} is better</span>
            </div>
          {/if}
        </div>
        <TargetInput {explorer} />
      </div>
      {#if details}
        <TrendChart {explorer} />
        {@render xPicker()}
      {:else}
        <RegressionView {explorer} {xPicker} />
      {/if}
      {#if explorer.levels.length && explorer.threshold !== null}
        <p class="target-answer">{explorer.passingLevel ? `The largest tested setting meeting the target on average is ${explorer.passingLevel.x} ${resourceUnit(explorer.axis, explorer.provider)}.` : "No tested setting meets the target on average."}</p>
      {/if}
    </section>
    {#if details}<Findings {explorer} />{/if}
  </div>
  <details class="experiment-info">
    <summary>Experiment details</summary>
    <p class="note" id="coverage" role="status">{plural(explorer.configs.length, "experiment")} · {plural(explorer.jobs.length, "job")} · {plural(explorer.collections, "collection")}
      · {explorer.threshold == null ? "No target set" : `Target ${comparator(key)} ${format(key, explorer.threshold)}`}</p>
    <p><strong>{questions[key].label}.</strong> {questions[key].meaning}</p>
    <p>At each tested setting, repeated runs are averaged within each circuit configuration. Each configuration then counts equally toward the average. The shaded band in Overview spans the lowest and highest individual measurements.</p>
  </details>
  {#if details}<SweepTable {explorer} />{/if}
</div>

<style>
  .plot-caption { padding:0; margin:0 0 12px; }
  h2 { text-wrap:balance; margin:0; }
  .experiment-info { margin-top:12px; }
  .experiment-info summary { cursor:pointer; font-weight:600; }
  .experiment-info p { max-width:80ch; margin:8px 0 0; }
  .target-answer { margin-top:12px; font-weight:650; }
  .range-plot { min-width:0; padding:clamp(10px,2vw,16px); border:1px solid var(--line); border-radius:12px; }
  .chart-header { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:start; gap:10px 24px; }
  .x-picker { justify-content:center; margin-top:4px; }
  .metric-picker { position:relative; min-width:0; padding:6px 28px 6px 10px; border:1px solid #abbdb3; border-radius:6px; color:var(--ink); font-size:.83rem; }
  .metric-picker::after { content:""; position:absolute; right:10px; top:50%; width:6px; height:6px; border:solid var(--muted); border-width:0 2px 2px 0; transform:translateY(-70%) rotate(45deg); pointer-events:none; }
  .axis-picker .metric-picker select { position:absolute; inset:0; width:100%; height:100%; opacity:0; }
  .metric-picker:focus-within { outline:3px solid #c17a23; outline-offset:2px; }
  .axis-picker { display:flex; flex-direction:row; align-items:center; gap:6px; color:var(--muted); font-size:.76rem; }
  .axis-picker select { width:auto; min-height:32px; padding-block:3px; font-size:.83rem; }
  .metric-group { display:grid; justify-items:start; gap:8px; min-width:0; }
  .legend { display:flex; flex-wrap:wrap; align-items:center; gap:4px 12px; font-size:.8rem; }
  .legend-item { display:inline-flex; align-items:center; gap:6px; }
  .range-key { width:22px; height:9px; background:rgba(56,123,154,.22); border:1px solid #387b9a; }
  .average-key { width:22px; border-top:3px solid var(--teal); }
  @media (max-width:680px) {
    .chart-header { grid-template-columns:minmax(0,1fr); }
    .metric-group { display:contents; }
    .legend { grid-row:3; }
  }
  .touch-hint { display:none; }
  @media (hover:none) {
    .pointer-hint { display:none; }
    .touch-hint { display:inline; }
  }
  .dot-key { width:8px; height:8px; border-radius:50%; background:var(--teal); }
</style>
