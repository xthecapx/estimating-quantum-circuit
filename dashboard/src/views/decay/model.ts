import { algorithmName } from "../../lib/domain/catalog";
import { palette, type EChartsCoreOption } from "../../lib/charts/echarts";

type Point = [number, number, number, number, number];
export interface Period {
  slopeA: number; slopeB: number; gap: number; rho: number | null; points: Point[];
}
export interface Cell {
  a: string; b: string; role: string; gap: number | null; grouped: boolean | null;
  periods: Record<string, Period>; overlap: Record<string, number>;
}
export interface Snapshot {
  schemaVersion: number; backend: string; jobs: number; algorithms: string[];
  tolerance: number; minPeriods: number; minLevels: number;
  panels: Record<string, Record<string, Cell[]>>;
}
export const resources: Record<string,string> = {
  "a.num_qubits":"Total logical qubits", "a.depth":"Logical depth", "a.size":"Logical operations",
  "a.ComplexityMetrics.gate_based_metrics.two_qubit_count":"Logical two-qubit gates",
  "a.StructuralMetrics.volume":"Structural volume", "a.BehavioralMetrics.program_communication":"Program communication",
  "a.quantum_specific.entanglement_ratio":"Entanglement ratio", "b.depth":"Compiled depth",
  "b.two_qubit_depth":"Compiled two-qubit depth", "b.two_qubit_gates":"Compiled two-qubit gates",
};
export const targets: Record<string,string> = {success:"Success rate", normalized:"Chance-adjusted, ideal-normalized success", hellinger_fidelity:"Hellinger fidelity", tvd_similarity:"TVD similarity", dsr:"Differential success rate"};
// These describe the logical circuit builders. The fits use measurements of the whole circuits.
export function construction(cell: Cell): { title: string; detail: string } {
  switch (cell.role) {
    case "fourier":
      return { title: "Phase estimation contains an inverse QFT",
        detail: "Phase estimation decodes controlled unitary powers with an inverse QFT built from Hadamards and controlled phase rotations. The QFT round trip uses that block after a forward QFT. The period-4 QFT circuit and S-gate phase estimation also encode the same quarter-cycle phase before that block." };
    case "composition":
      return [cell.a, cell.b].includes("QFT")
        ? { title: "Shor order finding contains an inverse QFT",
            detail: "Controlled modular multiplications encode a phase. An inverse QFT on the control register converts it into measurable peaks. The QFT benchmarks exercise the same transform with different preparation." }
        : { title: "Shor order finding uses the phase-estimation construction",
            detail: "Both circuits apply Hadamards to counting qubits, use them to control powers of a unitary, then decode with an inverse QFT. Shor specializes the unitary to modular multiplication." };
    case "oracle":
      return { title: "Two different oracle circuits",
        detail: "Grover marks bitstrings with a multi-controlled phase flip and uses diffusion to amplify them. Bernstein–Vazirani encodes a secret with CNOTs into an ancilla. They share the oracle model. Neither circuit calls the other." };
    case "entanglement":
      return { title: "Shared entangling gates",
        detail: "GHZ prepares a superposition with a Hadamard and a CNOT chain. vTP creates a Bell pair with a Hadamard and a CNOT, teleports a payload and checks its recovery. The shared gates serve different protocols." };
    case "mirror_protocol":
      return { title: "Shared inverse-validation pattern",
        detail: "vTP validates the payload after teleportation with inverse preparation gates. Random volumetric reverses its random two-qubit layers. Each circuit constructs its own inverse sequence." };
    case "control":
      return { title: "Random-circuit comparison",
        detail: "The random-volumetric circuit reverses random two-qubit layers to test recovery. The analysis uses it as a comparison workload across the same resource levels." };
    default:
      return { title: "Compared across algorithm families",
        detail: "The analysis compares every observed pair with shared resource levels. It specifies no circuit-containment relationship for this pair." };
  }
}

