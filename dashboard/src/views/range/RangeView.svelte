<script lang="ts">
  import type { AxisKey, QuestionKey } from "../../lib/data/types";
  import { axes, questionKeys, questions } from "../../lib/domain/catalog";
  import { comparator, format, plural } from "../../lib/domain/format";
  import type { Explorer } from "../../lib/state/explorer.svelte";
  import ExperimentFilters from "../ExperimentFilters.svelte";
  import TargetInput from "../TargetInput.svelte";
  import Findings from "./Findings.svelte";
  import SweepTable from "./SweepTable.svelte";
  import TrendChart from "./TrendChart.svelte";

  let { explorer }: { explorer: Explorer } = $props();
  const key = $derived(explorer.question);
  const metric = $derived(questions[key].label);
  const axisKeys = Object.keys(axes) as AxisKey[];
  const metricQuestion = (q: QuestionKey) => `${questions[q].label}: ${questions[q].prompt}`;
</script>

<div id="plot-view">
  <ExperimentFilters {explorer} showChipHistory />
  <div class="plot-caption">
    <h2 id="plot-title" tabindex="-1">{metric} by {axes[explorer.axis].toLowerCase()}</h2>
    <p class="note" id="coverage" role="status">{plural(explorer.configs.length, "experiment")} · {plural(explorer.jobs.length, "job")} · {plural(explorer.collections, "collection")}
      · {explorer.threshold == null ? "No target set" : `Target ${comparator(key)} ${format(key, explorer.threshold)}`}</p>
  </div>
  <div class="analysis">
    <section class="range-plot" aria-label="Operating range plot">
      <div class="chart-header">
        <label class="axis-picker"><span class="axis-name">Y-axis</span>
          <span class="metric-picker">
            <span aria-hidden="true">{metricQuestion(key)}</span>
            <select aria-label="Y-axis" value={key} onchange={e => explorer.setQuestion(e.currentTarget.value as QuestionKey)}>
              {#each questionKeys as q}<option value={q}>{metricQuestion(q)}</option>{/each}
            </select>
          </span>
        </label>
        <TargetInput {explorer} />
      </div>
      <TrendChart {explorer} />
      <label class="axis-picker x-picker">X-axis
        <select aria-label="X-axis" value={explorer.axis} onchange={e => explorer.axis = e.currentTarget.value as AxisKey}>
          {#each axisKeys as a}<option value={a}>{axes[a]}</option>{/each}
        </select>
      </label>
      <p class="note plot-help">Each point represents one job. {key === "success" ? "Hover to see its accepted-shot fraction and 99% confidence bounds." : "Hover to inspect the measurement."} Select a point or a job in the table to open its histogram. Dates are in UTC.</p>
    </section>
    <Findings {explorer} />
  </div>
  <SweepTable {explorer} />
</div>

<style>
  .range-plot { min-width:0; padding:clamp(10px,2vw,16px); border:1px solid var(--line); border-radius:12px; }
  .chart-header { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:10px; }
  .axis-picker { display:flex; flex-direction:row; align-items:center; gap:6px; min-width:0; color:var(--muted); }
  .axis-name { white-space:nowrap; }
  .axis-picker { font-size:.76rem; }
  .axis-picker select,.metric-picker { min-height:32px; font-size:.83rem; font-weight:500; }
  .metric-picker { position:relative; max-width:100%; min-width:0; display:flex; align-items:center; padding:6px 30px 6px 10px; border:1px solid #abbdb3; border-radius:6px; color:var(--ink); }
  .metric-picker::after { content:""; position:absolute; right:12px; width:7px; height:7px; border:solid var(--muted); border-width:0 2px 2px 0; transform:translateY(-2px) rotate(45deg); pointer-events:none; }
  .metric-picker select { position:absolute; inset:0; width:100%; height:100%; opacity:0; }
  .metric-picker:focus-within { outline:3px solid #c17a23; outline-offset:2px; }
  .x-picker { justify-content:center; }
  .x-picker select { width:auto; padding-block:3px; }
  .plot-help { border-top:1px solid var(--line); padding-top:10px; margin-top:12px; }
</style>
