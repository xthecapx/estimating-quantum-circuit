<script lang="ts">
  import PlotTarget from "../PlotTarget.svelte";
  import { targetSeries } from "../../lib/charts/target";
  import EChart from "../../lib/charts/EChart.svelte";
  import { palette, type EChartsType } from "../../lib/charts/echarts";
  import type { Job } from "../../lib/data/types";
  import { questions } from "../../lib/domain/catalog";
  import { unique } from "../../lib/domain/format";
  import { sweepAxis } from "../../lib/domain/sweep";
  import type { Explorer } from "../../lib/state/explorer.svelte";
  import IntervalLens, { type LensPoint } from "./IntervalLens.svelte";

  let { explorer }: { explorer: Explorer } = $props();

  let chart = $state<EChartsType>();
  let hovered = $state<LensPoint | null>(null);

  const showIntervals = $derived(explorer.question === "success");

  const grid = { left: 58, right: 18, top: 16, bottom: 28, outerBoundsMode: "none" };
  const option = $derived.by(() => {
    const { jobs, configs, axis, question: key, threshold, summary } = explorer;
    const dots = jobs
      .filter((j) => j[key] != null)
      .map((j) => ({ value: [j[axis], j[key] as number], job: j }));
    const boundary = summary.boundary;
    const shade =
      boundary != null && axis === sweepAxis(configs)
        ? [[{ xAxis: configs[boundary - 1][0][axis] }, { xAxis: configs[boundary][0][axis] }]]
        : [];
    const axisValues = unique(jobs.map((j) => j[axis]));
    const min = axisValues.length ? Math.max(0, Math.min(...axisValues) - 1) : 0;
    const max = axisValues.length ? Math.max(...axisValues) + 1 : 1;
    return {
      animation: false,
      grid,
      tooltip: { show: false },
      xAxis: {
        type: "value",
        min, max,
        minInterval: 1,
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 1,
        interval: showIntervals ? 0.1 : 0.25,
        axisLabel: {
          formatter: (v: number) => (key === "success" ? Math.round(v * 100) + "%" : String(v)),
        },
      },
      series: [
        targetSeries(key, threshold, min, max),
        {
          name: questions[key].label,
          type: "scatter",
          symbolSize: showIntervals ? 7 : 11,
          z: 3,
          itemStyle: { color: palette.teal },
          emphasis: { scale: false, itemStyle: { color: palette.accent, opacity: 1 } },
          data: dots,
          markArea: { silent: true, itemStyle: { color: palette.band }, data: shade },
        },
      ],
    };
  });

  // Any change of plotted data, or leaving the view, hides a stale lens.
  $effect(() => {
    void option;
    void explorer.view;
    hovered = null;
  });

  function ready(instance: EChartsType) {
    chart = instance;
    type Event = { data: { value: [number, number]; job: Job } };
    instance.on("mouseover", { seriesType: "scatter" }, (event) => {
      const { data } = event as unknown as Event;
      hovered = { job: data.job, value: data.value };
    });
    instance.on("mouseout", { seriesType: "scatter" }, () => {
      hovered = null;
    });
    instance.on("click", { seriesType: "scatter" }, (event) => {
      const { data } = event as unknown as Event;
      void explorer.openJob(data.job, document.getElementById("plot-title"));
    });
  }
</script>

<PlotTarget {explorer} {grid}>
  <EChart
    id="trend"
    class="plot"
    label={questions[explorer.question].label + " by " + explorer.axisLabels[explorer.axis].toLowerCase()}
    {option}
    replace
    onready={ready}
  />
  {#if hovered && chart}
    <IntervalLens {explorer} {chart} point={hovered} {showIntervals} />
  {/if}
</PlotTarget>
