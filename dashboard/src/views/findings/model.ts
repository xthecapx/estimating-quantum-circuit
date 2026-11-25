/**
 * Findings: the summary page. Everything is read from two snapshots that the Python
 * pipeline writes (estimation scopes + the model comparison on the validation run);
 * nothing is computed here beyond picking rows.
 */
import { palette, type EChartsCoreOption } from "../../lib/charts/echarts";
import { algorithmName } from "../../lib/domain/catalog";
import type { EstimationSnapshot } from "../estimation/model";

export interface ComparisonRow {
  target: string;
  model: string;
  label: string;
  chip: string;
  seenChip: boolean;
  group: "all" | "new" | "anchor" | "extrapolation";
  jobs: number;
  configs: number;
  r2: number | null;
  r2CiLow: number | null;
  r2CiHigh: number | null;
  mae: number | null;
}
export interface Contrast {
  target: string;
  against: string;
  label: string;
  diff: number;
  ciLow: number;
  ciHigh: number;
}
export interface ComparisonPoint {
  target: string;
  chip: string;
  config: string;
  group: "new" | "anchor" | "extrapolation";
  algorithm: string;
  twoQubitGates: number;
  jobs: number;
  observed: number;
  predicted: number;
}
export interface ComparisonSnapshot {
  schemaVersion: number;
  backend: string;
  manifestHash: string;
  inputs: Record<string, string>;
  status: string;
  best: string;
  labels: Record<string, string>;
  jobs: number;
  chips: string[];
  trainedChips: string[];
  rows: ComparisonRow[];
  contrasts: Contrast[];
  points: ComparisonPoint[];
}

export const BAR = 0.8;

/** Plain-language names. The professor reads these; keep them free of jargon. */
export const TARGETS: Record<string, { name: string; plain: string }> = {
  success: { name: "Success rate", plain: "share of runs that return a correct answer" },
  hellinger: { name: "Hellinger fidelity", plain: "how close the measured results are to the ideal ones (1 = identical)" },
  tvd: { name: "Total variation distance", plain: "how far the measured results are from the ideal ones (0 = identical)" },
  dsr: { name: "Differential success rate", plain: "how clearly the correct answer stands out from the strongest wrong one" },
};
export const TARGET_ORDER = ["success", "hellinger", "tvd", "dsr"] as const;

export const CHIPS: Record<string, string> = {
  ibm_fez: "IBM Fez",
  ibm_kingston: "IBM Kingston",
  ibm_marrakesh: "IBM Marrakesh",
};
export const chipName = (id: string) => CHIPS[id] ?? id;

export const MODELS: Record<string, { name: string; role: string; plain: string }> = {
  per_chip: {
    name: "One model per chip",
    role: "Best",
    plain: "Trained only on that chip's own runs. For a chip with no runs it falls back to the shared model.",
  },
  pooled: {
    name: "One shared model",
    role: "For a new chip",
    plain: "Trained on all chips together, without knowing which chip a circuit runs on.",
  },
  pooled_chip: {
    name: "Shared model + chip name",
    role: "Candidate",
    plain: "The shared model, also told which chip the circuit runs on. To be re-tested when more chips are added.",
  },
  size: {
    name: "Circuit size only",
    role: "Baseline",
    plain: "Four plain counts: two-qubit gates, depth, qubits, measurements. The bar a richer model has to beat.",
  },
  mixed: {
    name: "Per chip + calibration data",
    role: "Tested, not kept",
    plain: "The per-chip model plus the chip's published error rates on the day.",
  },
};
export const MODEL_ORDER = ["per_chip", "pooled", "pooled_chip", "size", "mixed"] as const;

/** Reference categorical slots, validated on the white card surface (see dataviz validator). */
export const SERIES = { blue: "#2a78d6", orange: "#eb6834", aqua: "#1baf7a" };
export const GROUPS = {
  anchor: { name: "Circuits seen in training", color: SERIES.blue, symbol: "circle" },
  new: { name: "New circuits", color: SERIES.orange, symbol: "diamond" },
  extrapolation: { name: "Larger than any trained circuit", color: SERIES.aqua, symbol: "triangle" },
} as const;

