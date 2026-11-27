import { algorithmName } from "../../lib/domain/catalog";
import { palette, type EChartsCoreOption } from "../../lib/charts/echarts";

type Point = [number, number, number, number, number];
export interface Period {
  slopeA: number;
  slopeB: number;
  gap: number;
  ciLow?: number | null;
  ciHigh?: number | null;
  pMatch?: number | null;
  rho: number | null;
  points: Point[];
}
export interface Cell {
  a: string;
  b: string;
  role: string;
  gap: number | null;
  ciLow?: number | null;
  ciHigh?: number | null;
  pWithin?: number | null;
  primaryOutcome?: boolean;
  grouped: boolean | null;
  periods: Record<string, Period>;
  overlap: Record<string, number>;
}
export interface BaseRate {
  pairClass: string;
  pairs: number;
  windows: number;
  matchedWindows: number;
  shareMatched: number | null;
  meanPMatch: number | null;
  cells: number;
  repeatedCells: number;
  shareRepeated: number | null;
}
export interface Snapshot {
  schemaVersion: number;
  backend: string;
  jobs: number;
  algorithms: string[];
  tolerance: number;
  minPeriods: number;
  minLevels: number;
  baseRates?: BaseRate[];
  panels: Record<string, Record<string, Cell[]>>;
}
export const resources: Record<string, string> = {
  "a.num_qubits": "Total logical qubits",
  "a.depth": "Logical depth",
  "a.size": "Logical operations",
  "a.ComplexityMetrics.gate_based_metrics.two_qubit_count": "Logical two-qubit gates",
  "a.StructuralMetrics.volume": "Structural volume",
  "a.BehavioralMetrics.program_communication": "Program communication",
  "a.quantum_specific.entanglement_ratio": "Entanglement ratio",
  "b.depth": "Compiled depth",
  "b.two_qubit_depth": "Compiled two-qubit depth",
  "b.two_qubit_gates": "Compiled two-qubit gates",
};
export const resourceShort: Record<string, string> = {
  "a.num_qubits": "Qubits",
  "a.depth": "Log. depth",
  "a.size": "Log. ops",
  "a.ComplexityMetrics.gate_based_metrics.two_qubit_count": "Log. 2Q gates",
  "a.StructuralMetrics.volume": "Volume",
  "a.BehavioralMetrics.program_communication": "Prog. comm.",
  "a.quantum_specific.entanglement_ratio": "Entangle.",
  "b.depth": "ISA depth",
  "b.two_qubit_depth": "ISA 2Q depth",
  "b.two_qubit_gates": "ISA 2Q gates",
};
export const targets: Record<string, string> = {
  success: "Success rate",
  chance_corrected: "Chance-corrected success",
  normalized: "Chance-adjusted, ideal-normalized success",
  hellinger_fidelity: "Hellinger fidelity",
  tvd_similarity: "TVD similarity",
  dsr: "Differential success rate",
};
export const CHIP_NAMES: Record<string, string> = {
  "Cepheus-1-108Q": "Rigetti · Cepheus-1-108Q",
  "Forte-1": "IonQ · Forte-1",
  ibm_fez: "IBM Fez",
  ibm_kingston: "IBM Kingston",
  ibm_marrakesh: "IBM Marrakesh",
};
export const CHIP_COLORS: Record<string, string> = {
  "Cepheus-1-108Q": "#755194",
  "Forte-1": "#605a32",
  ibm_fez: palette.teal,
  ibm_kingston: palette.accent,
  ibm_marrakesh: palette.blue,
};
export function chipName(backend: string): string {
  return CHIP_NAMES[backend] ?? backend;
}
// These describe the logical circuit builders. The fits use measurements of the whole circuits.
export function construction(cell: Cell): { title: string; detail: string; tag: string } {
  switch (cell.role) {
    case "fourier":
      return {
        tag: "Shared inverse QFT",
        title: "Phase estimation contains an inverse QFT",
        detail: "Phase estimation decodes controlled unitary powers with an inverse QFT built from Hadamards and controlled phase rotations. The QFT round trip uses that block after a forward QFT. The period-4 QFT circuit and S-gate phase estimation also encode the same quarter-cycle phase before that block.",
      };
    case "composition":
      return [cell.a, cell.b].includes("QFT")
        ? {
            tag: "Shared inverse QFT",
            title: "Shor order finding contains an inverse QFT",
            detail: "Controlled modular multiplications encode a phase. An inverse QFT on the control register converts it into measurable peaks. The QFT benchmarks exercise the same transform with different preparation.",
          }
        : {
            tag: "Shared PE construction",
            title: "Shor order finding uses the phase-estimation construction",
            detail: "Both circuits apply Hadamards to counting qubits, use them to control powers of a unitary, then decode with an inverse QFT. Shor specializes the unitary to modular multiplication.",
          };
    case "oracle":
      return {
        tag: "Oracle family",
        title: "Two different oracle circuits",
        detail: "Grover marks bitstrings with a multi-controlled phase flip and uses diffusion to amplify them. Bernstein–Vazirani encodes a secret with CNOTs into an ancilla. They share the oracle model. Neither circuit calls the other.",
      };
    case "entanglement":
      return {
        tag: "Entangling family",
        title: "Shared entangling gates",
        detail: "GHZ prepares a superposition with a Hadamard and a CNOT chain. vTP creates a Bell pair with a Hadamard and a CNOT, teleports a payload and checks its recovery. The shared gates serve different protocols.",
      };
    case "mirror_protocol":
      return {
        tag: "Inverse-validation",
        title: "Shared inverse-validation pattern",
        detail: "vTP validates the payload after teleportation with inverse preparation gates. Random volumetric reverses its random two-qubit layers. Each circuit constructs its own inverse sequence.",
      };
    case "control":
      return {
        tag: "Random-circuit control",
        title: "Random-circuit comparison",
        detail: "The random-volumetric circuit reverses random two-qubit layers to test recovery. The analysis uses it as a comparison workload across the same resource levels.",
      };
    default:
      return {
        tag: "Unrelated families",
        title: "Compared across algorithm families",
        detail: "The analysis compares every observed pair with shared resource levels. It specifies no circuit-containment relationship for this pair.",
      };
  }
}

