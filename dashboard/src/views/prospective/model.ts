import { algorithmName } from "../../lib/domain/catalog";
import { palette, type EChartsCoreOption } from "../../lib/charts/echarts";

export type Group = "anchor" | "new" | "extrapolation";
export type Verdict = "pass" | "fail" | "inconclusive";

export interface ChipRun {
  backend: string;
  qpu: "seen" | "unseen";
  campaignId: string;
  createdAt: string;
  gitCommit: string | null;
  jobs: number;
  configs: number;
  executedFrom: string;
  executedTo: string;
  trainingChips: string[];
}

export interface ScoreRow {
  backend: string;
  qpu: "seen" | "unseen";
  scope: string;
  transfer: string;
  target: string;
  regime: "circuit_only" | "mixed_submit";
  model: string | null;
  group: Group | "all";
  jobs: number;
  configs: number;
  r2: number | null;
  r2CiLow: number | null;
  r2CiHigh: number | null;
  mae: number | null;
  rmse: number | null;
  spearmanRho: number | null;
  h1Verdict: Verdict;
  /** Unseen-circuit validation (repeated grouped K-fold on training data) of the same frozen model. */
  trainingR2: number | null;
  trainingMae: number | null;
}

export interface PointRow {
  backend: string;
  scope: string;
  target: string;
  regime: string;
  config: string;
  group: Group;
  observed: number;
  predicted: number;
  jobs: number;
  algorithm: string;
  twoQubitGates: number | null;
  qubits: number | null;
}

export interface ProspectiveSnapshot {
  schemaVersion: number;
  backend: string;
  groups: Group[];
  chips: ChipRun[];
  scores: ScoreRow[];
  points: PointRow[];
}

export const H1_THRESHOLD = 0.8;

export const TARGET_LABELS: Record<string, string> = {
  success: "Success rate",
  hellinger: "Hellinger fidelity",
  tvd: "Total variation distance",
  dsr: "Differential success rate (DSR)",
};

export const GROUP_LABELS: Record<Group, string> = {
  anchor: "Known circuits",
  new: "New circuits",
  extrapolation: "Larger circuits",
};

export const GROUP_HELP: Record<Group, string> = {
  anchor: "Circuits already in the training data, run in a new calibration cycle. Isolates calibration drift.",
  new: "Circuits never executed before, within the measured size range. The pre-registered H1 test.",
  extrapolation: "Circuits with more two-qubit gates than any measured one. Tests scaling (H2).",
};

export const REGIME_LABELS: Record<string, string> = {
  circuit_only: "Circuit footprint only",
  mixed_submit: "Footprint + calibration",
};

export const CHIP_LABELS: Record<string, string> = {
  ibm_fez: "IBM Fez",
  ibm_kingston: "IBM Kingston",
  ibm_marrakesh: "IBM Marrakesh",
  pooled: "Pooled (Fez + Kingston)",
};

export const VERDICT_LABELS: Record<Verdict, string> = {
  pass: "Pass",
  fail: "Fail",
  inconclusive: "Inconclusive",
};

/**
 * Categorical slots from the reference palette, checked with the dataviz validator on the
 * white card surface: blue/orange pass every check; blue/orange/aqua pass all-pairs with a
 * contrast WARN on aqua, so the scatter always shows a legend, a distinct shape per group
 * and a table of the same numbers.
 */
export const SERIES = {
  prospective: "#2a78d6",
  reference: "#eb6834",
};

/** Marker shape per group so identity never depends on color alone. */
export const GROUP_SYMBOL: Record<Group, string> = {
  anchor: "circle",
  new: "diamond",
  extrapolation: "triangle",
};
export const GROUP_COLOR: Record<Group, string> = {
  anchor: "#2a78d6",
  new: "#eb6834",
  extrapolation: "#1baf7a",
};

/** The model that is the headline for each chip: same-chip for seen, best single transfer source otherwise. */
export function modelsFor(chip: ChipRun, scores: ScoreRow[]): string[] {
  const scopes = [...new Set(scores.filter((s) => s.backend === chip.backend).map((s) => s.scope))];
  const order = (scope: string) =>
    scope === chip.backend ? 0 : scope === "pooled" ? 1 : 2 + scopes.indexOf(scope);
  return scopes.sort((a, b) => order(a) - order(b));
}

export function findScore(
  scores: ScoreRow[],
  q: Pick<ScoreRow, "backend" | "scope" | "target" | "regime"> & { group: ScoreRow["group"] },
): ScoreRow | undefined {
  return scores.find(
    (s) =>
      s.backend === q.backend && s.scope === q.scope && s.target === q.target && s.regime === q.regime && s.group === q.group,
  );
}

export function transferLabel(chip: ChipRun, scope: string): string {
  if (scope === chip.backend) return "trained on this chip";
  if (scope === "pooled") return chip.qpu === "unseen" ? "zero-shot, pooled model" : "pooled model";
  return `zero-shot from ${CHIP_LABELS[scope] ?? scope}`;
}

export function fmt(value: number | null | undefined, digits = 2): string {
  return value == null || !Number.isFinite(value) ? "—" : value.toFixed(digits);
}

/**
 * Dot-and-interval chart: one row per chip/model; prospective R² with its 95% CI (blue),
 * and the unseen-circuit validation R² of the same frozen model (orange diamond) for reference.
 * One x-axis (R²), threshold line at 0.80.
 */
