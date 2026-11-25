<script lang="ts">
  import EChart from "../../lib/charts/EChart.svelte";
  import { comparisonData, estimationData } from "../../lib/data/load";
  import Select from "../../lib/ui/Select.svelte";
  import { footprintMetric } from "../estimation/footprintMetrics";
  import {
    BAR, GROUPS, MODELS, MODEL_ORDER, STATUS_LABEL, TARGETS, TARGET_ORDER,
    chipName, contrast, fmt, parityChart, points, reading, row, scoreChart, trainingRow,
    type Status,
  } from "./model";

  let {
    comparison, estimation, onnavigate,
  }: {
    comparison: Record<string, string>;
    estimation: Record<string, string>;
    onnavigate: (section: string) => void;
  } = $props();

  const cmpStore = $derived(comparisonData.watch(comparison["validation-v1"]));
  const data = $derived($cmpStore.data);
  const pooledStore = $derived(estimationData.watch(estimation.pooled, "pooled"));
  const pooled = $derived($pooledStore.data);

  let target = $state<(typeof TARGET_ORDER)[number]>("success");
  let chip = $state("");
  const chips = $derived(data?.chips ?? []);
  const activeChip = $derived(chips.includes(chip) ? chip : (chips[0] ?? ""));
  const unseen = $derived(chips.filter((c) => !data?.trainedChips.includes(c)));
  const T = $derived(TARGETS[target]);

  const best = (c: string, t: string = target) => (data ? row(data, "per_chip", t, c) : undefined);
  const pts = $derived((data?.points ?? []).filter((p) => p.target === target && p.chip === activeChip));
  const training = $derived(trainingRow(pooled, target));

  /** Training-side rows per chip need each chip's own snapshot. */
  const chipStores = $derived((data?.trainedChips ?? []).map((c) => ({ chip: c, store: estimationData.watch(estimation[c], c) })));

  const modelRows = $derived(
    data
      ? MODEL_ORDER.map((m) => ({
          id: m, ...MODELS[m],
          cells: chips.map((c) => row(data, m, target, c)),
          verdict: m === "per_chip" ? undefined : reading(contrast(data, target, m)),
          diff: m === "per_chip" ? undefined : contrast(data, target, m),
        }))
      : [],
  );

  const sizeGain = $derived(data ? contrast(data, target, "size") : undefined);
  const calib = $derived(data ? contrast(data, target, "mixed") : undefined);
  const scaling = $derived((training?.h2 ?? []).filter((r) => r.protocol === "scaling_extrapolation" && r.variant === "footprint"));
  const zeroShot = $derived((training?.h2 ?? []).filter((r) => r.protocol === "leave_algorithm_out"));
  const h4 = $derived((training?.h4Contrasts ?? []).find((c) => c.a === "paradigm_matched"));
  const stable = $derived((training?.stable ?? []).map((f) => ({ ...f, ...footprintMetric(f.feature, f.feature) })));

  /** Supported only if the low end of every chip's likely range clears the target. */
  const lows = $derived(chips.map((c) => best(c)?.r2CiLow ?? 0));
  const h1: Status = $derived(
    lows.every((v) => v >= BAR) ? "yes" : chips.some((c) => (best(c)?.r2 ?? 0) >= BAR) ? "partly" : "no",
  );
  const worst = (rows: Record<string, any>[]) => (rows.length ? Math.max(...rows.map((r) => r.r2 ?? 0)) : null);
  const statusClass = (s: Status) => ({ yes: "ok", partly: "mid", no: "bad", waiting: "wait" })[s];
</script>