export const declineLabels = {
  similar: "Similar decline",
  different: "Different losses",
  mixed: "No joint decline",
};
export function declineStatus(p: Period, tolerance: number): keyof typeof declineLabels {
  const span = p.points[p.points.length - 1][0] - p.points[0][0];
  // Polyfit can return a tiny negative slope for a flat trend. Compare the total
  // drop with roundoff at the observed scale, independently for each algorithm.
  const declines = (slope: number, column: number) => {
    const scale = Math.max(1, ...p.points.map(point => Math.abs(point[column])));
    return -slope * span > 16 * Number.EPSILON * scale;
  };
  if (!declines(p.slopeA, 1) || !declines(p.slopeB, 2)) return "mixed";
  return p.gap <= tolerance ? "similar" : "different";
}
export function matchingWindows(c: Cell, tolerance: number): number {
  return Object.values(c.periods).filter(p => declineStatus(p, tolerance) === "similar").length;
}
export const short = (a: string) =>
  ({ "BERNSTEIN-VAZIRANI": "BV", "PHASE-ESTIMATION": "PE", "RANDOM-VOLUMETRIC": "RV" }[a] ?? algorithmName(a));
export const key = (c: Cell) => c.a + "/" + c.b;

type PartnerEvidence = { id: string; cell: Cell; resources: Set<string>; comparable: boolean };

