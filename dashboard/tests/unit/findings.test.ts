import { describe, expect, it } from "vitest";
import { contrast, points, reading, row, type ComparisonSnapshot } from "../../src/views/findings/model";

const data = {
  rows: [
    { target: "success", model: "per_chip", chip: "a", group: "all", r2: 0.94, mae: 0.054 },
    { target: "success", model: "pooled", chip: "a", group: "all", r2: 0.9, mae: 0.07 },
    { target: "success", model: "per_chip", chip: "a", group: "new", r2: 0.9, mae: 0.05 },
  ],
  contrasts: [
    { target: "success", against: "pooled", diff: 0.04, ciLow: 0.01, ciHigh: 0.08 },
    { target: "success", against: "size", diff: 0.01, ciLow: -0.02, ciHigh: 0.03 },
    { target: "success", against: "mixed", diff: -0.03, ciLow: -0.06, ciHigh: -0.01 },
  ],
} as unknown as ComparisonSnapshot;

describe("findings model", () => {
  it("finds the all-circuits row by default", () => {
    expect(row(data, "per_chip", "success", "a")?.r2).toBe(0.94);
    expect(row(data, "per_chip", "success", "a", "new")?.r2).toBe(0.9);
    expect(row(data, "size", "success", "a")).toBeUndefined();
  });
  it("calls a difference only when its range excludes zero", () => {
    expect(reading(contrast(data, "success", "pooled"))).toBe("better");
    expect(reading(contrast(data, "success", "size"))).toBe("same");
    expect(reading(contrast(data, "success", "mixed"))).toBe("worse");
    expect(reading(undefined)).toBe("same");
  });
  it("states an error as points on the 0-100 scale", () => {
    expect(points(0.054)).toBe("5.4 points");
    expect(points(null)).toBe("—");
  });
});