<section class="findings" aria-label="Findings">
  {#if $cmpStore.error}
    <p role="alert" class="note">{$cmpStore.error.message}</p>
  {:else if !data}
    <p role="status" class="note">Reading the model comparison…</p>
  {:else}
    <div class="lead">
      <p class="eyebrow">The question</p>
      <h2>Can we tell how well a quantum program will run, before paying to run it?</h2>
      <p class="intro-text">
        Quantum computers are noisy: the same program gives a correct answer only part of the time, and every run is billed.
        This project measures a program's structure <strong>before</strong> it runs — a short list of numbers we call its
        <strong>footprint</strong> — and trains a model to predict the quality of the result. Below: how close the predictions
        got on {data.jobs} real runs the models had never seen, on {chips.length} IBM chips.
      </p>
    </div>

    <div class="settings controls">
      <Select label="Quality measure" value={target} options={TARGET_ORDER} format={(k) => TARGETS[k].name} onchange={(v) => (target = v)} />
      <p class="note measure">{T.name}: {T.plain}.</p>
    </div>

    <div class="tiles" role="list" aria-label="Prediction accuracy per chip">
      {#each chips as c (c)}
        {@const r = best(c)}
        <article class="tile" role="listitem">
          <p class="tile-chip">
            {chipName(c)}
            <span class="tag" class:warm={unseen.includes(c)}>{unseen.includes(c) ? "never trained on" : "trained on"}</span>
          </p>
          <p class="tile-value">± {points(r?.mae)}</p>
          <p class="tile-sub">typical prediction error</p>
          <p class="tile-meta">
            Score {fmt(r?.r2)} <span class="dim">(likely {fmt(r?.r2CiLow)}–{fmt(r?.r2CiHigh)}, 1 = perfect)</span><br />
            {r?.configs ?? "—"} circuits · {r?.jobs ?? "—"} runs
          </p>
        </article>
      {/each}
    </div>
    <p class="note">
      How to read it: a prediction of 80% with an error of ± 5 points means the chip usually measures between 75% and 85%.
      The score (R²) is the share of the differences between circuits that the model explains; the target set before the
      experiment was {BAR.toFixed(2)}.
    </p>

    <article class="card">
      <div class="card-head">
        <div>
          <h3>Predicted before running vs measured on the chip</h3>
          <p class="note">Each mark is one circuit on {chipName(activeChip)}. On the diagonal, the prediction was exact.</p>
        </div>
        <div class="settings chip-select">
          <Select label="Chip" value={activeChip} options={chips} format={chipName} onchange={(v) => (chip = v)} />
        </div>
      </div>
      <div class="legend" aria-hidden="true">
        {#each Object.values(GROUPS) as g}
          <span><i class="sym {g.symbol}" style="--c:{g.color}"></i>{g.name}</span>
        {/each}
        <span><i class="rule"></i>Perfect prediction</span>
      </div>
      <EChart option={parityChart(pts, T.name)} replace class="plot" style="height:min(62vw,420px)" label="Predicted against measured {T.name} for {chipName(activeChip)}" />
    </article>

    <article class="card">
      <h3>Which model should be used?</h3>
      <p class="note">
        Five ways of building the predictor, scored on the same {data.jobs} unseen runs. Higher score is better; the error is
        in points on the 0–100 scale.
      </p>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Model</th>
              {#each chips as c}<th scope="col">{chipName(c)}{unseen.includes(c) ? " (new chip)" : ""}</th>{/each}
              <th scope="col">Against the best</th>
            </tr>
          </thead>
          <tbody>
            {#each modelRows as m (m.id)}
              <tr class:best={m.id === "per_chip"}>
                <th scope="row">
                  {m.name} <span class="role {m.id}">{m.role}</span>
                  <span class="sub">{m.plain}</span>
                </th>
                {#each m.cells as cell, i}
                  <td data-label={chipName(chips[i])}>
                    <span class="num">{fmt(cell?.r2)}</span><span class="sub">± {points(cell?.mae)}</span>
                  </td>
                {/each}
                <td data-label="Against the best">
                  {#if m.verdict === undefined}
                    <span class="sub">reference</span>
                  {:else}
                    <span class="verdict {m.verdict === 'better' ? 'bad' : m.verdict === 'worse' ? 'ok' : 'mid'}">
                      {m.verdict === "better" ? "Worse" : m.verdict === "worse" ? "Better" : "No clear difference"}
                    </span>
                    <span class="sub">{fmt(-(m.diff?.diff ?? 0), 3)} score</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="note">
        <strong>Decision.</strong> Use one model per chip where the chip has training runs; use the shared model for a chip
        with none. The shared model that is also told the chip name stays a candidate: it will be tested again when runs from
        more chips and other providers are added.
      </p>
    </article>

    <h3 class="section-title">What the experiment showed</h3>
    <div class="claims">
      <article class="claim">
        <p class="claim-head"><span class="status {statusClass(h1)}">{STATUS_LABEL[h1]}</span> H1 · The footprint predicts quality</p>
        <p>
          On runs the models never saw, the per-chip models scored {chips.map((c) => `${fmt(best(c)?.r2)} on ${chipName(c)}`).join(", ")}
          for {T.name.toLowerCase()}.
          {#if target === "dsr"}This measure is not predicted well by any model.{/if}
          Inside the training data alone the estimate is lower ({fmt(training?.r2)} for the shared model), partly because
          repeated runs of the <em>same</em> circuit already disagree with each other: no model could score above
          {fmt(training?.ceiling)} there.
        </p>
      </article>
      <article class="claim">
        <p class="claim-head"><span class="status mid">{STATUS_LABEL.partly}</span> H2 · It works for circuits it has not seen</p>
        <p>
          Yes for new circuits of a familiar size. No for circuits larger than anything in training (best score
          {fmt(worst(scaling))}, where 0 means no better than guessing the average) or for an algorithm that was left out
          of training (best score {fmt(worst(zeroShot))}). The model interpolates; it does not extrapolate.
        </p>
      </article>
      <article class="claim">
        <p class="claim-head"><span class="status wait">{STATUS_LABEL.waiting}</span> H3 · One model works across providers</p>
        <p>
          Only IBM chips have been measured so far. Across IBM chips, a model moved to a chip it never trained on
          ({unseen.map(chipName).join(", ") || "none yet"}) scored {fmt(unseen.length ? best(unseen[0])?.r2 : null)}.
          Runs on other providers are pending.
        </p>
      </article>
      <article class="claim">
        <p class="claim-head"><span class="status {h4?.verdict === 'a_better' ? 'ok' : 'bad'}">{h4?.verdict === "a_better" ? STATUS_LABEL.yes : STATUS_LABEL.no}</span> H4 · Real algorithms teach more than random circuits</p>
        <p>
          With the same number of training runs, models trained on real algorithms and models trained on random circuits
          predict equally well (difference {fmt(h4?.diff, 3)}, likely range {fmt(h4?.ciLow)} to {fmt(h4?.ciHigh)}).
          Real algorithms helped only by adding more data.
        </p>
      </article>
    </div>

    <h3 class="section-title">Three things worth knowing</h3>
    <div class="claims three">
      <article class="claim plain">
        <p class="claim-head">Most of the signal is circuit size</p>
        <p>
          A model that sees only four plain counts (gates, depth, qubits, measurements) comes within
          {fmt(Math.abs(sizeGain?.diff ?? 0), 3)} of the full footprint
          ({reading(sizeGain) === "better" ? "the footprint is measurably better" : "no clear difference"}).
          {#if stable.length}The footprint metric{stable.length > 1 ? "s" : ""} chosen in nearly every training round:
            {stable.slice(0, 3).map((f) => f.name.toLowerCase()).join(", ")}.{/if}
        </p>
      </article>
      <article class="claim plain">
        <p class="claim-head">The chip's published error rates did not help</p>
        <p>
          Adding the chip's calibration data on the day changed the score by {fmt(-(calib?.diff ?? 0), 3)}
          ({reading(calib) === "better" ? "worse than without it" : "no clear difference"}). The structure of the program
          carries the information; a prediction needs no live hardware data.
        </p>
      </article>
      <article class="claim plain">
        <p class="claim-head">One circuit family was inflating the score</p>
        <p>
          Shor's algorithm almost always fails on these chips, so "it will fail" is an easy correct guess. Counting it raised
          the training score from {fmt(training?.r2)} to {fmt(training?.withAnchor)}. All scores on this page leave it out.
        </p>
      </article>
    </div>

    <article class="card">
      <h3>Limits</h3>
      <ul class="limits">
        <li>Two chips were used for training and three for testing, all from one provider and one chip family.</li>
        <li>The test run has {data.jobs} runs; ranges are wide for small groups (13 new circuits per chip).</li>
        <li>The best model was chosen after looking at this test run, so its score here is a description, not a fresh test. The next planned run is the fresh test.</li>
        <li>Predictions are valid for circuit sizes covered by training.</li>
      </ul>
      <p class="links">
        Details:
        <button type="button" onclick={() => onnavigate("validation")}>Pre-registered test</button>
        <button type="button" onclick={() => onnavigate("footprint")}>Footprint metrics</button>
        <button type="button" onclick={() => onnavigate("estimation")}>Model training</button>
        <button type="button" onclick={() => onnavigate("range")}>Raw experiment data</button>
      </p>
    </article>
  {/if}
</section>

<style>
  .findings { padding: clamp(12px, 2.3vw, 28px); display: grid; gap: 18px; min-width: 0; }
  .lead h2 { font: 500 clamp(1.5rem, 2.8vw, 2.3rem)/1.18 Georgia, serif; letter-spacing: -0.02em; margin: 2px 0 10px; max-width: 22em; }
  .intro-text { max-width: 760px; color: var(--muted); line-height: 1.6; }
  .controls { align-items: end; border-bottom: 1px solid var(--line); padding-bottom: 14px; margin: 0; }
  .controls :global(label) { flex: 0 1 240px; min-width: 0; }
  .controls :global(select), .card-head :global(select) { width: 100%; min-width: 0; }
  .measure { flex: 1 1 260px; margin: 0; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap: 12px; }
  .tile { border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; background: #fff; display: grid; gap: 2px; }
  .tile-chip { font-weight: 650; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .tile-value { font-size: 2rem; font-weight: 650; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; margin-top: 4px; }
  .tile-sub { font-size: 0.8rem; color: var(--muted); }
  .tile-meta { font-size: 0.8rem; color: var(--ink); line-height: 1.5; margin-top: 6px; }
  .dim { color: var(--muted); }
  .tag { font-size: 0.66rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; background: #e8efec; color: var(--ink); }
  .tag.warm { background: #fdeee6; }
  .card { border: 1px solid var(--line); border-radius: 10px; padding: 16px 18px; min-width: 0; background: #fff; display: grid; gap: 10px; }
  .card h3, .section-title { font-size: 1.02rem; }
  .section-title { margin-top: 6px; }
  .card-head { display: flex; justify-content: space-between; align-items: end; gap: 12px; flex-wrap: wrap; }
  .chip-select { margin: 0; flex: 0 1 200px; }
  .chip-select :global(label) { width: 100%; }
  .note { font-size: 0.86rem; color: var(--muted); line-height: 1.5; max-width: 820px; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 0.8rem; color: var(--ink); }
  .legend span { display: inline-flex; align-items: center; gap: 7px; }
  .sym { display: inline-block; width: 10px; height: 10px; background: var(--c); }
  .sym.circle { border-radius: 50%; }
  .sym.diamond { transform: rotate(45deg); width: 9px; height: 9px; }
  .sym.triangle { width: 0; height: 0; background: none; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 10px solid var(--c); }
  .rule { display: inline-block; width: 16px; height: 1px; background: #a2b6b2; }
  .table-scroll { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; font-size: 0.88rem; }
  th, td { text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  thead th { font-size: 0.76rem; color: var(--muted); font-weight: 650; }
  tbody th { font-weight: 600; min-width: 14rem; max-width: 24rem; }
  tr.best th { box-shadow: inset 3px 0 0 var(--teal); }
  .num { display: block; font-size: 1.05rem; font-weight: 650; font-variant-numeric: tabular-nums; }
  .sub { display: block; font-size: 0.76rem; color: var(--muted); font-weight: 400; line-height: 1.4; margin-top: 2px; }
  .role { font-size: 0.66rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; background: #eef1ee; color: #46524f; margin-left: 4px; white-space: nowrap; }
  .role.per_chip { background: #dcefe9; color: #0b4f45; }
  .verdict, .status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; white-space: nowrap; }
  .ok { background: #dcfce7; color: #166534; }
  .bad { background: #fae5dc; color: #9a3412; }
  .mid { background: #fdf3d7; color: #7a5200; }
  .wait { background: #eef1ee; color: #46524f; }
  .verdict.mid { background: #eef1ee; color: #46524f; }
  .claims { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 12px; }
  .claims.three { grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); }
  .claim { border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; background: #fff; display: grid; gap: 8px; align-content: start; }
  .claim p { font-size: 0.88rem; line-height: 1.55; color: var(--ink); }
  .claim-head { font-weight: 650; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .claim.plain { background: #fbfcf9; }
  .limits { margin: 0; padding-left: 18px; font-size: 0.88rem; line-height: 1.6; color: var(--ink); }
  .links { font-size: 0.86rem; color: var(--muted); display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .links button { font: inherit; color: var(--teal); background: none; border: 1px solid var(--line); border-radius: 6px; padding: 4px 10px; cursor: pointer; }
  .links button:hover { background: #eef4f1; }
  @media (max-width: 640px) {
    thead { display: none; }
    table, tbody, tr, th, td { display: block; width: 100%; }
    tbody tr { border-bottom: 1px solid var(--line); padding: 6px 0; }
    tbody th, tbody td { border: 0; padding: 4px 6px; max-width: none; }
    tbody td::before { content: attr(data-label); display: block; font-size: 0.7rem; font-weight: 650; color: var(--muted); }
    tr.best th { box-shadow: none; border-left: 3px solid var(--teal); }
  }
</style>
