import { describe, expect, it } from "vitest";
import { sortTargetsByScore, type TargetReport } from "../../src/views/estimation/model";

function target(key: string, cv: number | null, holdout?: number): TargetReport {
  const metrics = (r2: number | null) => ({
    n: 10, r2, mae: 0.1, rmse: 0.1, spearmanRho: 0.5, meetsH1: (r2 ?? 0) >= 0.8,
  });
  return {
    key, column: key, label: key, higherBetter: true, r2Threshold: 0.8, bestModel: "RF",
    footprintCount: 5, hardwareFeatureCount: 0, baselines: [], points: [], footprint: [], h2: [], h4: [],
    h3: { regimes: [], drift: { available: false, rows: [] }, transferMatrix: [] },
    leaderboard: cv === null && holdout === undefined ? [] : [
      { model: "QAQS", label: "QAQS", kind: "procedure", cv: metrics(cv),
        holdout: holdout === undefined ? null : metrics(holdout) },
    ],
  };
}

describe("sortTargetsByScore", () => {
  it("orders targets best to worst by headline CV R²", () => {
    const targets = {
      dsr: target("dsr", 0.62), hellinger: target("hellinger", 0.79),
      tvd: target("tvd", 0.8), success: target("success", 0.78),
    };
    expect(sortTargetsByScore(targets, "cv")).toEqual(["tvd", "hellinger", "success", "dsr"]);
  });

  it("uses the holdout score when that split is active", () => {
    const targets = { a: target("a", 0.9, 0.5), b: target("b", 0.7, 0.8) };
    expect(sortTargetsByScore(targets, "holdout")).toEqual(["b", "a"]);
    expect(sortTargetsByScore(targets, "cv")).toEqual(["a", "b"]);
  });

  it("puts targets without a score last", () => {
    const targets = { empty: target("empty", null), ok: target("ok", 0.4) };
    expect(sortTargetsByScore(targets, "cv")).toEqual(["ok", "empty"]);
  });
});