export function relationshipRanking(reports: Snapshot[], outcome: string) {
  const network = new Map<string, Map<string, PartnerEvidence>>();
  for (const report of reports) {
    for (const id of report.algorithms) {
      if (!network.has(id)) network.set(id, new Map());
    }
    for (const [metric, panel] of Object.entries(report.panels)) {
      for (const cell of panel[outcome] ?? []) {
        const eligible = Object.keys(cell.periods).length >= report.minPeriods;
        const repeated = eligible && matchingWindows(cell, report.tolerance) >= report.minPeriods;
        for (const [id, other] of [[cell.a, cell.b], [cell.b, cell.a]]) {
          const partners = network.get(id)!;
          const partner = partners.get(other) ?? { id: other, cell, resources: new Set<string>(), comparable: false };
          if (repeated) partner.resources.add(metric);
          if (eligible) partner.comparable = true;
          partners.set(other, partner);
        }
      }
    }
  }
  return Array.from(network, ([id, entries]) => {
    const partners = [...entries.values()].sort((a, b) =>
      b.resources.size - a.resources.size || Number(b.comparable) - Number(a.comparable)
      || algorithmName(a.id).localeCompare(algorithmName(b.id)));
    return { id, partners, count: partners.filter(p => p.resources.size > 0).length };
  }).sort((a, b) => b.count - a.count || algorithmName(a.id).localeCompare(algorithmName(b.id)));
}

export interface ChipEvidence {
  cell: Cell;
  matched: number;
  eligible: number;
  minimum: number;
  tolerance: number;
  coverage: string;
}

export interface ResourceRow {
  metric: string;
  chips: Map<string, ChipEvidence>;
  matched: number;
  eligible: number;
  repeats: number;
  comparable: number;
  medianGap: number | null;
}

export function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function resourceEvidence(reports: Snapshot[], algorithm: string, partner: string, outcome: string): ResourceRow[] {
  const metrics = new Set(reports.flatMap(report => Object.keys(report.panels)));
  return Array.from(metrics, metric => {
    const chips = new Map<string, ChipEvidence>();
    const allGaps: number[] = [];
    for (const report of reports) {
      const cell = report.panels[metric]?.[outcome]?.find(c =>
        (c.a === algorithm && c.b === partner) || (c.a === partner && c.b === algorithm));
      if (!cell) continue;
      const shared = Object.values(cell.overlap);
      const best = Math.max(0, ...shared);
      for (const period of Object.values(cell.periods)) allGaps.push(period.gap);
      chips.set(report.backend, {
        coverage: shared.length ? `${best} of ${report.minLevels} shared levels` : "No window data",
        cell,
        matched: matchingWindows(cell, report.tolerance),
        eligible: Object.keys(cell.periods).length,
        minimum: report.minPeriods,
        tolerance: report.tolerance,
      });
    }
    const evidence = [...chips.values()];
    return {
      metric,
      chips,
      matched: evidence.reduce((sum, e) => sum + e.matched, 0),
      eligible: evidence.reduce((sum, e) => sum + e.eligible, 0),
      repeats: evidence.filter(e => e.matched >= e.minimum).length,
      comparable: evidence.filter(e => e.eligible >= e.minimum).length,
      medianGap: median(allGaps),
    };
  }).filter(row => row.chips.size).sort((a, b) =>
    b.repeats - a.repeats || b.comparable - a.comparable
    || (resources[a.metric] ?? a.metric).localeCompare(resources[b.metric] ?? b.metric));
}

export interface WindowEntry {
  backend: string;
  name: string;
  period: Period;
  cell: Cell;
  tolerance: number;
  reversed: boolean;
}

/** Collect every eligible window for a pair and resource across the chosen chip(s). */
export function collectWindows(
  reports: Snapshot[],
  metric: string,
  algorithm: string,
  partner: string,
  outcome: string,
  scope: string,
): WindowEntry[] {
  const selected = scope === "all" ? reports : reports.filter(r => r.backend === scope);
  const entries: WindowEntry[] = [];
  for (const report of selected) {
    const cell = report.panels[metric]?.[outcome]?.find(c =>
      (c.a === algorithm && c.b === partner) || (c.a === partner && c.b === algorithm));
    if (!cell) continue;
    const reversed = algorithm === cell.b;
    for (const [name, period] of Object.entries(cell.periods)) {
      entries.push({ backend: report.backend, name, period, cell, tolerance: report.tolerance, reversed });
    }
  }
  return entries;
}

