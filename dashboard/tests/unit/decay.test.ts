import { describe, expect, it } from "vitest";
import { declineStatus, matchingWindows, type Cell, type Period } from "../../src/views/decay/model";

function fit(slopeA: number, slopeB: number): Period {
  return {
    slopeA, slopeB, rho: null, gap: 100 * Math.abs(slopeA - slopeB) * 2,
    points: [0, 1, 2].map(x => [x, 1 + x*slopeA, 1 + x*slopeB, 1 + x*slopeA, 1 + x*slopeB]),
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
      periods: {one: fit(-0.06, -0.05), two: fit(-0.12, -0.1), three: fit(-0.1, -0.3)},
    };
    expect(matchingWindows(cell, 5)).toBe(2);
    expect(matchingWindows({...cell, periods: {}}, 5)).toBe(0);
  });
});
