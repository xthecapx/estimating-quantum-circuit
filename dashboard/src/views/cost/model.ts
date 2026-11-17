import { algorithmName } from "../../lib/domain/catalog";
import { palette, type EChartsCoreOption } from "../../lib/charts/echarts";

export interface CostMetrics {
  n: number;
  r2: number | null;
  maeSeconds: number;
  maeMilliseconds: number;
  mapePercent: number;
  biasSeconds: number;
  maxErrorSeconds: number;
  billedSecondsAccuracy?: number;
  r2Sd?: number;
}

export interface PhysicalTerms {
  overheadSeconds: number;
  twirlingOverheadSeconds: number;
  perShotSeconds: number;
  durationSlope: number;
  twirlingDurationSlope: number;
  twirlingPerShotSeconds: number;
  circuitTimeMaeMilliseconds: number;
}

export interface CostPoint {
  backend: string;
  config_id: string;
  algorithm: string;
  observed: number;
  predicted: number;
  duration: number | null;
  circuit: number;
  whole: number;
  jobs: number;
  twirling: number;
  dynamic: number;
  depth: number | null;
  split: "unseen_circuit" | "new_run";
}

export interface CostProfile {
  algorithm: string;
  jobs: number;
  medianSeconds: number;
  maxSeconds: number;
  medianCircuitSeconds: number;
  threeSecondShare: number;
}

export interface CostSnapshot {
  schemaVersion: number;
  backend: string;
  secondsPerRu: number;
  ibmRule: { overheadSeconds: number; perExecutionSeconds: number };
  jobs: { total: number; training: number; newRun: number; withoutRu: number; chips: string[]; shots: number[] };
  observed: {
    medianSeconds: number;
    medianRus: number;
    medianCircuitSeconds: number;
    overheadShare: number;
    threeSecondShare: number;
    totalRus: number;
  };
  primaryModel: string;
  physicalTerms: PhysicalTerms;
  unseenCircuit: { nSplits: number; nRepeats: number; metrics: Record<string, CostMetrics> };
  newRun: Record<string, Record<string, CostMetrics>>;
  profile: CostProfile[];
  points: CostPoint[];
}

export const CHIP_LABELS: Record<string, string> = {
  ibm_fez: "IBM Fez",
  ibm_kingston: "IBM Kingston",
  ibm_marrakesh: "IBM Marrakesh",
  all: "All three chips",
};

/** Two validated categorical slots (dataviz validator, light card surface): model = blue, IBM rule = orange. */
export const COLOR = { model: "#2a78d6", ibm: "#eb6834" };

export function fmt(value: number | null | undefined, digits = 2): string {
  return value == null || !Number.isFinite(value) ? "—" : value.toFixed(digits);
}

/** Physical-model cost of one job at a given shot count (seconds). */
export function physicalSeconds(t: PhysicalTerms, shots: number, durationSeconds: number, twirling: boolean): number {
  const perShot =
    t.perShotSeconds + t.durationSlope * durationSeconds + (twirling ? t.twirlingPerShotSeconds + t.twirlingDurationSlope * durationSeconds : 0);
  return t.overheadSeconds + (twirling ? t.twirlingOverheadSeconds : 0) + shots * perShot;
}

/** IBM's published rule of thumb: ~2 s per job + 350 µs per circuit execution. */
export function ibmRuleSeconds(rule: CostSnapshot["ibmRule"], shots: number): number {
  return rule.overheadSeconds + rule.perExecutionSeconds * shots;
}

/** IBM bills whole seconds, rounded up. */
export function billedWholeSeconds(seconds: number): number {
  return Math.ceil(seconds - 1e-9);
}

