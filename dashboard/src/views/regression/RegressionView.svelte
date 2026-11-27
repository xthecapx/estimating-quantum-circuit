<script lang="ts">
  import type { Snippet } from "svelte";
  import type { CustomSeriesRenderItem } from "echarts";
  import PlotTarget from "../PlotTarget.svelte";
  import { targetSeries } from "../../lib/charts/target";
  import EChart from "../../lib/charts/EChart.svelte";
  import { palette, type EChartsType } from "../../lib/charts/echarts";
  import { questions } from "../../lib/domain/catalog";
  import { comparator, format, lowerIsBetter } from "../../lib/domain/format";
  import { passes } from "../../lib/domain/sweep";
  import type { Explorer } from "../../lib/state/explorer.svelte";
  import { averageAnswer, averageQuestion, resourceUnit } from "./questions";

  let { explorer, xPicker }: { explorer: Explorer; xPicker: Snippet } = $props();
  const axis = $derived(explorer.axis);
  const metric = $derived(explorer.question);
  const target = $derived(explorer.threshold);
  const levels = $derived(explorer.levels);
  const first = $derived(levels[0]?.x ?? 0);
  const last = $derived(levels.at(-1)?.x ?? 0);
  function nearest(value: number) {
    return levels.reduce((best, p) => Math.abs(p.x - value) < Math.abs(best.x - value) ? p : best, levels[0]);
  }
  const observed = $derived(explorer.overviewLevel);
  const x = $derived(observed?.x ?? 0);
  const y = $derived(observed?.mean ?? 0);
  const unit = $derived(resourceUnit(axis, explorer.provider));
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
    const index = levels.indexOf(observed);
    const previous = levels[Math.max(0, index - 1)].x;
    const next = levels[Math.min(levels.length - 1, index + 1)].x;
    const positions: Record<string, number> = {
      ArrowLeft: previous, ArrowDown: previous, ArrowRight: next, ArrowUp: next,
      Home: first, End: last,
    };
    if (Object.hasOwn(positions, event.key)) {
      event.preventDefault();
      explorer.readAt = positions[event.key];
    }
  }
  const coverage = $derived.by(() => {
    const lower = levels.map(({ x, min }) => [x, min]);
    const upper = levels.map(({ x, max }) => [x, max]).reverse();
    const bounds = [...lower, ...upper];
    const renderItem: CustomSeriesRenderItem = (_, api) => ({
      type: "polygon",
      shape: { points: bounds.map(point => api.coord(point)) },
      style: { fill: "rgba(56,123,154,.22)", stroke: palette.blue, lineWidth: 1 },
    });
    return { type: "custom", name: "Observed range", silent: true, z: 1, data: [0], renderItem };
  });
  const grid = { top: 22, right: 24, bottom: 28, left: 48, outerBoundsMode: "none" };
  const option = $derived({
    animation: false,
    grid,
    xAxis: { type: "value", min: first === last ? first - 1 : first, max: first === last ? last + 1 : last, minInterval: 1 },
    yAxis: { type: "value", min: 0, max: 1, interval: 0.25,
      axisLabel: { formatter: (v: number) => metric === "success" ? Math.round(v * 100) + "%" : String(v) } },
    series: [
      coverage,
      targetSeries(metric, target, first === last ? first - 1 : first, first === last ? last + 1 : last),
      { type: "line", name: "Average", symbol: "circle", symbolSize: 6, itemStyle: { color: palette.teal }, lineStyle: { width: 2, color: palette.teal }, data: levels.map(p => [p.x, p.mean]) },
      { type: "scatter", name: "Selected average", z: 8, symbolSize: 15, itemStyle: { opacity: 1, color: pointColor, borderColor: "#fff", borderWidth: 2 }, data: [[x, y]],
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
      explorer.readAt = nearest(value[0]).x;
    });
  }
</script>

<section aria-label="Operating range overview">
    {#if levels.length}
    <PlotTarget {explorer} {grid}>
    <div class="point-control" role="slider" tabindex="0" aria-label="Selected tested setting"
      aria-valuemin={first} aria-valuemax={last} aria-valuenow={x}
      aria-valuetext={`${x} ${unit}, ${metricLabel} ${format(metric, y)}`} onkeydown={navigatePoint}>
    <EChart id="average-plot" style="height:clamp(250px,35vw,365px)" label={averageQuestion(axis, metric, target)} {option} replace onready={attach} />
    </div>
    </PlotTarget>
  {:else}
    <p class="empty" role="status">This selection has no measured {questions[metric].label} values. Choose another axis or expand the experiment scope.</p>
  {/if}
    {@render xPicker()}
    {#if observed}
    <div class="reading">
      <span class="quality-scale">Worse <i></i> Better</span>
      <p aria-live="polite" id="average-reading"><strong>At {x} {unit},</strong> {averageAnswer(metric, y)}.
        {#if target !== null}<small>{passes(metric, y, target) ? "Meets the target" : "Misses the target"} of {comparator(metric)} {format(metric, target)}.</small>{/if}
          <small>Observed best {format(metric, lowerIsBetter(metric) ? observed.min : observed.max)} · worst {format(metric, lowerIsBetter(metric) ? observed.max : observed.min)}</small>
      </p>
    </div>
    {/if}
</section>

<style>
  .reading { display: flex; align-items: center; gap: 14px 25px; flex-wrap: wrap; padding: 14px 18px; margin-bottom: 5px; border-radius: 8px; background: #edf4ef; }
  .reading p { flex: 2 1 240px; }
  .reading small { display: block; color: var(--muted); margin-top: 3px; }
  .empty { padding: 20px 0; }

  .point-control:focus-visible { outline:2px solid var(--teal); outline-offset:2px; }
  .quality-scale { display:inline-flex; align-items:center; gap:6px; font-size:.78rem; color:var(--muted); }
  .quality-scale i { width:54px; height:5px; border-radius:4px; background:linear-gradient(90deg,#c3082c 0% 30%,#8f5b0e 50%,#136d4e); }
  .reading { display:grid; margin-top:12px; padding:12px 0; background:transparent; border-top:1px solid var(--line); border-radius:0; }
</style>