export interface PairConclusion {
  status: "strong" | "partial" | "none" | "insufficient";
  badge: string;
  headline: string;
  detail: string;
  repeatedResources: string[];
  bestResources: { metric: string; label: string; gap: number }[];
  closestResource?: { metric: string; gap: number };
}

/** Summarize whether a pair preserves decay across circuit resources and chips. */
export function pairConclusion(
  rows: ResourceRow[],
  algorithm: string,
  partner: string,
  outcome: string,
  tolerance: number,
): PairConclusion {
  const comparable = rows.filter(r => r.eligible > 0);
  const unit = outcome === "success" ? "pp" : "points";
  if (!comparable.length) {
    return {
      status: "insufficient",
      badge: "Insufficient overlap",
      headline: `${algorithmName(algorithm)} and ${algorithmName(partner)} share too few resource levels to compare`,
      detail: "No circuit resource has at least three exact shared levels in the same collection window.",
      repeatedResources: [],
      bestResources: [],
    };
  }
  const repeated = comparable.filter(r => r.repeats > 0);
  const totalMatched = comparable.reduce((sum, r) => sum + r.matched, 0);
  const totalEligible = comparable.reduce((sum, r) => sum + r.eligible, 0);
  const rankedByGap = comparable
    .filter((r): r is ResourceRow & { medianGap: number } => r.medianGap != null)
    .sort((a, b) => a.medianGap - b.medianGap);
  const closest = rankedByGap[0];
  const bestResources = rankedByGap.slice(0, 3).map(r => ({
    metric: r.metric,
    label: resources[r.metric] ?? r.metric,
    gap: r.medianGap,
  }));
  const repeatedNames = repeated.map(r => resources[r.metric] ?? r.metric);

  if (repeated.length > 0) {
    const crossChip = repeated.some(r => r.repeats >= 2);
    const list = repeatedNames.slice(0, 3).join(", ") + (repeatedNames.length > 3 ? ` (+${repeatedNames.length - 3} more)` : "");
    return {
      status: crossChip ? "strong" : "partial",
      badge: crossChip ? "Repeated across chips" : "Repeated on one chip",
      headline: `Similar decay on ${repeated.length} of ${comparable.length} comparable ${comparable.length === 1 ? "resource" : "resources"}`,
      detail: `${list} ${repeated.length === 1 ? "shows" : "show"} repeated matches within ${tolerance} ${unit} (${totalMatched} of ${totalEligible} eligible windows overall).`,
      repeatedResources: repeatedNames,
      bestResources,
      closestResource: closest ? { metric: closest.metric, gap: closest.medianGap } : undefined,
    };
  }
  const closestText = closest
    ? ` Closest metric is ${(resources[closest.metric] ?? closest.metric).toLowerCase()} (median ${fixed(closest.medianGap)} ${unit}).`
    : "";
  return {
    status: "none",
    badge: totalMatched > 0 ? "Isolated match only" : "Different decay",
    headline: `No repeated decay match across ${comparable.length} comparable ${comparable.length === 1 ? "resource" : "resources"}`,
    detail: `${totalMatched} of ${totalEligible} eligible windows fell within ${tolerance} ${unit}.${closestText}`,
    repeatedResources: [],
    bestResources,
    closestResource: closest ? { metric: closest.metric, gap: closest.medianGap } : undefined,
  };
}

export interface PartnerMapCell {
  metric: string;
  matched: number;
  eligible: number;
  repeats: number;
  medianGap: number | null;
  level: "cross" | "repeated" | "isolated" | "different" | "none";
}

export interface PartnerMapRow {
  partnerId: string;
  role: string;
  repeatedCount: number;
  cells: PartnerMapCell[];
}

