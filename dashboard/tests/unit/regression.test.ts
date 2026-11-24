import { describe, expect, it } from "vitest";
import { levelMeans } from "../../src/lib/stats/regression";
import { job } from "./fixtures";

describe("measured setting averages", () => {
  it("weights configurations equally within each resource level and ignores missing values", () => {
    const jobs = [
      job({ depth: 9, config: "a", tvd: 0.5 }),
      job({ depth: 9, config: "a", tvd: 1 }),
      job({ depth: 9, config: "b", tvd: 0.25 }),
      job({ depth: 2, config: "a", tvd: 0 }),
      job({ depth: 1, tvd: null }),
    ];
    expect(levelMeans(jobs, "depth", "tvd")).toEqual([{ x: 2, mean: 0, min: 0, max: 0 }, { x: 9, mean: 0.5, min: 0.25, max: 1 }]);
  });

});
