import { tick } from "svelte";
import type { AxisKey, IndexData, Job, QuestionKey, Reference } from "../data/types";
import { axes, questionKeys } from "../domain/catalog";
import { unique } from "../domain/format";
import {
  ALL_GROUPS,
  ALL_PERIODS,
  algorithmsIn,
  familiesIn,
  groupConfigs,
  inPeriod,
  jobKey,
  periods,
  pick,
  selectJobs,
  windowKey,
  type Config,
} from "../domain/scope";
import { levelMeans } from "../stats/regression";
import { passes, summarize } from "../domain/sweep";
import { CalibrationState } from "./calibration.svelte";
import type { UrlState, ViewName } from "./url";

export const BIN_OPTIONS = [8, 16, 32] as const;
const DEFAULT_TARGET = "0.5";

/**
 * Single source of truth for the explorer. User choices are stored as-is; the effective
 * values are derived, so a choice that is unavailable in the current scope falls back
 * without being forgotten.
 */
export class Explorer {
  // Initialised in the constructor; defaults keep class-field ordering valid for TypeScript.
  // `$derived` fields below are evaluated lazily, after construction.
  readonly jobsAll: Job[] = [];
  readonly refs: Record<string, Reference> = {};
  readonly backends: string[] = [];
  readonly calibration: CalibrationState;

  backendChoice = $state("");
  periodChoice = $state(ALL_PERIODS);
  algorithmChoice = $state("QFT");
  familyChoice = $state(ALL_GROUPS);
  question = $state<QuestionKey>("success");
  targetText = $state(DEFAULT_TARGET);
  axis = $state<AxisKey>("width");
  mode = $state<"details" | "overview">("overview");
  readAt = $state<number | null>(null);
  view = $state<ViewName>("range");
  configChoice = $state<string | null>(null);
  runChoice = $state<string | null>(null);
  bins = $state(8);

  /** Restores focus and scroll when leaving the histogram. */
  private rangeReturn: { focus?: HTMLElement | null; scroll: number } = { scroll: 0 };

  constructor(data: IndexData, initial: UrlState = {}) {
    this.jobsAll = data.jobs;
    this.refs = data.refs;
    this.backends = unique(data.jobs.map((j) => j.backend)).sort();
    this.backendChoice = pick(this.backends, "ibm_fez") ?? "";
    this.calibration = new CalibrationState(this);
    this.apply(initial);
  }

  // ---- scope -------------------------------------------------------------------------------
  backend = $derived(pick(this.backends, this.backendChoice) ?? "");
  periods = $derived(periods(this.jobsAll, this.backend));
  period = $derived(
    pick([ALL_PERIODS, ...this.periods.map((p) => p.id)], this.periodChoice) ?? ALL_PERIODS,
  );
  periodLabel = $derived(
    this.period === ALL_PERIODS
      ? "All periods"
      : (this.periods.find((p) => p.id === this.period)?.label ?? ""),
  );
  windowJobs = $derived(inPeriod(this.jobsAll, this.backend, this.period));
  algorithms = $derived(algorithmsIn(this.windowJobs));
  algorithm = $derived(pick(this.algorithms, this.algorithmChoice) ?? "");
  families = $derived(familiesIn(this.windowJobs, this.algorithm));
  family = $derived(pick([ALL_GROUPS, ...this.families], this.familyChoice) ?? ALL_GROUPS);
  jobs = $derived(selectJobs(this.windowJobs, this.algorithm, this.family));
  levels = $derived(levelMeans(this.jobs, this.axis, this.question));
  chosenLevel = $derived(this.levels.find(p => p.x === this.readAt));
  configs = $derived(groupConfigs(this.jobs));
  collections = $derived(unique(this.jobs.map(windowKey)).length);

  // ---- assessment --------------------------------------------------------------------------
  // Svelte number inputs emit numbers or null. Returning that same type preserves
  // intermediate edits such as "0." while the browser waits for the next digit.
  get targetValue(): number | null {
    return this.targetText.trim() === "" ? null : Number(this.targetText);
  }
  set targetValue(value: number | null) {
    this.targetText = value == null ? "" : String(value);
  }

  // Only the editable/display scale changes. Analysis and shared URLs use fractions.
  get targetScale() {
    return this.question === "success" ? 100 : 1;
  }
  get displayTarget(): number | null {
    const value = this.targetValue;
    return value == null ? null : Number((value * this.targetScale).toPrecision(15));
  }
  set displayTarget(value: number | null) {
    this.targetValue = value == null ? null : value / this.targetScale;
  }

  threshold = $derived.by(() => {
    if (this.targetText.trim() === "") return null;
    const value = Number(this.targetText);
    return Number.isFinite(value) && value >= 0 && value <= 1 ? value : null;
  });
  targetInvalid = $derived(this.targetText.trim() !== "" && this.threshold == null);
  passingLevel = $derived(this.threshold === null ? undefined :
    this.levels.filter(p => passes(this.question, p.mean, this.threshold!)).at(-1));
  overviewLevel = $derived(this.chosenLevel ?? this.passingLevel ?? this.levels[0]);
  summary = $derived(summarize(this.configs, this.jobs, this.question, this.threshold));

