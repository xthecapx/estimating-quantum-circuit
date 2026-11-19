import { describe, expect, it } from "vitest";
import { levelMeans, selectRegression } from "../../src/lib/stats/regression";
import { job } from "./fixtures";

describe("regression of setting means", () => {
  it("weights configurations equally within each resource level and ignores missing values", () => {
    const jobs = [
      job({ depth: 9, config: "a", tvd: 0.5 }),
      job({ depth: 9, config: "a", tvd: 1 }),
      job({ depth: 9, config: "b", tvd: 0.25 }),
      job({ depth: 2, config: "a", tvd: 0 }),
      job({ depth: 1, tvd: null }),
    ];
    expect(levelMeans(jobs, "depth", "tvd")).toEqual([{ x: 2, mean: 0 }, { x: 9, mean: 0.5 }]);
  });

  it.each([
    ["Constant", (_x: number): number => 0.75],
    ["Linear", (x: number): number => 0.85 - 0.08 * x],
    ["Logarithmic", (x: number): number => 0.9 - 0.25 * Math.log1p(x)],
    ["Quadratic", (x: number): number => 0.2 + 0.03 * (x - 3) ** 2],
  ] as const)("recovers the %s model from equal-weight means", (shape, outcome) => {
    const levels = [0, 1, 3, 4, 5, 7].map(x => ({ x, mean: outcome(x) }));
    const fit = selectRegression(levels)!;
    expect(fit.shape).toBe(shape);
    expect(fit.predict(2)).toBeCloseTo(outcome(2), 9);
    expect(fit.error).toBeCloseTo(0, 9);
  });

  it("requires at least three distinct levels", () => {
    expect(selectRegression([{ x: 2, mean: 0.2 }, { x: 10, mean: 0.7 }])).toBeNull();
  });
});
