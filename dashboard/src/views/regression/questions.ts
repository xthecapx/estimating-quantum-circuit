import type { AxisKey, QuestionKey } from "../../lib/data/types";
import { comparator, format } from "../../lib/domain/format";

export const resource: Record<AxisKey, { unit: string; change: string; largest: string }> = {
  width: { unit: "logical qubits", change: "With more qubits", largest: "maximum number of qubits" },
  depth: { unit: "ISA layers", change: "With deeper circuits", largest: "deepest circuit" },
  bits: { unit: "measured bits", change: "With more measured bits", largest: "highest measured bit count" },
  gates: { unit: "two-qubit gates", change: "With more two-qubit gates", largest: "highest two-qubit gate count" },
};

const prompts: Record<QuestionKey, { trend: string; metric: string }> = {
  success: { trend: "how often is the answer accepted", metric: "success" },
  hellinger: { trend: "how closely does the output match the ideal", metric: "Hellinger fidelity" },
  tvd: { trend: "how far is the output from the ideal", metric: "full TVD" },
  coarse: { trend: "how far are answer groups from their target shares", metric: "coarse TVD" },
  chance: { trend: "how much better do we do than guessing", metric: "chance-corrected success" },
  dsr: { trend: "do accepted peaks stand out", metric: "DSR" },
  contrast: { trend: "how far ahead is the leading answer", metric: "top-two contrast" },
};

export function fitQuestion(axis: AxisKey, key: QuestionKey, target: number | null) {
  const { change, largest } = resource[axis];
  const { trend, metric } = prompts[key];
  if (target === null) return `${change}, ${trend}?`;
  const value = key === "success"
    ? target.toLocaleString("en", { style: "percent", maximumFractionDigits: 15 })
    : String(target);
  return `What’s the ${largest} with ${metric} ${comparator(key)} ${value}?`;
}

export function fitAnswer(key: QuestionKey, y: number): string {
  const percent = (100 * y).toFixed(1) + "%";
  switch (key) {
    case "success": return `an estimated ${percent} of shots return an accepted answer`;
    case "tvd": return `the fitted TVD is ${format(key, y)}, so about ${percent} of probability mass would need to move to match the ideal output`;
    case "coarse": return `the fitted coarse TVD is ${format(key, y)}, so about ${percent} of probability mass would need to move between the grouped outcomes to match the target split`;
    case "chance": return `the fitted chance-corrected success is ${format(key, y)}, or ${percent} of the available improvement over guessing`;
    case "hellinger": return `the estimated distribution overlap is ${format(key, y)} on the Hellinger fidelity scale`;
    case "contrast": return `the estimated contrast between the two leading answers is ${format(key, y)}`;
    case "dsr": return `the estimated contrast of the average accepted peak against the strongest wrong answer is ${format(key, y)}`;
  }
}