export const declineLabels = {
  similar: "Similar decline", different: "Different losses", mixed: "No joint decline",
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
export const short = (a:string) => ({"BERNSTEIN-VAZIRANI":"BV", "PHASE-ESTIMATION":"PE", "RANDOM-VOLUMETRIC":"RV"}[a] ?? algorithmName(a));
export const key = (c:Cell) => c.a + "/" + c.b;

export function rankResources(data: Snapshot) {
  return Object.entries(data.panels).map(([id, panel]) => {
    const pairs = new Set<string>();
    const outcomes = Object.entries(panel).map(([id, cells]) => {
      const matches = cells.map(cell => ({cell, count: matchingWindows(cell, data.tolerance)}))
        .filter(match => match.count >= data.minPeriods)
        .sort((a, b) => b.count - a.count || (a.cell.gap ?? Infinity) - (b.cell.gap ?? Infinity)
          || key(a.cell).localeCompare(key(b.cell)));
      for (const {cell} of matches) pairs.add([cell.a, cell.b].sort().join("/"));
      return {id, matches};
    }).sort((a, b) => b.matches.length - a.matches.length
      || (targets[a.id] ?? a.id).localeCompare(targets[b.id] ?? b.id, "en"));
    return {id, count: pairs.size, outcomes};
  }).sort((a, b) => b.count - a.count
    || (resources[a.id] ?? a.id).localeCompare(resources[b.id] ?? b.id, "en"));
}

export const fixed = (v:number|null) => v == null ? "—" : v.toFixed(2);
// The row and column use the same observed resource range in each period.
export function extraLoss(period: Period, reversed = false): number {
  const span = period.points[period.points.length - 1][0] - period.points[0][0];
  return (reversed ? -1 : 1) * 100 * (period.slopeA - period.slopeB) * span;
}
export function medianLoss(cell: Cell): number | null {
  const values = Object.values(cell.periods).map(p => extraLoss(p)).sort((a, b) => a - b);
  if (!values.length) return null;
  const mid = Math.floor(values.length / 2);
  return values.length % 2 ? values[mid] : (values[mid - 1] + values[mid]) / 2;
}
export function signed(value: number | null, digits = 2): string {
  if (value === null) return "—";
  const rounded = Number(value.toFixed(digits));
  return (rounded > 0 ? "+" : "") + rounded.toFixed(digits);
}
export function bounds(periods:Period[]) {
  const ys=periods.flatMap(p=>p.points.flatMap(t=>t.slice(1).map(v=>100*v)));
  const xs=periods.flatMap(p=>p.points.map(t=>t[0]));
  return {min: Math.floor(Math.min(0,...ys)/10)*10, max: Math.ceil(Math.max(100,...ys)/10)*10,
    xmin:Math.min(...xs), xmax:Math.max(...xs)};
}
export function chart(p:Period,c:Cell,b:ReturnType<typeof bounds>,x:string,y:string):EChartsCoreOption {
  return {
    grid:{top:20,left:48,right:15,bottom:49},
    xAxis:{type:"value",min:b.xmin,max:b.xmax,splitNumber:4,name:x,nameLocation:"middle",nameGap:29,nameTextStyle:{fontSize:10}},
    yAxis:{type:"value",min:b.min,max:b.max,splitNumber:4,axisLabel:{fontSize:10}},
    tooltip:{trigger:"item",confine:true},
    series:([c.a,c.b]).flatMap((name,i) => {
      const color=i===0?palette.teal:palette.accent;
      return [
        {type:"line" as const,name:algorithmName(name)+" fit",showSymbol:false,lineStyle:{color,width:2.5,type:i===0?"solid" as const:"dashed" as const},silent:true,data:p.points.map(t=>[t[0],100*t[3+i]])},
        {type:"scatter" as const,name:algorithmName(name),symbol:i===0?"circle":"diamond",symbolSize:9,itemStyle:{color},dimensions:[x,y],data:p.points.map(t=>[t[0],+(100*t[1+i]).toFixed(2)])}
      ];
    })
  };
}
