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
  import { ALL_GROUPS, ALL_PERIODS } from "../../lib/domain/scope";
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
  const quality = $derived(lowerIsBetter(metric) ? 1 - y : y);
  const pointColor = $derived.by(() => {
    // Interpolate through dark red, ochre and green so white text stays legible.
    const red = [195, 8, 44], amber = [143, 91, 14], green = [19, 109, 78];
    const lower = Math.max(0, (quality - 0.3) / 0.2);
    const [start, end] = quality < 0.5 ? [red, amber] : [amber, green];
    const fraction = quality < 0.5 ? lower : (quality - 0.5) * 2;
    return `rgb(${start.map((c, i) => Math.round(c + (end[i] - c) * fraction)).join(",")})`;
  });
  const metricLabel = $derived(metric === "dsr" ? "DSR" : questions[metric].label);
  function navigatePoint(event: KeyboardEvent) {
    const positions: Record<string, number> = {
      ArrowLeft: x - 1, ArrowDown: x - 1, ArrowRight: x + 1, ArrowUp: x + 1,
      Home: first, End: last,
    };
    if (Object.hasOwn(positions, event.key)) {
      event.preventDefault();
      readAt = Math.max(first, Math.min(last, positions[event.key]));
    }
  }
  const curve = $derived.by(() => {
    if (!fit) return [];
    const samples = new Set(levels.map((p) => p.x));
    for (let i = 0; i <= 240; i++) samples.add(first + (last - first) * i / 240);
    return [...samples].sort((a, b) => a - b).map((v) => [v, fit!.predict(v)]);
  });

  const grid = { top: 22, right: 24, bottom: 28, left: 48, outerBoundsMode: "none" };
  let drag: { id: number; startY: number; startValue: number; moved: boolean } | null = null;

  function startTargetDrag(event: PointerEvent) {
    if (event.button !== 0 || target === null || drag) return;
    const handle = event.currentTarget as HTMLElement;
    handle.setPointerCapture(event.pointerId);
    drag = { id: event.pointerId, startY: event.clientY, startValue: target, moved: false };
  }

  function moveTarget(event: PointerEvent) {
    if (event.pointerId !== drag?.id || !drag) return;
    if (!drag.moved && Math.abs(event.clientY - drag.startY) < 3) return;
    drag.moved = true;
    const height = (event.currentTarget as HTMLElement).parentElement!.getBoundingClientRect().height;
    const value = drag.startValue + (drag.startY - event.clientY) / height;
    explorer.targetValue = Math.round(100 * Math.max(0, Math.min(1, value))) / 100;
  }

  function finishTargetDrag(event: PointerEvent) {
    if (!drag || drag.id !== event.pointerId) return;
    if (!drag.moved) {
      // A click where the curve crosses the target still selects a fitted value.
      const bounds = (event.currentTarget as HTMLElement).getBoundingClientRect();
      const fraction = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
      readAt = Math.round(first + fraction * (last - first));
    }
    drag = null;
  }

  function stepTarget(event: KeyboardEvent) {
    if (target === null) return;
    const step = event.shiftKey ? 0.1 : 0.01;
    const values: Record<string, number> = {
      ArrowUp: target + step, ArrowRight: target + step,
      ArrowDown: target - step, ArrowLeft: target - step, Home: 0, End: 1,
    };
    if (Object.hasOwn(values, event.key)) {
      event.preventDefault();
      explorer.targetValue = Math.round(100 * Math.max(0, Math.min(1, values[event.key]))) / 100;
    }
  }
  const option = $derived({
    animation: false,
    grid,
    xAxis: { type: "value", min: first, max: last, minInterval: 1 },
    yAxis: { type: "value", min: 0, max: 1, interval: 0.25,
      axisLabel: { formatter: (v: number) => metric === "success" ? Math.round(v * 100) + "%" : String(v) } },
    series: [
      { type: "line", name: "Plot target", z: 0, silent: true, symbol: "none",
        lineStyle: { color: "#68449b", type: "dashed", width: 2 },
        data: target === null ? [] : [[first, target], [last, target]],
        endLabel: { show: target !== null, align: "right", offset: [-10, -10],
          color: "#68449b", backgroundColor: "#f7f1ff", padding: [2, 5], borderRadius: 4,
          formatter: target === null ? "" : `↕ Target ${comparator(metric)} ${format(metric, target)}` } },
      { type: "line", name: "Fitted mean", showSymbol: false, lineStyle: { width: 3, color: palette.teal }, data: curve },
      { type: "scatter", name: "Selected estimate", z: 8, symbolSize: 15, itemStyle: { opacity: 1, color: pointColor, borderColor: "#fff", borderWidth: 2 }, data: [[x, y]],
        label: { show: true, position: y > 0.5 ? "bottom" : "top", distance: 9,
          align: x < (first + last) / 2 ? "left" : "right", lineHeight: 16,
          formatter: `${metricLabel}  ${format(metric, y)}\n${x} ${unit}`, color: "#fff", backgroundColor: pointColor,
          padding: [4, 6], borderRadius: 4 },
        markLine: { silent: true, symbol: "none", label: { show: false },
          lineStyle: { type: "dashed", color: pointColor },
          data: [[{ coord: [x, 0] }, { coord: [x, y] }], [{ coord: [first, y] }, { coord: [x, y] }]] } },
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
  <div class="settings scope-fields" role="group" aria-label="Experiment filters">
    <Select icon="depth" label="Algorithm" value={explorer.algorithm} options={explorer.algorithms}
      format={algorithmName} onchange={(v) => { explorer.setAlgorithm(v); explorer.targetValue = 0.5; }} />
    <Select icon="chip" label="Chip" value={explorer.backend} options={explorer.backends}
      onchange={(v) => explorer.setBackend(v)} />
    <Select icon="date" label="Periods (UTC)" value={explorer.period}
      options={[ALL_PERIODS, ...explorer.periods.map(p => p.id)]}
      format={(v) => explorer.periods.find(p => p.id === v)?.label ?? "All periods"}
      onchange={(v) => explorer.setPeriod(v)} />
    <Select icon="group" label="Experiment group" value={explorer.family}
      options={[ALL_GROUPS, ...explorer.families]} format={(v) => v || "All experiments"}
      onchange={(v) => explorer.setFamily(v)} />
  </div>
  <h2>{fitQuestion(axis, metric, target, explorer.algorithm)}</h2>
  <p class="meaning">{questions[metric].meaning}</p>
  <div class="plot-panel">
    <div class="chart-header">
      <label class="axis-picker">Y-axis
        <select value={metric} onchange={(e) => { explorer.setQuestion(e.currentTarget.value as typeof metric); explorer.targetValue = 0.5; }}>
          {#each questionKeys as key}<option value={key}>{questions[key].label}</option>{/each}
        </select>
      </label>
      <label class="target-entry">{lowerIsBetter(metric) ? "Maximum" : "Minimum"} target (optional)
        <input type="number" min="0" max="1" step="0.01" inputmode="decimal" placeholder="No target"
          aria-invalid={explorer.targetInvalid} bind:value={explorer.targetValue} />
      </label>
    </div>
    {#if explorer.targetInvalid}<p class="note">Enter a target between 0 and 1.</p>{/if}
    {#if fit}
    <div class="legend"><span class="fit-key"></span>{questions[metric].label} · fitted mean · {lowerIsBetter(metric) ? "0" : "1"} is better
    </div>
    <div class="chart-stage">
    <div class="point-control" role="slider" tabindex="0" aria-label="Selected point on fitted curve"
      aria-valuemin={first} aria-valuemax={last} aria-valuenow={x}
      aria-valuetext={`${x} ${unit}, ${metricLabel} ${format(metric, y)}`} onkeydown={navigatePoint}>
    <EChart id="regression-plot" style="height:clamp(250px,35vw,365px)" label={fitQuestion(axis, metric, target, explorer.algorithm)} {option} replace onready={attach} />
    </div>
    {#if target !== null}
      <div class="target-overlay" style:inset={`${grid.top}px ${grid.right}px ${grid.bottom}px ${grid.left}px`}>
        <div class="target-line" role="slider" tabindex="0" aria-label="Plot target"
          aria-orientation="vertical" aria-valuemin={0} aria-valuemax={1} aria-valuenow={target}
          aria-valuetext={format(metric, target)} style:top={`${100 * (1 - target)}%`}
          onpointerdown={startTargetDrag} onpointermove={moveTarget} onpointerup={finishTargetDrag} onlostpointercapture={() => drag = null}
          onkeydown={stepTarget} title="Drag up or down to adjust the target">
        </div>
      </div>
    {/if}
    </div>
  {:else}
    <p class="empty" role="status">This selection has {levels.length} tested {levels.length === 1 ? "setting" : "settings"} with {questions[metric].label} values. A regression needs at least three. Choose another axis or expand the experiment scope.</p>
  {/if}
    <label class="axis-picker x-picker">X-axis
      <select value={axis} onchange={(e) => { explorer.axis = e.currentTarget.value as AxisKey; readAt = null; }}>
        {#each Object.entries(axes) as [key, label]}<option value={key}>{label}</option>{/each}
      </select>
    </label>
    {#if fit}
    <div class="reading">
      <span class="quality-scale">Worse <i></i> Better</span>
      <p aria-live="polite" id="fit-reading"><strong>At {x} {unit},</strong> {fitAnswer(metric, y)}.
        {#if target !== null}<small>{passes(metric, y, target) ? "Meets the target" : "Misses the target"} of {comparator(metric)} {format(metric, target)}.</small>{/if}
        {#if !tested}<small>Interpolated between tested settings.</small>{/if}
      </p>
    </div>
    {#if fit && target !== null}
      <p class="target-answer">{limit === undefined ? "No tested setting meets the target on the fit." : `The largest tested setting meeting the target is ${limit} ${unit}.`}</p>
    {/if}
    <details class="method">
      <summary>{fit.shape} fit · {levels.length} tested settings</summary>
      <p>At each X value, repetitions are averaged within each configuration, then configurations are weighted equally.
        Each tested X value has equal weight in the regression. We compare constant, linear and logarithmic fits,
        adding a quadratic with at least five settings. The selected fit has the lowest mean absolute error when each setting is held out in turn.
        Estimates are limited to the metric’s 0–1 scale. The held-out mean absolute error is {metric === "success" ? (100 * fit.error).toFixed(1) + " percentage points" : format(metric, fit.error)}.</p>
    </details>
    {/if}
  </div>
</section>

<style>
  .settings { margin-top: 0; }
  .method { color: var(--muted); font-size: .84rem; }
  summary { cursor: pointer; }
  h2 { max-width: 52ch; text-wrap: balance; }
  .meaning { margin: 6px 0 15px; color: var(--muted); }
  .target-answer { margin: 12px 0; font-weight: 650; }
  .legend { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 20px; font-size: .8rem; }
  .fit-key { width: 22px; border-top: 3px solid var(--teal); }
  .reading { display: flex; align-items: center; gap: 14px 25px; flex-wrap: wrap; padding: 14px 18px; margin-bottom: 5px; border-radius: 8px; background: #edf4ef; }
  .reading p { flex: 2 1 240px; }
  .reading small { display: block; color: var(--muted); margin-top: 3px; }
  .method { border-top: 1px solid var(--line); padding-top: 12px; margin-top: 18px; }
  .method p { margin-top: 8px; max-width: 85ch; }
  .empty { padding: 20px 0; }

  .plot-panel { min-width:0; border:1px solid var(--line); border-radius:12px; padding:16px; }
  .chart-header { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:10px; }
  .scope-fields { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%, 165px),1fr)); margin-bottom:16px; }
  .scope-fields :global(label) { min-width:0; }
  .scope-fields :global(select) { text-overflow:ellipsis; }
  .axis-picker { flex-direction:row; display:inline-flex; align-items:center; gap:6px; font-size:.76rem; color:var(--muted); }
  .axis-picker select { width:auto; max-width:100%; min-height:32px; padding-block:3px; font-size:.83rem; }
  .x-picker { display:flex; justify-content:center; }
  .point-control:focus-visible { outline:2px solid var(--teal); outline-offset:2px; }
  .quality-scale { display:inline-flex; align-items:center; gap:6px; font-size:.78rem; color:var(--muted); }
  .quality-scale i { width:54px; height:5px; border-radius:4px; background:linear-gradient(90deg,#c3082c 0% 30%,#8f5b0e 50%,#136d4e); }
  .reading { display:grid; margin-top:12px; padding:12px 0; background:transparent; border-top:1px solid var(--line); border-radius:0; }
  .target-entry { flex-direction:row; align-items:center; flex-wrap:wrap; }
  .target-entry input { width:7rem; border:1px solid #abbdb3; border-radius:6px; padding:7px; color:var(--ink); font:inherit; }
  .chart-stage { position:relative; }
  .target-overlay { position:absolute; pointer-events:none; }
  .target-line { position:absolute; width:100%; height:20px; transform:translateY(-50%); pointer-events:auto;
    cursor:ns-resize; touch-action:none; user-select:none; color:#68449b; display:flex; align-items:center; justify-content:flex-end; }
  .target-line:focus-visible { outline:2px solid currentColor; }
</style>
