import { describe, expect, it } from "vitest";
import { findScore, modelsFor, transferLabel, type ChipRun, type ScoreRow } from "../../src/views/prospective/model";

const chip = (backend: string, qpu: "seen" | "unseen"): ChipRun => ({
  backend, qpu, campaignId: `${backend}-v`, createdAt: "2026-11-16T20:00:00Z", gitCommit: "abc",
  jobs: 84, configs: 42, executedFrom: "", executedTo: "", trainingChips: ["ibm_fez", "ibm_kingston"],
});
const score = (backend: string, scope: string, group: ScoreRow["group"], r2: number): ScoreRow => ({
  backend, qpu: backend === "ibm_marrakesh" ? "unseen" : "seen", scope, transfer: "", target: "success",
  regime: "circuit_only", model: "RF", group, jobs: 10, configs: 5, r2, r2CiLow: r2 - 0.1, r2CiHigh: r2 + 0.05,
  mae: 0.05, rmse: 0.07, spearmanRho: 0.9, h1Verdict: "pass", trainingR2: 0.8, trainingMae: 0.07,
});

describe("prospective view model", () => {
  const scores = [
    score("ibm_fez", "pooled", "new", 0.96),
    score("ibm_fez", "ibm_fez", "new", 0.94),
    score("ibm_marrakesh", "ibm_kingston", "new", 0.69),
    score("ibm_marrakesh", "pooled", "new", 0.87),
    score("ibm_marrakesh", "ibm_fez", "new", 0.93),
  ];

  it("leads with the chip's own model, then pooled, then transfer sources", () => {
    expect(modelsFor(chip("ibm_fez", "seen"), scores)).toEqual(["ibm_fez", "pooled"]);
    expect(modelsFor(chip("ibm_marrakesh", "unseen"), scores)[0]).toBe("pooled");
  });

  it("finds the exact row and labels zero-shot transfer", () => {
    const s = findScore(scores, { backend: "ibm_marrakesh", scope: "ibm_fez", target: "success", regime: "circuit_only", group: "new" });
    expect(s?.r2).toBe(0.93);
    expect(transferLabel(chip("ibm_marrakesh", "unseen"), "ibm_fez")).toBe("zero-shot from IBM Fez");
    expect(transferLabel(chip("ibm_marrakesh", "unseen"), "pooled")).toBe("zero-shot, pooled model");
    expect(transferLabel(chip("ibm_fez", "seen"), "ibm_fez")).toBe("trained on this chip");
  });
});
