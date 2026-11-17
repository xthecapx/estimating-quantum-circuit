import { describe, expect, it } from "vitest";
import { billedWholeSeconds, ibmRuleSeconds, physicalSeconds, type PhysicalTerms } from "../../src/views/cost/model";

const terms: PhysicalTerms = {
  overheadSeconds: 1.702, twirlingOverheadSeconds: 0.03, perShotSeconds: 258e-6, durationSlope: 1.02,
  twirlingDurationSlope: 5.2, twirlingPerShotSeconds: -12e-6, circuitTimeMaeMilliseconds: 1.7,
};

describe("cost model helpers", () => {
  it("reproduces the typical 1,024-shot job at ~1.97 s", () => {
    expect(physicalSeconds(terms, 1024, 4.6e-6, false)).toBeCloseTo(1.702 + 1024 * (258e-6 + 1.02 * 4.6e-6), 6);
    expect(physicalSeconds(terms, 1024, 4.6e-6, false)).toBeGreaterThan(1.96);
  });

  it("scales the per-shot part linearly with shots and keeps the overhead fixed", () => {
    const a = physicalSeconds(terms, 1024, 10e-6, false) - terms.overheadSeconds;
    const b = physicalSeconds(terms, 2048, 10e-6, false) - terms.overheadSeconds;
    expect(b / a).toBeCloseTo(2, 9);
  });

  it("adds the twirling terms only when twirling is on", () => {
    expect(physicalSeconds(terms, 1024, 20e-6, true)).toBeGreaterThan(physicalSeconds(terms, 1024, 20e-6, false));
  });

  it("bills whole seconds rounded up and applies IBM's rule of thumb", () => {
    expect(billedWholeSeconds(1.971)).toBe(2);
    expect(billedWholeSeconds(2.0)).toBe(2);
    expect(billedWholeSeconds(2.04)).toBe(3);
    expect(ibmRuleSeconds({ overheadSeconds: 2, perExecutionSeconds: 0.00035 }, 1024)).toBeCloseTo(2.3584, 4);
  });
});