  // ---- selection ---------------------------------------------------------------------------
  selectedConfig = $derived.by((): Config | undefined => {
    const chosen = this.configs.find((g) => g[0].config === this.configChoice);
    return chosen ?? this.configs[this.summary.boundary ?? 0];
  });
  selectedJob = $derived.by((): Job | undefined => {
    const group = this.selectedConfig;
    if (!group) return undefined;
    return group.find((j) => jobKey(j) === this.runChoice) ?? group[0];
  });
  selectedReference = $derived(this.selectedJob ? this.refs[this.selectedJob.ref] : undefined);

  // ---- setters with the same reset rules as the original explorer -------------------------
  setBackend(value: string) {
    this.backendChoice = value;
    this.periodChoice = ALL_PERIODS;
    this.resetSelection();
  }
  setPeriod(value: string) {
    this.periodChoice = value;
    this.resetSelection();
  }
  setAlgorithm(value: string) {
    this.algorithmChoice = value;
    this.resetSelection();
  }
  setFamily(value: string) {
    this.readAt = null;
    this.familyChoice = value;
    this.configChoice = null;
    this.runChoice = null;
  }
  setQuestion(value: QuestionKey) {
    this.question = value;
    this.targetText = DEFAULT_TARGET;
  }
  selectConfig(config: string) {
    this.configChoice = config;
    this.runChoice = null;
  }
  private resetSelection() {
    this.readAt = null;
    this.familyChoice = ALL_GROUPS;
    this.configChoice = null;
    this.runChoice = null;
  }

  // ---- navigation --------------------------------------------------------------------------
  async openJob(job: Job, opener?: HTMLElement | null) {
    this.rangeReturn = { focus: opener, scroll: window.scrollY };
    this.configChoice = job.config;
    this.runChoice = jobKey(job);
    this.view = "job";
    await tick();
    document.getElementById("histogram-title")?.focus({ preventScroll: true });
    document.getElementById("explorer-path")?.scrollIntoView({ block: "nearest" });
  }

  /** Leave the histogram or calibration view; an ancestor breadcrumb may skip levels. */
  async returnToRange() {
    this.calibration.job = null;
    this.view = "range";
    await tick();
    const target = this.rangeReturn.focus?.isConnected
      ? this.rangeReturn.focus
      : document.getElementById("plot-title");
    target?.focus({ preventScroll: true });
    window.scrollTo({ top: this.rangeReturn.scroll, behavior: "instant" });
  }

  // ---- URL ---------------------------------------------------------------------------------
  apply(state: UrlState) {
    // Existing range and job links opened individual runs before the views were combined.
    this.mode = state.view === "job" || state.calOrigin === "job" || state.mode === "details" ? "details"
      : state.mode === "overview" || state.section === "regression" || !Object.keys(state).length ? "overview" : "details";
    this.readAt = /^\d+$/.test(state.readAt ?? "") && Number.isSafeInteger(Number(state.readAt)) ? Number(state.readAt) : null;
    if (state.backend) this.backendChoice = state.backend;
    this.periodChoice = state.period ?? ALL_PERIODS;
    if (state.algorithm) this.algorithmChoice = state.algorithm;
    this.familyChoice = state.family ?? ALL_GROUPS;
    if (state.question && (questionKeys as string[]).includes(state.question)) {
      this.question = state.question as QuestionKey;
    }
    this.targetText = state.target === "none" ? "" : state.target ?? DEFAULT_TARGET;
    if (state.axis && state.axis in axes) this.axis = state.axis as AxisKey;
    this.configChoice = state.config ?? null;
    this.runChoice = state.run ?? null;
    const bins = Number(state.bins);
    if ((BIN_OPTIONS as readonly number[]).includes(bins)) this.bins = bins;
    this.view = state.view === "job" && this.selectedJob ? "job" : "range";
    this.calibration.apply(state);
  }

  toUrl(): UrlState {
    const job = this.view !== "range" || this.configChoice ? this.selectedJob : undefined;
    return {
      mode: this.mode,
      readAt: this.chosenLevel?.x.toString(),
      backend: this.backend === this.backends[0] && this.backends.length === 1 ? undefined : this.backend,
      period: this.period || undefined,
      algorithm: this.algorithm,
      family: this.family || undefined,
      question: this.question,
      target: this.targetText === DEFAULT_TARGET ? undefined : this.targetText || "none",
      axis: this.axis === "width" ? undefined : this.axis,
      view: this.view === "range" ? undefined : this.view,
      config: job?.config,
      run: job ? jobKey(job) : undefined,
      bins: this.bins === 8 ? undefined : String(this.bins),
      ...this.calibration.toUrl(),
    };
  }
}
