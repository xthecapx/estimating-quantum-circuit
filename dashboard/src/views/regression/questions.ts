import type { AxisKey, QuestionKey } from "../../lib/data/types";
import { format } from "../../lib/domain/format";

export const resource: Record<AxisKey, { unit: string; change: string; extent: string }> = {
  width: { unit: "logical qubits", change: "With more qubits", extent: "How many qubits can the circuit use" },
  depth: { unit: "ISA layers", change: "With deeper circuits", extent: "How deep can the circuit be" },
  bits: { unit: "measured bits", change: "With more measured bits", extent: "How many bits can the circuit measure" },
  gates: { unit: "two-qubit gates", change: "With more two-qubit gates", extent: "How many two-qubit gates can the circuit use" },
};

export function fitQuestion(axis: AxisKey, key: QuestionKey, target: number | null, algorithm: string) {
  const { change, extent } = resource[axis];
  const percent = target?.toLocaleString("en", { style: "percent", maximumFractionDigits: 12 });
  const answer = algorithm === "GROVER" ? "a marked bitstring" : "an accepted answer";
  switch (key) {
    case "success":
      return target === null
        ? `${change}, how often does a measurement return ${answer}?`
        : `${extent} while still returning ${answer} in at least ${percent} of shots?`;
    case "tvd":
      return target === null
        ? `${change}, how much probability must shift between bitstrings to match the ideal distribution?`
        : `${extent} before matching the ideal bitstring distribution requires moving more than ${percent} of the probability?`;
    case "coarse":
      return target === null
        ? `${change}, how much probability must shift between answer groups to match their target shares?`
        : `${extent} while at most ${percent} of the probability needs to move between answer groups?`;
    case "chance":
      return target === null
        ? `${change}, how much of the gap between random guessing and perfect success does the circuit close?`
        : `${extent} while closing at least ${percent} of the gap between random guessing and perfect success?`;
    case "hellinger":
      return target === null
        ? `${change}, how closely do the measured bitstring frequencies follow the ideal probabilities?`
        : `${extent} while the overlap score between measured and ideal bitstring distributions stays at or above ${target}?`;
    case "dsr":
      return target === null
        ? `${change}, how clearly does the average accepted answer stand out against the most frequent wrong answer?`
        : `${extent} while the average accepted answer maintains a contrast score of at least ${target} against the most frequent wrong answer?`;
    case "contrast":
      return target === null
        ? `${change}, how clearly does the most frequent bitstring stand out from the runner-up?`
        : `${extent} while the two most frequent bitstrings still have a contrast score of at least ${target}?`;
  }
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