/** Build a Partner x Resource relationship preservation matrix for one algorithm. */
export function partnerResourceMap(
  reports: Snapshot[],
  algorithm: string,
  partners: { id: string; cell: Cell }[],
  outcome: string,
): { metrics: string[]; rows: PartnerMapRow[] } {
  const orderedMetrics = Object.keys(resources).filter(m =>
    reports.some(r => (r.panels[m]?.[outcome] ?? []).some(c =>
      (c.a === algorithm || c.b === algorithm) && Object.keys(c.periods).length > 0)));
  const rows: PartnerMapRow[] = partners.map(p => {
    const byMetric = new Map(resourceEvidence(reports, algorithm, p.id, outcome).map(r => [r.metric, r]));
    const cells: PartnerMapCell[] = orderedMetrics.map(metric => {
      const row = byMetric.get(metric);
      if (!row || !row.eligible) {
        return { metric, matched: 0, eligible: 0, repeats: 0, medianGap: null, level: "none" };
      }
      const level = row.repeats >= 2 ? "cross" : row.repeats === 1 ? "repeated" : row.matched > 0 ? "isolated" : "different";
      return { metric, matched: row.matched, eligible: row.eligible, repeats: row.repeats, medianGap: row.medianGap, level };
    });
    return {
      partnerId: p.id,
      role: p.cell.role,
      repeatedCount: cells.filter(c => c.repeats > 0).length,
      cells,
    };
  });
  return { metrics: orderedMetrics, rows };
}

/** Cross-chip summary matrix cell for the 8x8 all-pairs explorer when viewing "All data". */
export interface CombinedMatrixCell {
  a: string;
  b: string;
  gap: number | null;
  signedDelta: number | null;
  eligible: number;
  matched: number;
  repeated: boolean;
}

export function combinedPairMatrix(
  reports: Snapshot[],
  metric: string,
  outcome: string,
): Map<string, CombinedMatrixCell> {
  const map = new Map<string, { a: string; b: string; gaps: number[]; deltas: number[]; matched: number; repeated: boolean }>();
  for (const report of reports) {
    for (const cell of report.panels[metric]?.[outcome] ?? []) {
      const k = key(cell);
      const entry = map.get(k) ?? { a: cell.a, b: cell.b, gaps: [], deltas: [], matched: 0, repeated: false };
      const wins = Object.values(cell.periods);
      for (const p of wins) {
        entry.gaps.push(p.gap);
        entry.deltas.push(extraLoss(p, false));
      }
      const m = matchingWindows(cell, report.tolerance);
      entry.matched += m;
      if (wins.length >= report.minPeriods && m >= report.minPeriods) entry.repeated = true;
      map.set(k, entry);
    }
  }
  const result = new Map<string, CombinedMatrixCell>();
  for (const [k, entry] of map) {
    result.set(k, {
      a: entry.a,
      b: entry.b,
      gap: median(entry.gaps),
      signedDelta: median(entry.deltas),
      eligible: entry.gaps.length,
      matched: entry.matched,
      repeated: entry.repeated,
    });
  }
  return result;
}