/** Observed vs predicted billed seconds, one marker per circuit; shape = twirled or not. */
export function costParityChart(points: CostPoint[]): EChartsCoreOption {
  const vals = points.flatMap((p) => [p.observed, p.predicted]);
  const lo = Math.floor((Math.min(...vals) - 0.005) * 50) / 50;
  const hi = Math.ceil((Math.max(...vals) + 0.005) * 50) / 50;
  const series = [
    { key: 0, name: "Standard jobs", symbol: "circle", size: 8 },
    { key: 1, name: "Twirled jobs (Shor)", symbol: "diamond", size: 10 },
  ];
  return {
    grid: { top: 16, left: 62, right: 16, bottom: 48 },
    tooltip: {
      trigger: "item",
      confine: true,
      formatter: (params: unknown) => {
        const pt = (params as { data?: { pt: CostPoint } }).data?.pt;
        if (!pt) return "";
        const err = (pt.predicted - pt.observed) * 1e3;
        return (
          `<b>${algorithmName(pt.algorithm)} · ${pt.config_id}</b><br/>${CHIP_LABELS[pt.backend] ?? pt.backend}` +
          `${pt.duration != null ? ` · ${(pt.duration * 1e6).toFixed(1)} µs per shot` : " · dynamic circuit"}<br/>` +
          `Billed ${pt.observed.toFixed(3)} s · predicted ${pt.predicted.toFixed(3)} s (${err >= 0 ? "+" : ""}${err.toFixed(1)} ms)<br/>` +
          `Charged ${pt.whole} whole s · circuit ran ${pt.circuit.toFixed(3)} s`
        );
      },
    },
    xAxis: {
      type: "value", min: lo, max: hi, interval: 0.02, name: "Billed QPU time (s)", nameLocation: "middle", nameGap: 28,
      splitLine: { lineStyle: { color: palette.edge, width: 1 } }, axisLabel: { formatter: (v: number) => v.toFixed(2) },
    },
    yAxis: {
      type: "value", min: lo, max: hi, interval: 0.02, name: "Predicted before running (s)", nameLocation: "middle", nameGap: 46,
      splitLine: { lineStyle: { color: palette.edge, width: 1 } }, axisLabel: { formatter: (v: number) => v.toFixed(2) },
    },
    series: [
      { type: "line", name: "Perfect prediction", data: [[lo, lo], [hi, hi]], showSymbol: false, silent: true, lineStyle: { color: palette.muted, width: 1 } },
      ...series.map((s) => ({
        type: "scatter",
        name: s.name,
        symbol: s.symbol,
        symbolSize: s.size,
        itemStyle: { color: COLOR.model, opacity: 0.85, borderColor: "#fff", borderWidth: 1.5 },
        data: points.filter((p) => p.twirling === s.key).map((p) => ({ value: [+p.observed.toFixed(4), +p.predicted.toFixed(4)], pt: p })),
      })),
    ],
  };
}

