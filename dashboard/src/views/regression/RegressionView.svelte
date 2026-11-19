<script lang="ts">
  import EChart from "../../lib/charts/EChart.svelte";
  import { palette, type EChartsType } from "../../lib/charts/echarts";
  import type { AxisKey } from "../../lib/data/types";
  import { algorithmName, axes, questionKeys, questions } from "../../lib/domain/catalog";
  import { comparator, format, lowerIsBetter } from "../../lib/domain/format";
  import { passes } from "../../lib/domain/sweep";
  import type { Explorer } from "../../lib/state/explorer.svelte";
  import { levelMeans, selectRegression } from "../../lib/stats/regression";
  import Select from "../../lib/ui/Select.svelte";
  import { fitAnswer, fitQuestion, resource } from "./questions";

  let { explorer, readAt = $bindable<number | null>(null) }: { explorer: Explorer; readAt?: number | null } = $props();
  const axis = $derived(explorer.axis);
  const metric = $derived(explorer.question);
  const target = $derived(explorer.threshold);
  const levels = $derived(levelMeans(explorer.jobs, axis, metric));
  const fit = $derived(selectRegression(levels));
  const first = $derived(levels[0]?.x ?? 0);
  const last = $derived(levels.at(-1)?.x ?? 0);
  const limit = $derived.by(() => {
    if (!fit || target === null) return undefined;
    return levels.filter(({ x }) => passes(metric, fit!.predict(x), target)).at(-1)?.x;
  });
  const x = $derived(readAt !== null && readAt >= first && readAt <= last ? readAt : limit ?? first);
  const y = $derived(fit?.predict(x) ?? 0);
  const unit = $derived(resource[axis].unit);
  const tested = $derived(levels.some((p) => p.x === x));
  const curve = $derived.by(() => {
    if (!fit) return [];
    const samples = new Set(levels.map((p) => p.x));
    for (let i = 0; i <= 240; i++) samples.add(first + (last - first) * i / 240);
    return [...samples].sort((a, b) => a - b).map((v) => [v, fit!.predict(v)]);
  });

  const option = $derived({
    animation: false,
    grid: { top: 18, right: 22, bottom: 48, left: 48 },
    xAxis: { type: "value", min: first, max: last, minInterval: 1,
      name: axes[axis], nameLocation: "middle", nameGap: 30 },
    yAxis: { type: "value", min: 0, max: 1, interval: 0.25,
      axisLabel: { formatter: (v: number) => metric === "success" ? Math.round(v * 100) + "%" : String(v) } },
    series: [
      { type: "line", name: "Fitted mean", showSymbol: false, lineStyle: { width: 3, color: palette.teal }, data: curve,
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { type: "dashed", color: palette.threshold },
          data: target === null ? [] : [{ yAxis: target }] } },
      { type: "scatter", name: "Selected estimate", symbolSize: 12, itemStyle: { color: palette.teal, borderColor: "#fff", borderWidth: 2 }, data: [[x, y]] },
    ],
  });

  function attach(instance: EChartsType) {
    instance.getZr().on("click", (event) => {
      const pixel = [event.offsetX, event.offsetY];
      if (!instance.containPixel({ gridIndex: 0 }, pixel)) return;
      const value = instance.convertFromPixel({ gridIndex: 0 }, pixel) as number[];
      readAt = Math.max(first, Math.min(last, Math.round(value[0])));
    });
  }
</script>

