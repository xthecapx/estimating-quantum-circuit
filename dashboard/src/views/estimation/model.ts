import { algorithmName } from "../../lib/domain/catalog";
import { palette, type EChartsCoreOption } from "../../lib/charts/echarts";

export interface SplitMetrics {
  n: number;
  r2: number | null;
  mae: number | null;
  rmse: number | null;
  spearmanRho: number | null;
  meetsH1: boolean;
  /** Repeated K-fold only: sd of R² between repeats, and the per-repeat values. */
  r2Sd?: number | null;
  r2PerRepeat?: number[];
  /** 95% cluster-bootstrap CI of R² (resampled by circuit configuration). */
  r2CiLow?: number | null;
  r2CiHigh?: number | null;
  /** pass = CI entirely >= 0.80, fail = CI entirely < 0.80, otherwise inconclusive. */
  h1Verdict?: "pass" | "fail" | "inconclusive";
}

export interface ModelScore {
  model: string;
  label: string;
  kind: string;
  cv: SplitMetrics;
  holdout: SplitMetrics | null;
}

export interface PredictionPoint {
  backend: string;
  provider: string;
  algorithm: string;
  config: string;
  width: number;
  twoQubitGates: number;
  observed: number;
  predicted: number;
  residual: number;
  jobs: number;
  split: "cv" | "holdout";
}

export interface FootprintItem {
  feature: string;
  label: string;
  category: string;
  spearmanRho: number;
  vif: number | null;
  permutationImportance: number;
  shapMeanAbs: number;
  selectionFrequency?: number;
  compositeScore?: number;
  selected?: boolean;
  rank?: number;
}

export interface H2Row extends SplitMetrics {
  protocol: string;
  task: string;
  family: string;
  trainScope: string;
  testTarget: string;
  nTrain: number;
  nTest: number;
}

export interface H3Regime {
  regime: string;
  label: string;
  featureCount: number;
  cv: SplitMetrics;
  holdout: SplitMetrics | null;
}

export interface DriftRow {
  subset: string;
  jobs: number;
  submitR2: number | null;
  submitMae: number | null;
  execR2: number | null;
  execMae: number | null;
  maeDeltaExecMinusSubmit: number | null;
}

export interface TransferCell extends SplitMetrics {
  sourceBackend: string;
  sourceProvider: string;
  targetBackend: string;
  targetProvider: string;
  regime: string;
  regimeLabel: string;
  mode: string;
  /** False for chip-to-chip transfer inside one provider (cannot support the cross-provider claim). */
  crossProvider?: boolean;
  nTrain: number;
  nTest: number;
}

export interface H4Regime extends SplitMetrics {
  regime: string;
  label: string;
  nTrain: number;
  nTest: number;
  byFamily?: Record<string, SplitMetrics>;
  /** R² of each size-matched draw (regime "paradigm_matched" only). */
  r2PerDraw?: (number | null)[];
}

export interface SavedModelInfo {
  model: string;
  path: string;
  sizeKb: number;
  featureCount: number;
  r2: number | null;
  mae: number | null;
}

export interface FootprintAblationRow {
  k: number;
  cvR2: number | null;
  cvMae: number | null;
  features: string[];
  selected: boolean;
}

export interface TargetReport {
  key: string;
  column: string;
  label: string;
  higherBetter: boolean;
  r2Threshold: number;
  bestModel: string;
  footprintCount: number;
  candidateFootprintCount?: number;
  hardwareFeatureCount: number;
  selectedFootprintFeatures?: string[];
  selectedHardwareFeatures?: string[];
  footprintAblation?: FootprintAblationRow[];
  savedModels?: Record<string, SavedModelInfo>;
  leaderboard: ModelScore[];
  circuitLeaderboard?: ModelScore[];
  baselines: ModelScore[];
  points: PredictionPoint[];
  footprint: FootprintItem[];
  h2: H2Row[];
  h3: {
    regimes: H3Regime[];
    drift: { available: boolean; rows: DriftRow[] };
    /** Calibration-cycle validation (per chip): train on earlier windows, test on the latest. */
    temporal?: {
      holdoutPeriods: string[];
      holdoutConfigs: number;
      holdoutConfigsSeenInTrain: number;
      regimes: H3Regime[];
    } | null;
    transferMatrix: TransferCell[];
  };
  h4: H4Regime[];
}

export interface EstimationSnapshot {
  schemaVersion: number;
  backend: string;
  provider: string;
  modality: string;
  jobs: number;
  trainJobs: number;
  holdoutJobs: number;
  holdoutPeriods: string[];
  split?: {
    mode: "kfold" | "config" | "temporal";
    nSplits?: number;
    nRepeats?: number;
    totalConfigs?: number;
    holdoutConfigs?: number;
  };
  temporalOrdering?: {
    available: boolean;
    strict?: boolean;
    trainEnd?: string;
    holdoutStart?: string;
    holdoutJobsBeforeTrainEnd?: number;
  };
  algorithms: string[];
  backendsIncluded: string[];
  providersIncluded: string[];
  targets: Record<string, TargetReport>;
}

