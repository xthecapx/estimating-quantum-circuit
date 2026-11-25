import { describe, expect, it } from "vitest";
import {
  collectWindows,
  combinedPairMatrix,
  crossChipGapChart,
  declineStatus,
  matchingWindows,
  pairConclusion,
  partnerResourceMap,
  resourceEvidence,
  type Cell,
  type Period,
  type Snapshot,
} from "../../src/views/decay/model";

function fit(slopeA: number, slopeB: number, ciLow = 1, ciHigh = 4): Period {
  return {
    slopeA,
    slopeB,
    rho: 0.9,
    gap: 100 * Math.abs(slopeA - slopeB) * 2,
    ciLow,
    ciHigh,
    pMatch: 0.85,
    points: [0, 1, 2].map(x => [x, 1 + x * slopeA, 1 + x * slopeB, 1 + x * slopeA, 1 + x * slopeB]),
  };
}

function makeSnapshot(backend: string, cells: Cell[]): Snapshot {
  return {
    schemaVersion: 2,
    backend,
    jobs: 100,
    algorithms: ["QFT", "PHASE-ESTIMATION", "GROVER"],
    tolerance: 5,
    minPeriods: 2,
    minLevels: 3,
    panels: {
      "a.num_qubits": { success: cells },
    },
  };
}

describe("repeated similar decay", () => {
  it("compares the losses over the full range and includes the tolerance boundary", () => {
    // Binary fractions keep the gap exactly representable.
    const period = fit(-0.125, -0.0625);
    expect(declineStatus(period, 12.5)).toBe("similar");
    expect(declineStatus(period, 12)).toBe("different");
  });

  it("excludes rising, opposing and numerically flat fits even with a small gap", () => {
    for (const period of [fit(0.01, 0.01), fit(-0.01, 0.01), fit(-1e-16, -0.01)]) {
      expect(declineStatus(period, 5)).toBe("mixed");
    }
  });

  it("counts qualifying windows directly, independently of group membership or profile ranks", () => {
    const cell: Cell = {
      a: "A", b: "B", role: "other", grouped: false, gap: 5, overlap: {},
      periods: { one: fit(-0.06, -0.05), two: fit(-0.12, -0.1), three: fit(-0.1, -0.3) },
    };
    expect(matchingWindows(cell, 5)).toBe(2);
    expect(matchingWindows({ ...cell, periods: {} }, 5)).toBe(0);
  });

  it("aggregates windows, conclusions, partner maps, and gap charts across chips including Marrakesh", () => {
    const fezCell: Cell = {
      a: "PHASE-ESTIMATION", b: "QFT", role: "fourier", grouped: true, gap: 2.0, ciLow: 0.8, ciHigh: 3.4, pWithin: 0.92,
      overlap: { w1: 5, w2: 5 },
      periods: { w1: fit(-0.06, -0.05), w2: fit(-0.07, -0.06) },
    };
    const marrakeshCell: Cell = {
      a: "PHASE-ESTIMATION", b: "QFT", role: "fourier", grouped: null, gap: 3.0, ciLow: 1.5, ciHigh: 4.5, pWithin: 0.9,
      overlap: { m1: 4 },
      periods: { m1: fit(-0.08, -0.065) },
    };
    const reports = [makeSnapshot("ibm_fez", [fezCell]), makeSnapshot("ibm_marrakesh", [marrakeshCell])];
    const rows = resourceEvidence(reports, "PHASE-ESTIMATION", "QFT", "success");
    expect(rows).toHaveLength(1);
    expect(rows[0].matched).toBe(3);
    expect(rows[0].eligible).toBe(3);

    const allWins = collectWindows(reports, "a.num_qubits", "PHASE-ESTIMATION", "QFT", "success", "all");
    expect(allWins.map(w => w.backend)).toEqual(["ibm_fez", "ibm_fez", "ibm_marrakesh"]);
    expect(collectWindows(reports, "a.num_qubits", "PHASE-ESTIMATION", "QFT", "success", "ibm_fez")).toHaveLength(2);

    const conclusion = pairConclusion(rows, "PHASE-ESTIMATION", "QFT", "success", 5);
    expect(conclusion.status).toBe("partial");
    expect(conclusion.repeatedResources).toEqual(["Total logical qubits"]);

    const map = partnerResourceMap(reports, "PHASE-ESTIMATION", [{ id: "QFT", cell: fezCell }], "success");
    expect(map.metrics).toEqual(["a.num_qubits"]);
    expect(map.rows[0].cells[0].level).toBe("repeated");

    const combined = combinedPairMatrix(reports, "a.num_qubits", "success");
    expect(combined.get("PHASE-ESTIMATION/QFT")?.eligible).toBe(3);
    expect(combined.get("PHASE-ESTIMATION/QFT")?.repeated).toBe(true);

    const option = crossChipGapChart(rows, ["ibm_fez", "ibm_marrakesh"], 5, "pp", "a.num_qubits") as {
      xAxis: { max: number };
      yAxis: { data: unknown[] };
      series: unknown[];
    };
    expect(Array.isArray(option.series)).toBe(true);
    // Tight X-axis bound fits plotted values rather than inflating past 25 pp.
    expect(option.xAxis.max).toBeLessThanOrEqual(12);
    expect(option.yAxis.data[0]).toEqual(expect.objectContaining({ value: "▸ Total logical qubits" }));
  });

  it("ignores unplotted single-window outliers when scaling the cross-chip gap axis", () => {
    const outlierCell: Cell = {
      a: "PHASE-ESTIMATION", b: "QFT", role: "fourier", grouped: true, gap: 4.3, ciLow: 1.6, ciHigh: 7.9, pWithin: 0.58,
      overlap: { w1: 5, w2: 5, w3: 5 },
      periods: { w1: fit(-0.35, -0.05, 29, 33), w2: fit(-0.07, -0.05, 0.5, 6), w3: fit(-0.08, -0.06, 1, 7.9) },
    };
    const rows = resourceEvidence([makeSnapshot("ibm_fez", [outlierCell])], "PHASE-ESTIMATION", "QFT", "success");
    const option = crossChipGapChart(rows, ["ibm_fez"], 5, "pp") as { xAxis: { max: number } };
    // Plotted cell median is 4.3 with CI high 7.9, so axis stays tight around 10 pp instead of stretching to 35+ pp.
    expect(option.xAxis.max).toBeLessThanOrEqual(12);
  });
});