export const fmt = (v: number | null | undefined, digits = 2) =>
  v == null || !Number.isFinite(v) ? "—" : v.toFixed(digits);
/** A 0–1 quality error as "± N points" on the 0–100 scale. */
export const points = (mae: number | null | undefined) =>
  mae == null ? "—" : `${(mae * 100).toFixed(1)} points`;

export function row(data: ComparisonSnapshot, model: string, target: string, chip: string, group = "all") {
  return data.rows.find((r) => r.model === model && r.target === target && r.chip === chip && r.group === group);
}
export function contrast(data: ComparisonSnapshot, target: string, against: string) {
  return data.contrasts.find((c) => c.target === target && c.against === against);
}
export type Reading = "better" | "worse" | "same";
/** Reads a paired difference "best minus alternative": does the best model really win? */
export function reading(c: Contrast | undefined): Reading {
  if (!c) return "same";
  return c.ciLow > 0 ? "better" : c.ciHigh < 0 ? "worse" : "same";
}

export type Status = "yes" | "partly" | "no" | "waiting";
export const STATUS_LABEL: Record<Status, string> = {
  yes: "Supported",
  partly: "Partly supported",
  no: "Not supported",
  waiting: "Waiting for data",
};

/** Predicted vs measured, one dot per circuit; the diagonal is a perfect prediction. */
export function parityChart(pts: ComparisonPoint[], targetName: string): EChartsCoreOption {
  const axis = (name: string, gap: number) => ({
    type: "value", min: 0, max: 1, name, nameLocation: "middle", nameGap: gap,
    nameTextStyle: { color: palette.ink },
    axisLabel: { color: palette.ink, formatter: (v: number) => `${Math.round(v * 100)}%` },
    splitLine: { lineStyle: { color: palette.edge, width: 1 } },
  });
  return {
    grid: { top: 12, left: 58, right: 14, bottom: 46 },
    tooltip: {
      trigger: "item", confine: true,
      formatter: (params: unknown) => {
        const pt = (params as { data?: { pt?: ComparisonPoint } }).data?.pt;
        if (!pt) return "";
        const err = (pt.predicted - pt.observed) * 100;
        return `<b>${algorithmName(pt.algorithm)} · ${pt.config}</b><br/>${GROUPS[pt.group].name}<br/>` +
          `Measured ${(pt.observed * 100).toFixed(1)}% · Predicted ${(pt.predicted * 100).toFixed(1)}%<br/>` +
          `Off by ${err >= 0 ? "+" : ""}${err.toFixed(1)} points · ${Math.round(pt.twoQubitGates)} two-qubit gates`;
      },
    },
    xAxis: axis(`Measured on the chip (${targetName.toLowerCase()})`, 30),
    yAxis: axis("Predicted before running", 42),
    series: [
      {
        type: "line", name: "Perfect prediction", data: [[0, 0], [1, 1]], showSymbol: false, silent: true,
        lineStyle: { color: palette.muted, width: 1 },
      },
      ...(Object.keys(GROUPS) as (keyof typeof GROUPS)[]).map((g) => ({
        type: "scatter", name: GROUPS[g].name, symbol: GROUPS[g].symbol, symbolSize: g === "anchor" ? 9 : 11,
        itemStyle: { color: GROUPS[g].color, opacity: 0.9, borderColor: "#fff", borderWidth: 1.5 },
        data: pts.filter((p) => p.group === g).map((p) => ({ value: [+p.observed.toFixed(4), +p.predicted.toFixed(4)], pt: p })),
      })),
    ],
  };
}

export interface ScoreBar { label: string; r2: number | null; low: number | null; high: number | null; note?: string; highlight?: boolean }

