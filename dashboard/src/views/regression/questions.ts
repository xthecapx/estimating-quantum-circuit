import type { AxisKey, QuestionKey } from "../../lib/data/types";
import { format } from "../../lib/domain/format";

export const resource: Record<AxisKey, { unit: string; settings: string }> = {
  width: { unit: "logical qubits", settings: "qubit counts" },
  depth: { unit: "ISA layers", settings: "depths" },
  bits: { unit: "measured bits", settings: "measured bit counts" },
  gates: { unit: "two-qubit gates", settings: "two-qubit gate counts" },
};

export function averageQuestion(axis: AxisKey, key: QuestionKey, target: number | null) {
  const settings = resource[axis].settings;
  if (target === null) {
    const trend: Record<QuestionKey, string> = {
      success: "how often do shots return an accepted answer",
      dsr: "how clearly does a typical accepted answer stand out from the strongest wrong answer",
      contrast: "how far ahead is the leading bitstring from the runner-up",
      coarse: "how much probability must shift between answer groups to reach their target shares",
      tvd: "how much probability must shift to match the ideal output",
      hellinger: "how closely do measured bitstring frequencies match the ideal distribution",
      chance: "how much of the gap from guessing to perfect success does the circuit close",
    };
    return `Across ${settings}, ${trend[key]} on average?`;
  }
  const percent = target.toLocaleString("en", { style: "percent", maximumFractionDigits: 12 });
  const criterion: Record<QuestionKey, string> = {
    success: `do at least ${percent} of shots return an accepted answer`,
    dsr: `does contrast between the average accepted peak and the strongest wrong answer reach ${target}`,
    contrast: `does contrast between the leading bitstring and the runner-up reach ${target}`,
    coarse: `must at most ${percent} of probability shift between answer groups to reach their target shares`,
    tvd: `must at most ${percent} of probability shift to match the ideal output`,
    hellinger: `does overlap with the ideal bitstring distribution score at least ${target}`,
    chance: `does the circuit close at least ${percent} of the gap from guessing to perfect success`,
  };
  return `At which ${settings} ${criterion[key]} on average?`;
}

export function averageAnswer(key: QuestionKey, y: number): string {
  const percent = (100 * y).toFixed(1) + "%";
  switch (key) {
    case "success": return `an average of ${percent} of shots return an accepted answer`;
    case "tvd": return `the average TVD is ${format(key, y)}, so about ${percent} of probability mass would need to move to match the ideal output`;
    case "coarse": return `the average coarse TVD is ${format(key, y)}, so about ${percent} of probability mass would need to move between the grouped outcomes to match the target split`;
    case "chance": return `the average chance-corrected success is ${format(key, y)}, or ${percent} of the available improvement over guessing`;
    case "hellinger": return `the average distribution overlap is ${format(key, y)} on the Hellinger fidelity scale`;
    case "contrast": return `the average contrast between the two leading answers is ${format(key, y)}`;
    case "dsr": return `the average contrast of the average accepted peak against the strongest wrong answer is ${format(key, y)}`;
  }
}
