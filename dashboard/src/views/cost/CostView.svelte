<script lang="ts" module>
  export interface CostChoices {
    split: string;
    circuit: string;
    shots: string;
    price: string;
  }
</script>

<script lang="ts">
  import EChart from "../../lib/charts/EChart.svelte";
  import { algorithmName } from "../../lib/domain/catalog";
  import Select from "../../lib/ui/Select.svelte";
  import {
    CHIP_LABELS,
    billedWholeSeconds,
    costParityChart,
    durationChart,
    fmt,
    ibmRuleSeconds,
    physicalSeconds,
    shotsChart,
    type CostSnapshot,
  } from "./model";

  let {
    reports,
    choices,
    onchange,
  }: {
    reports: Record<string, string>;
    choices: CostChoices;
    onchange: (v: CostChoices) => void;
  } = $props();

  let data = $state<CostSnapshot>();
  let error = $state("");

  $effect(() => {
    const filename = reports["cost-v1"];
    const controller = new AbortController();
    data = undefined;
    error = "";
    if (!filename) return;
    fetch(new URL("data/" + filename, document.baseURI), { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw Error("fetch");
        const s: CostSnapshot = await r.json();
        if (s.schemaVersion !== 1 || !s.points || !s.physicalTerms) throw Error("schema");
        if (!controller.signal.aborted) data = s;
      })
      .catch(() => {
        if (!controller.signal.aborted) error = "The cost results could not be loaded. Reload to try again.";
      });
    return () => controller.abort();
  });

  const split = $derived(choices.split === "unseen_circuit" ? "unseen_circuit" : "new_run");
  const points = $derived((data?.points ?? []).filter((p) => p.split === split));
  const primary = $derived(data?.primaryModel ?? "");
  const headline = $derived(data?.newRun[primary]?.all);

  /** Calculator: one representative circuit per configuration (new-run chips first, then training). */
  const circuits = $derived.by(() => {
    const seen = new Map<string, NonNullable<typeof data>["points"][number]>();
    for (const p of data?.points ?? []) {
      if (p.duration == null) continue;
      const prev = seen.get(p.config_id);
      if (!prev || (p.split === "new_run" && prev.split !== "new_run")) seen.set(p.config_id, p);
    }
    return [...seen.values()].sort((a, b) => a.duration! - b.duration!);
  });
  const circuit = $derived(circuits.find((c) => c.config_id === choices.circuit) ?? circuits[Math.floor(circuits.length / 2)]);
  const shotOptions = ["256", "512", "1024", "2048", "4096", "8192", "16384", "32768"];
  const shots = $derived(shotOptions.includes(choices.shots) ? Number(choices.shots) : 1024);
  const price = $derived(Number.isFinite(parseFloat(choices.price)) && parseFloat(choices.price) >= 0 ? parseFloat(choices.price) : null);

  const calc = $derived.by(() => {
    if (!data || !circuit) return undefined;
    const tw = circuit.twirling === 1;
    const sec = physicalSeconds(data.physicalTerms, shots, circuit.duration!, tw);
    const ibm = ibmRuleSeconds(data.ibmRule, shots);
    return { sec, ru: sec / data.secondsPerRu, whole: billedWholeSeconds(sec), ibm, ibmRu: ibm / data.secondsPerRu, tw };
  });

  function change(v: Partial<CostChoices>) {
    onchange({ ...choices, ...v });
  }
  const pct = (v?: number) => (v == null ? "—" : `${(v * 100).toFixed(v < 0.1 ? 1 : 0)}%`);
  /** Primary model first, then the alternatives, IBM's rule last. */
  const models = $derived(
    data
      ? [primary, ...Object.keys(data.newRun).filter((m) => m !== primary && m !== "IBM rule of thumb"), "IBM rule of thumb"].filter(
          (m) => m in data!.newRun,
        )
      : [],
  );
</script>

