import type { AxisKey, Job, QuestionKey } from "../data/types";

/** Average repetitions within a configuration before weighting configurations equally at each x. */
export function levelMeans(jobs: Job[], axis: AxisKey, metric: QuestionKey) {
  const levels = new Map<number, { min: number; max: number; configs: Map<string, { sum: number; count: number }> }>();
  for (const job of jobs) {
    const x = job[axis];
    const y = job[metric];
    if (y == null || !Number.isFinite(y) || !Number.isFinite(x)) continue;
    const level = levels.get(x) ?? { min: y, max: y, configs: new Map<string, { sum: number; count: number }>() };
    levels.set(x, level);
    level.min = Math.min(level.min, y);
    level.max = Math.max(level.max, y);
    const group = level.configs.get(job.config) ?? { sum: 0, count: 0 };
    group.sum += y;
    group.count++;
    level.configs.set(job.config, group);
  }
  return Array.from(levels, ([x, { min, max, configs }]) => ({
    x, min, max,
    mean: average(Array.from(configs.values(), (g) => g.sum / g.count)),
  })).sort((a, b) => a.x - b.x);
}

const average = (values: number[]) => values.reduce((sum, value) => sum + value, 0) / values.length;