export const SCOPE_LABELS: Record<string, string> = {
  ibm_fez: "IBM Fez (ibm_fez)",
  ibm_kingston: "IBM Kingston (ibm_kingston)",
  pooled: "All QPUs Pooled (Cross-chip)",
};

export const TARGET_LABELS: Record<string, string> = {
  dsr: "Differential Success Rate (DSR)",
  hellinger: "Hellinger Fidelity (HF)",
  tvd: "Total Variation Distance (TVD)",
  success: "Success Rate",
};

export const VIEW_LABELS: Record<string, string> = {
  h1: "H1 · Model Leaderboard & Predictions",
  footprint: "O2 · Circuit Footprint & SHAP",
  h3: "H3 · Hardware Boundary & Cross-Chip Transfer",
  h2_h4: "H2 · Scalability & H4 · Random vs. Paradigm",
};

/**
 * Thesis names for the three QAQS validation tests. Keep in sync with
 * VALIDATION_NAMES in experiments/qaqs_kfold.py and the manuscript.
 */
export const VALIDATION = {
  unseenCircuit: {
    name: "Unseen-circuit validation",
    short: "Unseen circuits",
    method: "repeated grouped K-fold by circuit configuration",
    question: "Does QAQS predict circuits it has never seen?",
  },
  calibrationCycle: {
    name: "Calibration-cycle validation",
    short: "Later calibration cycle",
    method: "forward temporal holdout: earlier windows → latest window",
    question: "Does QAQS predict a later calibration cycle?",
  },
  prospective: {
    name: "Prospective validation",
    short: "New QPU run",
    method: "frozen models, new IBM run, predictions committed first",
    question: "Does QAQS predict a run that did not exist at training time?",
  },
} as const;

/** Selector labels: `cv` = unseen-circuit validation, `holdout` = calibration-cycle validation. */
export const SPLIT_LABELS: Record<string, string> = {
  holdout: VALIDATION.calibrationCycle.name,
  cv: VALIDATION.unseenCircuit.name,
};

export const ALGO_COLORS: Record<string, string> = {
  QFT: "#087363",
  "PHASE-ESTIMATION": "#387b9a",
  GROVER: "#c44d16",
  "BERNSTEIN-VAZIRANI": "#bd6617",
  VTP: "#2d6a4f",
  GHZ: "#6d597a",
  "RANDOM-VOLUMETRIC": "#7c8d89",
  SHOR: "#9b2226",
};

export const ALGO_SHORT: Record<string, string> = {
  QFT: "QFT",
  "PHASE-ESTIMATION": "PE",
  GROVER: "Grover",
  "BERNSTEIN-VAZIRANI": "BV",
  VTP: "vTP",
  GHZ: "GHZ",
  "RANDOM-VOLUMETRIC": "RV",
  SHOR: "Shor",
};

export const fmt = (v: number | null | undefined, digits = 3): string =>
  v == null || !Number.isFinite(v) ? "—" : v.toFixed(digits);

/** Headline R² of a target: first leaderboard row (the nested QAQS procedure in K-fold snapshots). */
export function targetScore(report: TargetReport | undefined, split: "holdout" | "cv"): number | null {
  const row = report?.leaderboard[0];
  return row ? pickSplit(row, split).r2 : null;
}

/** Target keys ordered best to worst by headline R²; targets without a score go last. */
export function sortTargetsByScore(
  targets: Record<string, TargetReport>,
  split: "holdout" | "cv",
): string[] {
  return Object.keys(targets).sort((a, b) => {
    const ra = targetScore(targets[a], split);
    const rb = targetScore(targets[b], split);
    if (ra === null && rb === null) return a.localeCompare(b);
    if (ra === null) return 1;
    if (rb === null) return -1;
    return rb - ra;
  });
}

export function pickSplit(row: ModelScore | H3Regime, split: "holdout" | "cv"): SplitMetrics {
  return split === "holdout" && row.holdout ? row.holdout : row.cv;
}