export function intervalChart(
  rows: { label: string; score?: ScoreRow }[],
  threshold = H1_THRESHOLD,
): EChartsCoreOption {
  const labels = rows.map((r) => r.label);
  const lows = rows.map((r) => r.score?.r2CiLow ?? null);
  const highs = rows.map((r) => r.score?.r2CiHigh ?? null);
  const all = [...lows, ...highs, ...rows.map((r) => r.score?.r2 ?? null), ...rows.map((r) => r.score?.trainingR2 ?? null)]
    .filter((v): v is number => v != null && Number.isFinite(v));
  const min = Math.min(0, Math.floor((Math.min(...all, 0.5) - 0.05) * 10) / 10);
  return {
    grid: { top: 22, left: 4, right: 16, bottom: 40, containLabel: true },
    tooltip: {
      trigger: "item",
      confine: true,
      formatter: (params: unknown) => {
        const p = params as { dataIndex: number };
        const s = rows[p.dataIndex]?.score;
        if (!s) return "";
        return (
          `<b>${rows[p.dataIndex].label}</b><br/>` +
          `New-run R² ${fmt(s.r2, 3)} [${fmt(s.r2CiLow)}, ${fmt(s.r2CiHigh)}] · MAE ${fmt(s.mae, 3)}<br/>` +
          `Training-data validation R² ${fmt(s.trainingR2, 3)}<br/>` +
          `${s.configs} circuits / ${s.jobs} jobs · ${VERDICT_LABELS[s.h1Verdict]}`
        );
      },
    },
    xAxis: {
      type: "value",
      min,
      max: 1,
      name: "R² (higher is better)",
      nameLocation: "middle",
      nameGap: 26,
      splitLine: { lineStyle: { color: palette.edge, width: 1 } },
      splitNumber: 4,
      axisLabel: { color: palette.ink, hideOverlap: true },
    },
    yAxis: {
      type: "category",
      data: labels,
      inverse: true,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: palette.edge } },
      axisLabel: { color: palette.ink, fontSize: 11, lineHeight: 14, width: 110, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        name: "ci-base",
        stack: "ci",
        silent: true,
        itemStyle: { color: "transparent" },
        data: lows.map((v) => (v == null ? null : Math.max(v, min))),
        barWidth: 6,
      },
      {
        type: "bar",
        name: "95% CI",
        stack: "ci",
        itemStyle: { color: "rgba(42,120,214,.28)", borderRadius: 3 },
        data: highs.map((h, i) => (h == null || lows[i] == null ? null : h - Math.max(lows[i]!, min))),
        barWidth: 6,
      },
      {
        type: "scatter",
        name: "Training-data validation",
        symbol: "diamond",
        symbolSize: 10,
        itemStyle: { color: SERIES.reference, borderColor: "#fff", borderWidth: 2 },
        data: rows.map((r) => r.score?.trainingR2 ?? null),
        z: 3,
      },
      {
        type: "scatter",
        name: "New-run R²",
        symbolSize: 11,
        itemStyle: { color: SERIES.prospective, borderColor: "#fff", borderWidth: 2 },
        data: rows.map((r) => r.score?.r2 ?? null),
        markLine: {
          silent: true,
          symbol: "none",
          label: { show: false },
          lineStyle: { color: palette.threshold, width: 1, type: "solid" },
          data: [{ xAxis: threshold }],
        },
        z: 4,
      },
    ],
  };
}

/** Observed vs pre-registered prediction, one marker per configuration; shape and color by group. */
export function parityChart(points: PointRow[], targetLabel: string): EChartsCoreOption {
  const groups: Group[] = ["anchor", "new", "extrapolation"];
  return {
    grid: { top: 16, left: 56, right: 16, bottom: 48 },
    tooltip: {
      trigger: "item",
      confine: true,
      formatter: (params: unknown) => {
        const p = params as { seriesName: string; data: { value: [number, number]; pt: PointRow } };
        const pt = p.data?.pt;
        if (!pt) return "";
        return (
          `<b>${algorithmName(pt.algorithm)} · ${pt.config}</b><br/>${p.seriesName}` +
          `${pt.twoQubitGates != null ? ` · ${Math.round(pt.twoQubitGates)} 2Q gates` : ""}<br/>` +
          `Observed ${pt.observed.toFixed(3)} (mean of ${pt.jobs}) · Predicted ${pt.predicted.toFixed(3)}<br/>` +
          `Error ${(pt.predicted - pt.observed >= 0 ? "+" : "") + (pt.predicted - pt.observed).toFixed(3)}`
        );
      },
    },
    xAxis: {
      type: "value",
      min: 0,
      max: 1,
      name: `Observed ${targetLabel.toLowerCase()}`,
      nameLocation: "middle",
      nameGap: 28,
      splitLine: { lineStyle: { color: palette.edge, width: 1 } },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1,
      name: "Pre-registered prediction",
      nameLocation: "middle",
      nameGap: 38,
      splitLine: { lineStyle: { color: palette.edge, width: 1 } },
    },
    series: [
      {
        type: "line",
        name: "Perfect prediction",
        data: [
          [0, 0],
          [1, 1],
        ],
        showSymbol: false,
        silent: true,
        lineStyle: { color: palette.muted, width: 1 },
      },
      ...groups.map((g) => ({
        type: "scatter",
        name: GROUP_LABELS[g],
        symbol: GROUP_SYMBOL[g],
        symbolSize: g === "anchor" ? 9 : 11,
        itemStyle: { color: GROUP_COLOR[g], opacity: 0.9, borderColor: "#fff", borderWidth: 1.5 },
        data: points
          .filter((p) => p.group === g)
          .map((p) => ({ value: [+p.observed.toFixed(4), +p.predicted.toFixed(4)], pt: p })),
      })),
    ],
  };
}
