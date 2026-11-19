import type { AxisKey, Job, QuestionKey } from "../data/types";

export interface Level {
  x: number;
  mean: number;
}

/** Average repetitions within a configuration before weighting configurations equally at each x. */
export function levelMeans(jobs: Job[], axis: AxisKey, metric: QuestionKey): Level[] {
  const levels = new Map<number, Map<string, { sum: number; count: number }>>();
  for (const job of jobs) {
    const x = job[axis];
    const y = job[metric];
    if (y == null || !Number.isFinite(y) || !Number.isFinite(x)) continue;
    const configs = levels.get(x) ?? new Map<string, { sum: number; count: number }>();
    levels.set(x, configs);
    const group = configs.get(job.config) ?? { sum: 0, count: 0 };
    group.sum += y;
    group.count++;
    configs.set(job.config, group);
  }
  return Array.from(levels, ([x, configs]) => ({
    x,
    mean: average(Array.from(configs.values(), (g) => g.sum / g.count)),
  })).sort((a, b) => a.x - b.x);
}

const average = (values: number[]) => values.reduce((sum, value) => sum + value, 0) / values.length;
const bounded = (y: number) => Math.min(1, Math.max(0, y));

type Shape = "Constant" | "Linear" | "Logarithmic" | "Quadratic";
export interface Regression {
  shape: Shape;
  error: number;
  predict: (x: number) => number;
}

function leastSquares(levels: Level[], shape: Shape) {
  const meanY = average(levels.map((p) => p.mean));
  if (shape === "Constant") return () => meanY;

  const transform = shape === "Logarithmic" ? Math.log1p : (x: number) => x;
  const center = average(levels.map((p) => transform(p.x)));
  const span = transform(levels.at(-1)!.x) - transform(levels[0].x);
  const scale = (x: number) => (transform(x) - center) / span;
  const xs = levels.map((p) => scale(p.x));
  const squares = xs.reduce((sum, x) => sum + x * x, 0);
  const slope = levels.reduce((sum, p, i) => sum + xs[i] * (p.mean - meanY), 0) / squares;
  const line = (x: number) => meanY + slope * x;
  if (shape !== "Quadratic") return (x: number) => bounded(line(scale(x)));

  // Remove the constant and linear components from x² to fit curvature independently.
  const offset = squares / xs.length;
  const tilt = xs.reduce((sum, x) => sum + x ** 3, 0) / squares;
  const bend = (x: number) => x * x - offset - tilt * x;
  const curvature = levels.reduce((sum, p, i) => sum + bend(xs[i]) * (p.mean - line(xs[i])), 0)
    / xs.reduce((sum, x) => sum + bend(x) ** 2, 0);
  return (x: number) => {
    const z = scale(x);
    return bounded(line(z) + curvature * bend(z));
  };
}

/** Inputs are distinct, sorted x levels. Hold out one entire level, not one job. */
export function selectRegression(levels: Level[]): Regression | null {
  if (levels.length < 3) return null;
  const shapes: Shape[] = ["Constant", "Linear", "Logarithmic"];
  if (levels.length >= 5) shapes.push("Quadratic");
  let best: Regression | null = null;
  for (const shape of shapes) {
    const errors = levels.map((held, i) => {
      const train = levels.filter((_, j) => j !== i);
      return Math.abs(leastSquares(train, shape)(held.x) - held.mean);
    });
    const error = average(errors);
    if (!best || error < best.error - 1e-10) {
      best = { shape, error, predict: leastSquares(levels, shape) };
    }
  }
  return best;
}
