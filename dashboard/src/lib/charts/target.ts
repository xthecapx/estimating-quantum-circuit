import type { QuestionKey } from "../data/types";
import { comparator, format } from "../domain/format";

export function targetSeries(metric: QuestionKey, value: number | null, left: number, right: number) {
  return {
    type: "line", name: "Plot target", z: 0, silent: true, symbol: "none", animation: false,
    lineStyle: { color: "#68449b", type: "dashed", width: 2 },
    data: value === null ? [] : [[left, value], [right, value]],
    endLabel: {
      show: value !== null, align: "right", offset: [-16, value !== null && value > 0.9 ? 12 : -10],
      color: "#68449b", backgroundColor: "#f7f1ff", padding: [2, 5], borderRadius: 4,
      formatter: value === null ? "" : `Target ${comparator(metric)} ${format(metric, value)}`,
    },
  };
}