export const fixed = (v: number | null | undefined) => (v == null ? "—" : v.toFixed(2));
// The row and column use the same observed resource range in each period.
export function extraLoss(period: Period, reversed = false): number {
  const span = period.points[period.points.length - 1][0] - period.points[0][0];
  return (reversed ? -1 : 1) * 100 * (period.slopeA - period.slopeB) * span;
}
export function medianLoss(cell: Cell): number | null {
  return median(Object.values(cell.periods).map(p => extraLoss(p)));
}
export function signed(value: number | null | undefined, digits = 2): string {
  if (value == null) return "—";
  const rounded = Number(value.toFixed(digits));
  return (rounded > 0 ? "+" : "") + rounded.toFixed(digits);
}
export function bounds(periods: Period[]) {
  const ys = periods.flatMap(p => p.points.flatMap(t => t.slice(1).map(v => 100 * v)));
  const xs = periods.flatMap(p => p.points.map(t => t[0]));
  return {
    min: Math.floor(Math.min(0, ...ys) / 10) * 10,
    max: Math.ceil(Math.max(100, ...ys) / 10) * 10,
    xmin: Math.min(...xs),
    xmax: Math.max(...xs),
  };
}
export function chart(p: Period, c: Cell, b: ReturnType<typeof bounds>, x: string, y: string): EChartsCoreOption {
  return {
    grid: { top: 20, left: 48, right: 15, bottom: 49 },
    xAxis: { type: "value", min: b.xmin, max: b.xmax, splitNumber: 4, name: x, nameLocation: "middle", nameGap: 29, nameTextStyle: { fontSize: 10 } },
    yAxis: { type: "value", min: b.min, max: b.max, splitNumber: 4, axisLabel: { fontSize: 10 } },
    tooltip: { trigger: "item", confine: true },
    series: ([c.a, c.b]).flatMap((name, i) => {
      const color = i === 0 ? palette.teal : palette.accent;
      return [
        { type: "line" as const, name: algorithmName(name) + " fit", showSymbol: false, lineStyle: { color, width: 2.5, type: i === 0 ? "solid" as const : "dashed" as const }, silent: true, data: p.points.map(t => [t[0], 100 * t[3 + i]]) },
        { type: "scatter" as const, name: algorithmName(name), symbol: i === 0 ? "circle" : "diamond", symbolSize: 9, itemStyle: { color }, dimensions: [x, y], data: p.points.map(t => [t[0], +(100 * t[1 + i]).toFixed(2)]) },
      ];
    }),
  };
}

/**
 * Horizontal dot + 95% bootstrap interval plot comparing median decay gap across
 * all comparable circuit resources (sorted best-to-worst, closest to 0 at top)
 * against the tolerance cutoff. X-axis fits strictly to the plotted dots & CIs.
 */