<section class="surface" aria-label="Regression explorer">
  <div class="settings">
    <Select label="Algorithm" value={explorer.algorithm} options={explorer.algorithms} format={algorithmName} onchange={(v) => explorer.setAlgorithm(v)} />
    <Select label="X-axis" value={axis} options={Object.keys(axes) as AxisKey[]} format={(v) => axes[v]} onchange={(v) => { explorer.axis = v; readAt = null; }} />
    <Select label="Y-axis" value={metric} options={questionKeys} format={(v) => questions[v].label} onchange={(v) => explorer.setQuestion(v)} />
  </div>
  <details class="scope">
    <summary>{explorer.backend} · {explorer.periodLabel} · {explorer.family || "All experiments"}</summary>
    <div class="settings">
      <Select label="Chip" value={explorer.backend} options={explorer.backends} onchange={(v) => explorer.setBackend(v)} />
      <Select label="Collection period" value={explorer.period} options={["", ...explorer.periods.map(p => p.id)]}
        format={(v) => explorer.periods.find(p => p.id === v)?.label ?? "All periods"} onchange={(v) => explorer.setPeriod(v)} />
      <Select label="Experiment group" value={explorer.family} options={["", ...explorer.families]} format={(v) => v || "All experiments"} onchange={(v) => explorer.setFamily(v)} />
    </div>
  </details>
  <h2>{fitQuestion(axis, metric, target)}</h2>
  <p class="meaning">{questions[metric].meaning}</p>
  <div class="settings target">
    <label>{lowerIsBetter(metric) ? "Maximum" : "Minimum"} target (optional)
      <input type="number" min="0" max="1" step="0.1" inputmode="decimal" placeholder="No target" aria-invalid={explorer.targetInvalid}
        bind:value={explorer.targetValue} />
    </label>
    <span class="note">{explorer.targetInvalid ? "Enter a target between 0 and 1." : metric === "success" ? "0.5 means 50% of shots." : "Metric scale 0–1."}</span>
  </div>
  {#if fit}
    {#if target !== null}
      <p class="target-answer">{limit === undefined ? "No tested setting meets the target on the fit." : `The largest tested setting meeting the target is ${limit} ${unit}.`}</p>
    {/if}
    <div class="legend"><span class="fit-key"></span>{questions[metric].label} · fitted mean
      {#if target !== null}<span class="target-key"></span>Target {comparator(metric)} {format(metric, target)}{/if}
    </div>
    <EChart id="regression-plot" style="height:clamp(250px,35vw,365px)" label={fitQuestion(axis, metric, target)} {option} replace onready={attach} />
    <div class="reading">
      <label>Read at {axes[axis].toLowerCase()}
        <input type="range" min={first} max={last} step="1" value={x} aria-valuetext={`${x} ${unit}`}
          oninput={(event) => readAt = Number(event.currentTarget.value)} />
      </label>
      <p aria-live="polite" id="fit-reading"><strong>At {x} {unit},</strong> {fitAnswer(metric, y)}.
        {#if target !== null}<small>{passes(metric, y, target) ? "Meets the target" : "Misses the target"} of {comparator(metric)} {format(metric, target)}.</small>{/if}
        {#if !tested}<small>Interpolated between tested settings.</small>{/if}
      </p>
    </div>
    <p class="note">Click the curve or use the slider to read a fitted value.</p>
    <details class="method">
      <summary>{fit.shape} fit · {levels.length} tested settings</summary>
      <p>At each X value, repetitions are averaged within each configuration, then configurations are weighted equally.
        Each tested X value has equal weight in the regression. We compare constant, linear and logarithmic fits,
        adding a quadratic with at least five settings. The selected fit has the lowest mean absolute error when each setting is held out in turn.
        Estimates are limited to the metric’s 0–1 scale. The held-out mean absolute error is {metric === "success" ? (100 * fit.error).toFixed(1) + " percentage points" : format(metric, fit.error)}.</p>
    </details>
  {:else}
    <p class="empty" role="status">This selection has {levels.length} tested {levels.length === 1 ? "setting" : "settings"} with {questions[metric].label} values. A regression needs at least three. Choose another axis or expand the experiment scope.</p>
  {/if}
</section>

<style>
  .settings { margin-top: 0; }
  .scope, .method { color: var(--muted); font-size: .84rem; }
  summary { cursor: pointer; }
  .scope { padding-bottom: 16px; border-bottom: 1px solid var(--line); margin-bottom: 20px; }
  .scope .settings { margin: 12px 0 0; }
  h2 { max-width: 52ch; text-wrap: balance; }
  .meaning { margin: 6px 0 15px; color: var(--muted); }
  .target { align-items: end; margin-bottom: 10px; }
  .target label { flex: 0 1 175px; }
  .target span { padding-bottom: 9px; }
  .target-answer { margin: 12px 0; font-weight: 650; }
  .legend { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 20px; font-size: .8rem; }
  .fit-key, .target-key { width: 22px; border-top: 3px solid var(--teal); }
  .target-key { margin-left: 5px; border-top: 2px dashed #9a5b12; }
  .reading { display: flex; align-items: center; gap: 14px 25px; flex-wrap: wrap; padding: 14px 18px; margin-bottom: 5px; border-radius: 8px; background: #edf4ef; }
  .reading label { flex: 1 1 145px; max-width: 215px; }
  .reading p { flex: 2 1 240px; }
  .reading small { display: block; color: var(--muted); margin-top: 3px; }
  input[type=range] { accent-color: var(--teal); width: 100%; }
  .method { border-top: 1px solid var(--line); padding-top: 12px; margin-top: 18px; }
  .method p { margin-top: 8px; max-width: 85ch; }
  .empty { padding: 20px 0; }
</style>