/** Score with its 95% interval per row, and the 0.80 bar. One series: the title names it. */
export function scoreChart(rows: ScoreBar[], opts: { bar?: number; ceiling?: (number | null)[] } = {}): EChartsCoreOption {
  const vals = rows.flatMap((r) => [r.r2, r.low]).filter((v): v is number => v != null);
  const min = Math.min(0, Math.floor((Math.min(...vals, 0.4) - 0.05) * 10) / 10);
  const clamp = (v: number | null) => (v == null ? null : Math.max(v, min));
  return {
    grid: { top: 8, left: 4, right: 18, bottom: 40, containLabel: true },
    tooltip: {
      trigger: "item", confine: true,
      formatter: (params: unknown) => {
        const r = rows[(params as { dataIndex: number }).dataIndex];
        if (!r) return "";
        return `<b>${r.label.replace("\n", " · ")}</b><br/>Score ${fmt(r.r2)} (likely range ${fmt(r.low)} to ${fmt(r.high)})` +
          (r.note ? `<br/>${r.note}` : "");
      },
    },
    xAxis: {
      type: "value", min, max: 1, name: "Prediction score (R²) · 1 = perfect", nameLocation: "middle", nameGap: 26,
      nameTextStyle: { color: palette.ink }, axisLabel: { color: palette.ink },
      splitLine: { lineStyle: { color: palette.edge, width: 1 } },
    },
    yAxis: {
      type: "category", data: rows.map((r) => r.label), inverse: true, axisTick: { show: false },
      axisLine: { lineStyle: { color: palette.edge } },
      axisLabel: { color: palette.ink, fontSize: 12, lineHeight: 15 },
    },
    series: [
      { type: "bar", stack: "ci", silent: true, itemStyle: { color: "transparent" }, barWidth: 8, data: rows.map((r) => clamp(r.low)) },
      {
        type: "bar", stack: "ci", name: "Likely range", barWidth: 8,
        itemStyle: { color: "rgba(42,120,214,.26)", borderRadius: 4 },
        data: rows.map((r) => (r.low == null || r.high == null ? null : r.high - Math.max(r.low, min))),
      },
      ...(opts.ceiling
        ? [{
            type: "scatter", name: "Best any model could reach", symbol: "rect", symbolSize: [3, 18], z: 3,
            itemStyle: { color: palette.ink }, data: opts.ceiling,
          }]
        : []),
      {
        type: "scatter", name: "Score", symbolSize: 13, z: 4,
        itemStyle: { color: SERIES.blue, borderColor: "#fff", borderWidth: 2 },
        data: rows.map((r) => clamp(r.r2)),
        markLine: {
          silent: true, symbol: "none", label: { show: false },
          lineStyle: { color: palette.threshold, width: 1.5, type: "dashed" },
          data: [{ xAxis: opts.bar ?? BAR }],
        },
      },
    ],
  };
}

/** Everything the page needs from the training-side snapshots, per trained chip. */
export function trainingRow(snap: EstimationSnapshot | undefined, target: string) {
  const t = snap?.targets?.[target] as Record<string, any> | undefined;
  if (!t) return undefined;
  const cv = t.leaderboard?.[0]?.cv ?? {};
  const d = t.diagnostics ?? {};
  return {
    r2: cv.r2 as number | null, low: cv.r2CiLow as number | null, high: cv.r2CiHigh as number | null,
    verdict: cv.h1Verdict as string | undefined,
    ceiling: d.noiseCeiling?.looReplicateR2 as number | null | undefined,
    configMean: d.configMean?.r2 as number | null | undefined,
    size: d.sizeBaseline?.r2 as number | null | undefined,
    withAnchor: d.subsets?.allJobs?.r2 as number | null | undefined,
    perAlgorithm: (d.perAlgorithm ?? []) as { algorithm: string; r2: number | null; configs: number; observedMean: number }[],
    h2: (t.h2 ?? []) as Record<string, any>[],
    h3: (t.h3?.regimes ?? []) as Record<string, any>[],
    temporal: (t.h3?.temporal?.regimes ?? []) as Record<string, any>[],
    h4Contrasts: (t.h4Contrasts ?? []) as Record<string, any>[],
    stable: (t.stableFootprintFeatures ?? []) as { feature: string; selectionFrequency: number }[],
    footprint: (t.selectedFootprintFeatures ?? []) as string[],
    providerTransfer: t.h3?.providerTransfer as { status: string } | undefined,
  };
}