export function crossChipGapChart(
  rows: ResourceRow[],
  backends: string[],
  tolerance: number,
  unit: string,
  activeMetric = "",
): EChartsCoreOption {
  const comparable = rows
    .filter(r => r.eligible > 0)
    .sort((a, b) => (a.medianGap ?? Infinity) - (b.medianGap ?? Infinity));
  const categories = comparable.map(r => {
    const label = resources[r.metric] ?? r.metric;
    return r.metric === activeMetric
      ? { value: `▸ ${label}`, textStyle: { fontWeight: 700, color: palette.teal } }
      : label;
  });

  const symbols: Record<string, string> = { ibm_fez: "circle", ibm_kingston: "diamond", ibm_marrakesh: "triangle" };
  const offsets: Record<string, number> = { ibm_fez: -0.18, ibm_kingston: 0.18, ibm_marrakesh: 0 };

  let maxPlotted = tolerance * 1.6;
  const series: Record<string, unknown>[] = [];
  for (const backend of backends) {
    const color = CHIP_COLORS[backend] ?? palette.ink;
    const offset = backends.length > 1 ? (offsets[backend] ?? 0) : 0;
    const whiskers: [number, number, number][] = [];
    const dots: {
      value: [number, number];
      metric: string;
      backend: string;
      matched: number;
      eligible: number;
      ciLow: number | null;
      ciHigh: number | null;
      pWithin: number | null;
    }[] = [];

    comparable.forEach((row, idx) => {
      const ev = row.chips.get(backend);
      if (!ev || !ev.eligible) return;
      const winList = Object.values(ev.cell.periods);
      const gap = ev.cell.gap ?? median(winList.map(p => p.gap));
      if (gap == null) return;
      const ciLow = ev.cell.ciLow ?? (winList.length === 1 ? (winList[0].ciLow ?? null) : null);
      const ciHigh = ev.cell.ciHigh ?? (winList.length === 1 ? (winList[0].ciHigh ?? null) : null);
      const pWithin = ev.cell.pWithin ?? (winList.length === 1 ? (winList[0].pMatch ?? null) : null);
      maxPlotted = Math.max(maxPlotted, gap, ciHigh ?? 0);
      if (ciLow != null && ciHigh != null) {
        whiskers.push([idx, ciLow, ciHigh]);
      }
      dots.push({ value: [+gap.toFixed(2), idx], metric: row.metric, backend, matched: ev.matched, eligible: ev.eligible, ciLow, ciHigh, pWithin });
    });

    if (whiskers.length) {
      series.push({
        type: "custom",
        name: chipName(backend) + " 95% CI",
        silent: true,
        z: 2,
        renderItem: (_params: unknown, api: { value: (i: number) => number; coord: (v: [number, number]) => [number, number]; size?: (v: [number, number]) => [number, number] }) => {
          const yIdx = api.value(0);
          const low = api.coord([api.value(1), yIdx]);
          const high = api.coord([api.value(2), yIdx]);
          const band = api.size ? api.size([0, 1])[1] : 24;
          const dy = offset * Math.min(band * 0.5, 16);
          return {
            type: "line",
            shape: { x1: low[0], y1: low[1] + dy, x2: high[0], y2: high[1] + dy },
            style: { stroke: color, lineWidth: 2, opacity: 0.55 },
          };
        },
        data: whiskers,
      });
    }

    series.push({
      type: "scatter",
      name: chipName(backend),
      symbol: symbols[backend] ?? "circle",
      symbolSize: 10,
      symbolOffset: [0, `${Math.round(offset * 100)}%`],
      z: 4,
      itemStyle: { color, borderColor: "#fff", borderWidth: 1.5 },
      data: dots,
      markLine: backend === backends[0] ? {
        silent: true,
        symbol: "none",
        lineStyle: { color: palette.teal, type: "dashed", width: 1.8 },
        label: { formatter: `Similar-decay cutoff (≤ ${tolerance} ${unit})`, position: "insideEndTop", color: palette.teal, fontSize: 10, fontWeight: 600 },
        data: [{ xAxis: tolerance }],
      } : undefined,
      markArea: backend === backends[0] ? {
        silent: true,
        itemStyle: { color: "rgba(8, 115, 99, 0.09)" },
        data: [[{ xAxis: 0 }, { xAxis: tolerance }]],
      } : undefined,
    });
  }

  const step = maxPlotted <= 12 ? 2 : 5;
  const xMax = Math.ceil((maxPlotted * 1.08) / step) * step;

  return {
    grid: { top: 28, left: 168, right: 20, bottom: 40, containLabel: false },
    xAxis: {
      type: "value",
      min: 0,
      max: xMax,
      name: `Median gap in fitted quality drop (${unit}) · ← Closer to 0 = better agreement`,
      nameLocation: "middle",
      nameGap: 26,
      nameTextStyle: { fontSize: 11, color: palette.ink },
      axisLabel: { fontSize: 10 },
      splitLine: { lineStyle: { color: "#e5ece7" } },
    },
    yAxis: {
      type: "category",
      data: categories,
      inverse: true,
      triggerEvent: true,
      axisLabel: { fontSize: 11, color: palette.ink, width: 156, overflow: "truncate" },
      axisTick: { show: false },
      splitLine: { show: true, lineStyle: { color: "#f0f4f1" } },
    },
    tooltip: {
      trigger: "item",
      confine: true,
      formatter: (params: unknown) => {
        const d = (params as { data?: { metric: string; backend: string; value: [number, number]; matched: number; eligible: number; ciLow: number | null; ciHigh: number | null; pWithin: number | null } }).data;
        if (!d) return "";
        const verdict = d.value[0] <= tolerance ? `Within ≤ ${tolerance} ${unit} similar-decay cutoff` : `Above ${tolerance} ${unit} cutoff`;
        const ci = d.ciLow != null && d.ciHigh != null ? `<br/>95% CI: [${d.ciLow.toFixed(2)}, ${d.ciHigh.toFixed(2)}] ${unit}` : "";
        const pm = d.pWithin != null ? `<br/>P(gap ≤ ${tolerance}): ${Math.round(d.pWithin * 100)}%` : "";
        return `<strong>${resources[d.metric] ?? d.metric}</strong><br/>${chipName(d.backend)}: <b>${d.value[0].toFixed(2)} ${unit}</b> (${verdict})${ci}${pm}<br/>Matching windows: ${d.matched} of ${d.eligible}`;
      },
    },
    series,
  };
}