/** Billed time vs scheduled per-shot duration: observed circuits and the physical model line. */
export function durationChart(points: CostPoint[], t: PhysicalTerms, shots: number): EChartsCoreOption {
  const statics = points.filter((p) => p.duration != null);
  const maxUs = Math.max(...statics.map((p) => p.duration! * 1e6), 1);
  const line = (tw: boolean) =>
    Array.from({ length: 41 }, (_, i) => {
      const us = (maxUs * 1.05 * i) / 40;
      return [+us.toFixed(2), +physicalSeconds(t, shots, us * 1e-6, tw).toFixed(4)];
    });
  return {
    grid: { top: 16, left: 62, right: 16, bottom: 48 },
    tooltip: {
      trigger: "item",
      confine: true,
      formatter: (params: unknown) => {
        const pt = (params as { data?: { pt: CostPoint } }).data?.pt;
        if (!pt) return "";
        return `<b>${algorithmName(pt.algorithm)} · ${pt.config_id}</b><br/>${(pt.duration! * 1e6).toFixed(1)} µs per shot · billed ${pt.observed.toFixed(3)} s`;
      },
    },
    xAxis: {
      type: "value", min: 0, name: "Scheduled duration of one shot (µs)", nameLocation: "middle", nameGap: 28,
      splitLine: { lineStyle: { color: palette.edge, width: 1 } },
    },
    yAxis: {
      type: "value", scale: true, name: "Billed QPU time (s)", nameLocation: "middle", nameGap: 46,
      splitLine: { lineStyle: { color: palette.edge, width: 1 } },
      axisLabel: { formatter: (v: number) => v.toFixed(2) },
    },
    series: [
      {
        type: "scatter", name: "Standard jobs", symbol: "circle", symbolSize: 7,
        itemStyle: { color: COLOR.model, opacity: 0.55 },
        data: statics.filter((p) => !p.twirling).map((p) => ({ value: [+(p.duration! * 1e6).toFixed(2), +p.observed.toFixed(4)], pt: p })),
      },
      {
        type: "scatter", name: "Twirled jobs (Shor)", symbol: "diamond", symbolSize: 9,
        itemStyle: { color: COLOR.model, opacity: 0.85, borderColor: "#fff", borderWidth: 1 },
        data: statics.filter((p) => p.twirling).map((p) => ({ value: [+(p.duration! * 1e6).toFixed(2), +p.observed.toFixed(4)], pt: p })),
      },
      { type: "line", name: "Model, standard", data: line(false), showSymbol: false, silent: true, lineStyle: { color: palette.ink, width: 2 } },
      { type: "line", name: "Model, twirled", data: line(true), showSymbol: false, silent: true, lineStyle: { color: palette.ink, width: 1.5, type: "dotted" } },
    ],
  };
}

/** Cost vs shot count for one circuit: QAQS physical model and IBM's rule, one axis (RU). */
export function shotsChart(
  t: PhysicalTerms,
  rule: CostSnapshot["ibmRule"],
  durationSeconds: number,
  twirling: boolean,
  secondsPerRu: number,
  chosen: number,
): EChartsCoreOption {
  const shots = [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536];
  const ru = (s: number) => s / secondsPerRu;
  return {
    grid: { top: 16, left: 66, right: 20, bottom: 52 },
    tooltip: {
      trigger: "axis",
      confine: true,
      valueFormatter: (v: unknown) => `${(+(v as number)).toFixed(4)} RU`,
    },
    xAxis: {
      type: "log", logBase: 2, min: 128, max: 65536, name: "Shots per job (log scale)", nameLocation: "middle", nameGap: 30,
      splitLine: { lineStyle: { color: palette.edge, width: 1 } },
      axisLabel: { formatter: (v: number) => (v >= 1024 ? `${v / 1024}k` : `${v}`) },
    },
    yAxis: {
      type: "value", min: 0, name: "Resource units per job", nameLocation: "middle", nameGap: 50,
      splitLine: { lineStyle: { color: palette.edge, width: 1 } },
    },
    series: [
      {
        type: "line", name: "QAQS cost model", showSymbol: false,
        lineStyle: { color: COLOR.model, width: 2 }, itemStyle: { color: COLOR.model },
        data: shots.map((s) => [s, +ru(physicalSeconds(t, s, durationSeconds, twirling)).toFixed(5)]),
        markLine: {
          silent: true, symbol: "none",
          lineStyle: { color: palette.muted, width: 1, type: "solid" },
          label: { show: true, position: "insideEndTop", color: palette.ink, fontSize: 10 },
          data: [
            { xAxis: 1024, label: { formatter: "measured" } },
            ...(chosen !== 1024 ? [{ xAxis: chosen, label: { formatter: "your choice" } }] : []),
          ],
        },
      },
      {
        type: "line", name: "IBM rule of thumb", showSymbol: false,
        lineStyle: { color: COLOR.ibm, width: 2 }, itemStyle: { color: COLOR.ibm },
        data: shots.map((s) => [s, +ru(ibmRuleSeconds(rule, s)).toFixed(5)]),
      },
    ],
  };
}