<section class="surface cost" aria-label="Execution cost model">
  {#if error}
    <p role="alert">{error}</p>
  {:else if !reports["cost-v1"]}
    <p class="note">No cost snapshot matches the current export. Run <code>python -m experiments.qaqs_cost</code>, then rebuild.</p>
  {:else if !data}
    <p role="status">Loading cost results…</p>
  {:else}
    <div class="lead">
      <p class="eyebrow">Execution cost · resource units</p>
      <h2>What will a job cost before it runs?</h2>
      <p class="intro-text">
        IBM bills QPU time in resource units (RU): 1 RU = 1 minute of QPU time, charged in whole seconds rounded up.
        One QAQS cost model, shared by every chip, predicts the billed time from the compiled circuit, its scheduled
        duration, the runtime options and the number of shots. Tested on the {data.jobs.newRun} new validation jobs.
      </p>
    </div>

    <div class="tiles" role="list">
      <article class="tile" role="listitem">
        <p class="tile-label">Prediction error on new runs</p>
        <p class="tile-value">{fmt(headline?.maeMilliseconds, 1)} ms</p>
        <p class="tile-sub">mean absolute error on ~{fmt(data.observed.medianSeconds, 2)} s jobs ({fmt(headline?.mapePercent, 2)}%)</p>
      </article>
      <article class="tile" role="listitem">
        <p class="tile-label">Whole seconds charged correctly</p>
        <p class="tile-value">{pct(headline?.billedSecondsAccuracy)}</p>
        <p class="tile-sub">2 vs 3 billed seconds, {data.jobs.newRun} new-run jobs</p>
      </article>
      <article class="tile" role="listitem">
        <p class="tile-label">Typical job</p>
        <p class="tile-value">{fmt(data.observed.medianRus, 4)} RU</p>
        <p class="tile-sub">{fmt(data.observed.medianSeconds, 3)} s billed; {pct(data.observed.overheadShare)} is fixed per-job overhead</p>
      </article>
      <article class="tile" role="listitem">
        <p class="tile-label">IBM rule of thumb, same jobs</p>
        <p class="tile-value">{fmt(data.newRun["IBM rule of thumb"]?.all.maeMilliseconds, 0)} ms</p>
        <p class="tile-sub">error of 2 s + {fmt(data.ibmRule.perExecutionSeconds * 1e6, 0)} µs per shot</p>
      </article>
    </div>

    <div class="two-col">
      <article class="card">
        <div class="card-head">
          <h3>Predicted vs billed, per circuit</h3>
          <div class="settings inline">
            <Select
              label="Test"
              value={split}
              options={["new_run", "unseen_circuit"]}
              format={(s) => (s === "new_run" ? "New runs (3 chips)" : "Training: unseen circuits")}
              onchange={(s) => change({ split: s })}
            />
          </div>
        </div>
        <p class="note">
          {split === "new_run"
            ? "Model fitted on the training campaigns, scored on the validation-v1 jobs (Marrakesh never seen)."
            : "Grouped K-fold on the training campaigns: every circuit predicted by a model that never saw it."}
        </p>
        <EChart option={costParityChart(points)} replace label="Predicted against billed QPU time per circuit" style="height:340px;width:100%" />
        <div class="legend" aria-hidden="true">
          <span><i class="dot"></i>Standard jobs</span>
          <span><i class="diamond"></i>Twirled jobs (Shor)</span>
        </div>
      </article>

      <article class="card">
        <h3>Billed time grows with circuit duration</h3>
        <p class="note">
          Each job pays {fmt(data.physicalTerms.overheadSeconds, 2)} s of overhead, then
          {fmt(data.physicalTerms.perShotSeconds * 1e6, 0)} µs + {fmt(data.physicalTerms.durationSlope, 2)} × duration per shot.
          Dynamic circuits are not scheduled and are left out of this view.
        </p>
        <EChart option={durationChart(data.points, data.physicalTerms, 1024)} replace label="Billed QPU time against scheduled shot duration" style="height:340px;width:100%" />
        <div class="legend" aria-hidden="true">
          <span><i class="dot faint"></i>Standard jobs</span>
          <span><i class="diamond"></i>Twirled jobs (Shor)</span>
          <span><i class="rule"></i>Model at 1,024 shots</span>
        </div>
      </article>
    </div>

    <article class="card">
      <h3>Cost calculator</h3>
      <p class="note">
        Pick a measured circuit and a shot count. The model was only observed at {data.jobs.shots.join(", ")} shots; other
        shot counts follow IBM's usage formula with the fitted per-shot terms, and are an extrapolation. Shot counts are
        multiples of 1,024 (1k = 1,024).
      </p>
      <div class="settings calc-controls">
        <Select
          label="Circuit"
          value={circuit?.config_id ?? ""}
          options={circuits.map((c) => c.config_id)}
          format={(id) => {
            const c = circuits.find((x) => x.config_id === id)!;
            return `${algorithmName(c.algorithm)} · ${id} · ${(c.duration! * 1e6).toFixed(1)} µs`;
          }}
          onchange={(id) => change({ circuit: id })}
        />
        <Select label="Shots" value={String(shots)} options={shotOptions} format={(s) => Number(s).toLocaleString()} onchange={(s) => change({ shots: s })} />
        <label
          >Price per RU (optional, your plan)<input
            type="number"
            min="0"
            step="any"
            inputmode="decimal"
            placeholder="e.g. your contract rate"
            value={choices.price}
            oninput={(e) => change({ price: (e.currentTarget as HTMLInputElement).value })}
          /></label
        >
      </div>
      {#if calc && circuit}
        <div class="calc">
          <div>
            <p class="tile-label">QAQS estimate</p>
            <p class="tile-value">{calc.ru.toFixed(4)} RU</p>
            <p class="tile-sub">
              {calc.sec.toFixed(3)} s → billed {calc.whole} whole s{calc.tw ? " · twirled" : ""}
              {#if price != null}· {(calc.ru * price).toLocaleString(undefined, { maximumFractionDigits: 4 })} per job{/if}
            </p>
          </div>
          <div>
            <p class="tile-label">IBM rule of thumb</p>
            <p class="tile-value muted-value">{calc.ibmRu.toFixed(4)} RU</p>
            <p class="tile-sub">{calc.ibm.toFixed(3)} s{#if price != null} · {(calc.ibmRu * price).toLocaleString(undefined, { maximumFractionDigits: 4 })} per job{/if}</p>
          </div>
          <div>
            <p class="tile-label">Measured at 1,024 shots</p>
            <p class="tile-value muted-value">{(circuit.observed / data.secondsPerRu).toFixed(4)} RU</p>
            <p class="tile-sub">{circuit.observed.toFixed(3)} s on {CHIP_LABELS[circuit.backend] ?? circuit.backend}</p>
          </div>
        </div>
        <EChart
          option={shotsChart(data.physicalTerms, data.ibmRule, circuit.duration!, calc.tw, data.secondsPerRu, shots)}
          replace
          label="Resource units per job against shot count"
          style="height:300px;width:100%"
        />
        <div class="legend" aria-hidden="true">
          <span><i class="line blue"></i>QAQS cost model</span>
          <span><i class="line orange"></i>IBM rule of thumb</span>
          <span><i class="rule muted"></i>1,024 shots (measured) and your choice</span>
        </div>
      {/if}
    </article>

    <article class="card">
      <h3>Model comparison</h3>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Model</th>
              <th scope="col">Training: unseen circuits</th>
              {#each Object.keys(data.newRun[primary] ?? {}) as scope}<th scope="col">New runs · {CHIP_LABELS[scope] ?? scope}</th>{/each}
            </tr>
          </thead>
          <tbody>
            {#each models as name (name)}
              {@const cv = data.unseenCircuit.metrics[name]}
              <tr class:primary={name === primary}>
                <th scope="row">{name}</th>
                <td data-label="Training: unseen circuits"><span class="num">{fmt(cv?.maeMilliseconds, 1)} ms</span><span class="sub">R² {fmt(cv?.r2, 3)} · {pct(cv?.billedSecondsAccuracy)} whole s</span></td>
                {#each Object.entries(data.newRun[name] ?? {}) as [scope, m] (scope)}
                  <td data-label={`New runs · ${CHIP_LABELS[scope] ?? scope}`}><span class="num">{fmt(m.maeMilliseconds, 1)} ms</span><span class="sub">R² {fmt(m.r2, 3)} · {pct(m.billedSecondsAccuracy)} whole s</span></td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="note">Mean absolute error of billed QPU time. Marrakesh had no training data and bills ~8 ms more per job than predicted.</p>
    </article>

    <article class="card">
      <h3>Cost by algorithm</h3>
      <div class="table-scroll">
        <table>
          <thead><tr><th scope="col">Algorithm</th><th scope="col">Jobs</th><th scope="col">Median billed</th><th scope="col">Max billed</th><th scope="col">Circuit time</th><th scope="col">Charged 3 s</th></tr></thead>
          <tbody>
            {#each data.profile as row (row.algorithm)}
              <tr>
                <th scope="row">{algorithmName(row.algorithm)}</th>
                <td data-label="Jobs">{row.jobs}</td>
                <td data-label="Median billed">{row.medianSeconds.toFixed(3)} s <span class="sub">{(row.medianSeconds / data.secondsPerRu).toFixed(4)} RU</span></td>
                <td data-label="Max billed">{row.maxSeconds.toFixed(3)} s</td>
                <td data-label="Circuit time">{row.medianCircuitSeconds.toFixed(3)} s</td>
                <td data-label="Charged 3 s">{pct(row.threeSecondShare)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </article>

    <details class="provenance">
      <summary>How this was built</summary>
      <ul>
        <li>{data.jobs.total} jobs with an RU usage report on {data.jobs.chips.map((b) => CHIP_LABELS[b] ?? b).join(", ")}; {data.jobs.withoutRu} older jobs report whole seconds only and are excluded.</li>
        <li>One model for all chips, no chip input. Inputs are known before running: shots, scheduled duration, twirling and dynamical decoupling, dynamic-circuit flag, compiled depth, size and two-qubit gates.</li>
        <li>Structure: IBM's usage formula (per-job overhead + shots × per-shot time) plus a gradient-boosted residual. Overhead and per-shot time are separated using IBM's measured circuit time, a training label only.</li>
        <li>Tests: grouped K-fold by circuit on {data.jobs.training} training jobs ({data.unseenCircuit.nSplits} folds × {data.unseenCircuit.nRepeats} repeats), and the {data.jobs.newRun} validation-v1 jobs. Cost was not pre-registered for those runs.</li>
        <li>Every job ran {data.jobs.shots.join(", ")} shots, so shot-count scaling in the calculator is untested. Prices depend on your IBM plan; enter your own rate.</li>
      </ul>
    </details>
  {/if}
</section>

<style>
  .cost { padding: clamp(12px, 2.3vw, 28px); display: grid; gap: 18px; min-width: 0; }
  .lead h2 { font: 500 clamp(1.4rem, 2.6vw, 2.1rem) Georgia, serif; margin: 2px 0 8px; }
  .intro-text { max-width: 780px; color: var(--muted); line-height: 1.55; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 210px), 1fr)); gap: 12px; }
  .tile { border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; background: #fff; display: grid; gap: 3px; }
  .tile-label { font-size: 0.78rem; font-weight: 650; color: var(--muted); }
  .tile-value { font-size: 1.75rem; font-weight: 650; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
  .muted-value { color: var(--muted); }
  .tile-sub { font-size: 0.8rem; color: var(--muted); line-height: 1.45; }
  .two-col { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 14px; }
  .card { border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; min-width: 0; background: #fff; display: grid; gap: 8px; align-content: start; }
  .card h3 { font-size: 1rem; }
  .card-head { display: flex; justify-content: space-between; align-items: end; gap: 12px; flex-wrap: wrap; }
  .inline { margin: 0; width: min(100%, 14rem); }
  .inline :global(label), .inline :global(select) { width: 100%; }
  .calc-controls { margin: 4px 0; }
  .calc-controls :global(label) { flex: 1 1 200px; min-width: 0; }
  .calc-controls :global(label:first-child) { flex: 3 1 320px; }
  .calc-controls :global(select), .calc-controls input { width: 100%; min-width: 0; }
  .calc-controls input { font: inherit; padding: 8px 10px; border: 1px solid var(--line); border-radius: 7px; background: #fff; color: var(--ink); }
  .calc { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); gap: 12px; border-top: 1px solid var(--line); padding-top: 10px; }
  .note { font-size: 0.84rem; color: var(--muted); line-height: 1.45; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 0.78rem; color: var(--muted); }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .legend i { display: inline-block; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: #2a78d6; }
  .dot.faint { opacity: 0.55; }
  .diamond { width: 9px; height: 9px; background: #2a78d6; transform: rotate(45deg); }
  .rule { width: 16px; height: 2px; background: #34554e; }
  .rule.muted { background: #a2b6b2; width: 2px; height: 12px; }
  .line { width: 16px; height: 2px; }
  .line.blue { background: #2a78d6; }
  .line.orange { background: #eb6834; }
  .table-scroll { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; font-size: 0.86rem; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  thead th { font-size: 0.76rem; color: var(--muted); font-weight: 650; }
  tbody th { font-weight: 600; min-width: 10rem; }
  tr.primary th { box-shadow: inset 3px 0 0 #2a78d6; }
  .num { display: block; font-weight: 650; font-variant-numeric: tabular-nums; }
  .sub { display: block; font-size: 0.74rem; color: var(--muted); font-weight: 400; }
  .provenance { font-size: 0.84rem; color: var(--muted); }
  .provenance summary { cursor: pointer; font-weight: 600; color: var(--ink); }
  .provenance ul { margin: 8px 0 0; padding-left: 18px; line-height: 1.55; }
  @media (max-width: 640px) {
    thead { display: none; }
    table, tbody, tr, th, td { display: block; width: 100%; }
    tbody tr { border-bottom: 1px solid var(--line); padding: 6px 0; }
    tbody th, tbody td { border: 0; padding: 4px 6px; }
    tbody td::before { content: attr(data-label); display: block; font-size: 0.7rem; font-weight: 650; color: var(--muted); }
  }
</style>