export function leaderboardChart(
  rows: ModelScore[],
  split: "holdout" | "cv",
  threshold: number,
): EChartsCoreOption {
  const ordered = [...rows].reverse();
  const labels = ordered.map((r) => r.model);
  const values = ordered.map((r) => {
    const m = pickSplit(r, split);
    return m.r2 == null ? null : +m.r2.toFixed(4);
  });
  return {
    grid: { top: 22, left: 138, right: 24, bottom: 38 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, confine: true },
    xAxis: {
      type: "value",
      name: "R²",
      nameLocation: "middle",
      nameGap: 24,
      min: (v: { min: number }) => Math.min(0, Math.floor((v.min ?? 0) * 10) / 10),
      max: 1,
    },
    yAxis: {
      type: "category",
      data: labels,
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        type: "bar",
        name: "R²",
        data: values.map((val, i) => ({
          value: val,
          itemStyle: {
            color:
              ordered[i].kind === "analytical_baseline"
                ? palette.reference
                : val != null && val >= threshold
                  ? palette.teal
                  : palette.accent,
          },
        })),
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { color: palette.outline, type: "dashed", width: 1.5 },
          label: { formatter: `H1 target (${threshold.toFixed(2)})`, fontSize: 10 },
          data: [{ xAxis: threshold }],
        },
      },
    ],
  };
}

export function scatterChart(
  points: PredictionPoint[],
  split: "holdout" | "cv",
  targetLabel: string,
): EChartsCoreOption {
  const filtered = points.filter((p) => p.split === split);
  const usePoints = filtered.length ? filtered : points;
  const byAlgo = new Map<string, PredictionPoint[]>();
  for (const pt of usePoints) {
    const arr = byAlgo.get(pt.algorithm) ?? [];
    arr.push(pt);
    byAlgo.set(pt.algorithm, arr);
  }
  const series: EChartsCoreOption[] = [
    {
      type: "line",
      name: "Ideal y = x",
      data: [
        [0, 0],
        [1, 1],
      ],
      showSymbol: false,
      silent: true,
      lineStyle: { color: palette.muted, type: "dashed", width: 1.5 },
    },
  ];
  for (const [algo, pts] of byAlgo.entries()) {
    series.push({
      type: "scatter",
      name: algorithmName(algo),
      symbolSize: 8,
      itemStyle: { color: ALGO_COLORS[algo] ?? palette.blue, opacity: 0.85 },
      data: pts.map((p) => [
        +p.observed.toFixed(4),
        +p.predicted.toFixed(4),
        p.config,
        p.backend,
        p.jobs,
        Math.round(p.twoQubitGates || 0),
      ]),
    });
  }
  return {
    grid: { top: 24, left: 54, right: 24, bottom: 48 },
    tooltip: {
      trigger: "item",
      confine: true,
      formatter: (params: unknown) => {
        const p = params as { seriesName?: string; value?: [number, number, string, string, number, number] };
        if (!p.value || p.value.length < 6) return "";
        const [obs, pred, cfg, chip, jobs, g2] = p.value;
        return `<b>${p.seriesName} · ${cfg}</b><br/>Chip: ${chip} (${jobs} jobs, ${g2} 2Q gates)<br/>Observed: ${obs.toFixed(3)} · Predicted: ${pred.toFixed(3)}`;
      },
    },
    xAxis: {
      type: "value",
      min: 0,
      max: 1,
      name: `Observed ${targetLabel}`,
      nameLocation: "middle",
      nameGap: 28,
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1,
      name: `Predicted`,
      nameLocation: "middle",
      nameGap: 38,
    },
    series,
  };
}

export function footprintChart(items: FootprintItem[]): EChartsCoreOption {
  const ordered = [...items].reverse();
  return {
    grid: { top: 20, left: 215, right: 24, bottom: 38 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, confine: true },
    xAxis: {
      type: "value",
      name: "Mean |SHAP| contribution",
      nameLocation: "middle",
      nameGap: 24,
    },
    yAxis: {
      type: "category",
      data: ordered.map((d) => d.label),
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        type: "bar",
        name: "Mean |SHAP|",
        data: ordered.map((d) => ({
          value: +d.shapMeanAbs.toFixed(5),
          itemStyle: { color: d.selected === false ? palette.muted : palette.teal },
        })),
      },
    ],
  };
}

export function regimeBarChart(
  items: { label: string; r2: number | null; mae: number | null; color?: string }[],
  metric: "r2" | "mae" = "r2",
): EChartsCoreOption {
  return {
    grid: { top: 24, left: 54, right: 20, bottom: 56 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, confine: true },
    xAxis: {
      type: "category",
      data: items.map((i) => i.label),
      axisLabel: { fontSize: 10, interval: 0, width: 110, overflow: "break" },
    },
    yAxis: {
      type: "value",
      name: metric === "r2" ? "R²" : "MAE",
      min: metric === "r2" ? (v: { min: number }) => Math.min(0, Math.floor((v.min ?? 0) * 10) / 10) : 0,
    },
    series: [
      {
        type: "bar",
        name: metric === "r2" ? "R²" : "MAE",
        data: items.map((i) => ({
          value: i[metric] == null ? null : +i[metric]!.toFixed(4),
          itemStyle: { color: i.color ?? palette.teal },
        })),
      },
    ],
  };
}
