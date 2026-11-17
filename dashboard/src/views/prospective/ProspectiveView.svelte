<script lang="ts" module>
  export interface ProspectiveChoices {
    target: string;
    regime: string;
    chip: string;
  }
</script>

<script lang="ts">
  import EChart from "../../lib/charts/EChart.svelte";
  import Select from "../../lib/ui/Select.svelte";
  import {
    CHIP_LABELS,
    GROUP_HELP,
    GROUP_LABELS,
    H1_THRESHOLD,
    REGIME_LABELS,
    TARGET_LABELS,
    VERDICT_LABELS,
    findScore,
    fmt,
    intervalChart,
    modelsFor,
    parityChart,
    transferLabel,
    type ChipRun,
    type Group,
    type ProspectiveSnapshot,
    type ScoreRow,
  } from "./model";

  let {
    reports,
    choices,
    onchange,
  }: {
    reports: Record<string, string>;
    choices: ProspectiveChoices;
    onchange: (v: ProspectiveChoices) => void;
  } = $props();

  let data = $state<ProspectiveSnapshot>();
  let error = $state("");

  $effect(() => {
    const filename = reports["validation-v1"];
    const controller = new AbortController();
    data = undefined;
    error = "";
    if (!filename) return;
    fetch(new URL("data/" + filename, document.baseURI), { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw Error("fetch");
        const s: ProspectiveSnapshot = await r.json();
        if (s.schemaVersion !== 1 || !s.scores || !s.chips) throw Error("schema");
        if (!controller.signal.aborted) data = s;
      })
      .catch(() => {
        if (!controller.signal.aborted) error = "The validation results could not be loaded. Reload to try again.";
      });
    return () => controller.abort();
  });

  const targets = ["success", "hellinger", "tvd", "dsr"] as const;
  const groups: Group[] = ["new", "anchor", "extrapolation"];

  const target = $derived(targets.includes(choices.target as never) ? choices.target : "success");
  const regime = $derived(choices.regime === "mixed_submit" ? "mixed_submit" : "circuit_only");
  const chips = $derived(
    [...(data?.chips ?? [])].sort((a, b) => (a.qpu === b.qpu ? a.backend.localeCompare(b.backend) : a.qpu === "seen" ? -1 : 1)),
  );
  const chip = $derived(chips.find((c) => c.backend === choices.chip) ?? chips[0]);

  /** Headline rows: every chip × every model that predicted it, `new` group. */
  function rowsFor(group: ScoreRow["group"]) {
    if (!data) return [];
    return chips.flatMap((c) =>
      modelsFor(c, data!.scores).map((scope) => ({
        chip: c,
        scope,
        label: `${(CHIP_LABELS[c.backend] ?? c.backend).replace("IBM ", "")}\n${scope === c.backend ? "own model" : scope === "pooled" ? "pooled model" : `${(CHIP_LABELS[scope] ?? scope).replace("IBM ", "")} model`}`,
        score: findScore(data!.scores, { backend: c.backend, scope, target, regime, group }),
      })),
    );
  }
  const newRows = $derived(rowsFor("new"));

  /** One headline number per chip: its default model on new circuits. */
  function headline(c: ChipRun) {
    if (!data) return undefined;
    const scope = modelsFor(c, data.scores)[0];
    return { scope, score: findScore(data.scores, { backend: c.backend, scope, target, regime, group: "new" }) };
  }

  const chipModels = $derived(chip && data ? modelsFor(chip, data.scores) : []);
  const scatterScope = $derived(chipModels[0]);
  const scatterPoints = $derived(
    data && chip
      ? data.points.filter((p) => p.backend === chip.backend && p.scope === scatterScope && p.target === target && p.regime === regime)
      : [],
  );

  function change(v: Partial<ProspectiveChoices>) {
    onchange({ ...choices, ...v });
  }

  const verdictClass = (v?: string) => (v === "pass" ? "ok" : v === "fail" ? "bad" : "mid");
  const day = (iso?: string) => (iso ? iso.slice(0, 10) : "");
</script>

<section class="surface prospective" aria-label="Prospective validation">
  {#if error}
    <p role="alert">{error}</p>
  {:else if !reports["validation-v1"]}
    <p class="note">No prospective validation snapshot matches the current export. Run <code>python dashboard/export_prospective.py</code>, then rebuild.</p>
  {:else if !data}
    <p role="status">Loading validation results…</p>
  {:else}
    <div class="lead">
      <p class="eyebrow">Prospective validation · the real test</p>
      <h2>How well do frozen QAQS models predict new QPU runs?</h2>
      <p class="intro-text">
        Models were frozen, then their predictions for {data.chips[0]?.configs ?? 42} circuits were committed
        <strong>before</strong> the jobs ran on three IBM chips. Every number here compares those committed predictions with
        what the hardware actually returned. Training-data validation appears only as a reference.
      </p>
    </div>

    <div class="settings controls">
      <Select
        label="Quality metric"
        value={target}
        options={targets}
        format={(k) => TARGET_LABELS[k] ?? k}
        onchange={(t) => change({ target: t })}
      />
      <Select
        label="Model inputs"
        value={regime}
        options={["circuit_only", "mixed_submit"]}
        format={(r) => REGIME_LABELS[r] ?? r}
        onchange={(r) => change({ regime: r })}
      />
    </div>

    <div class="tiles" role="list">
      {#each chips as c (c.backend)}
        {@const h = headline(c)}
        <article class="tile" role="listitem">
          <p class="tile-chip">
            {CHIP_LABELS[c.backend] ?? c.backend}
            <span class="qpu" class:unseen={c.qpu === "unseen"}>{c.qpu === "unseen" ? "unseen QPU" : "seen QPU"}</span>
          </p>
          <p class="tile-value">R² {fmt(h?.score?.r2)}</p>
          <p class="tile-ci">95% CI [{fmt(h?.score?.r2CiLow)}, {fmt(h?.score?.r2CiHigh)}] · MAE {fmt(h?.score?.mae, 3)}</p>
          <p class="tile-meta">
            New circuits · {transferLabel(c, h?.scope ?? "")}<br />
            <span class="verdict {verdictClass(h?.score?.h1Verdict)}">
              {h?.score ? VERDICT_LABELS[h.score.h1Verdict] : "—"}
            </span>
            vs H1 ≥ {H1_THRESHOLD.toFixed(2)}
          </p>
        </article>
      {/each}
    </div>

    <article class="card">
      <h3>New circuits on every chip and model</h3>
      <p class="note">
        Blue dot: R² on the new run, with its 95% interval (resampled by circuit). Orange diamond: the same frozen
        model's score on training-data validation (unseen circuits, training windows). Passing H1 needs the whole
        interval right of {H1_THRESHOLD.toFixed(2)}.
      </p>
      <EChart
        option={intervalChart(newRows)}
        replace
        label="R² with 95% intervals for new circuits, per chip and model"
        style={`height:${Math.max(240, 60 + newRows.length * 44)}px;width:100%`}
      />
      <div class="legend" aria-hidden="true">
        <span><i class="dot blue"></i>New-run R² and 95% CI</span>
        <span><i class="diamond"></i>Training-data validation (reference)</span>
        <span><i class="rule"></i>H1 threshold</span>
      </div>
    </article>

    <article class="card">
      <h3>Known, new and larger circuits</h3>
      <p class="note">R² on the new run by circuit group. Rows marked unseen QPU are zero-shot: no training data from that chip.</p>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Chip · model</th>
              {#each groups as g}<th scope="col" title={GROUP_HELP[g]}>{GROUP_LABELS[g]}</th>{/each}
              <th scope="col">Training-data validation</th>
            </tr>
          </thead>
          <tbody>
            {#each chips as c (c.backend)}
              {#each modelsFor(c, data.scores) as scope (scope)}
                {@const ref = findScore(data.scores, { backend: c.backend, scope, target, regime, group: "all" })}
                <tr class:unseen-row={c.qpu === "unseen"}>
                  <th scope="row">
                    {CHIP_LABELS[c.backend] ?? c.backend}
                    <span class="sub">{transferLabel(c, scope)}</span>
                  </th>
                  {#each groups as g}
                    {@const s = findScore(data.scores, { backend: c.backend, scope, target, regime, group: g })}
                    <td data-label={GROUP_LABELS[g]}>
                      <span class="num">{fmt(s?.r2)}</span>
                      <span class="sub">[{fmt(s?.r2CiLow)}, {fmt(s?.r2CiHigh)}] · MAE {fmt(s?.mae, 3)}</span>
                      {#if g === "new" && s && regime === "circuit_only"}
                        <span class="verdict {verdictClass(s.h1Verdict)}">{VERDICT_LABELS[s.h1Verdict]}</span>
                      {/if}
                    </td>
                  {/each}
                  <td class="ref" data-label="Training-data validation"><span class="num">{fmt(ref?.trainingR2)}</span><span class="sub">MAE {fmt(ref?.trainingMae, 3)}</span></td>
                </tr>
              {/each}
            {/each}
          </tbody>
        </table>
      </div>
      <dl class="groups">
        {#each groups as g}<div><dt>{GROUP_LABELS[g]}</dt><dd>{GROUP_HELP[g]}</dd></div>{/each}
      </dl>
    </article>

    <article class="card">
      <div class="card-head">
        <h3>Predicted vs observed, per circuit</h3>
        <div class="settings chip-select">
        <Select
          label="Chip"
          value={chip?.backend ?? ""}
          options={chips.map((c) => c.backend)}
          format={(b) => `${CHIP_LABELS[b] ?? b}${chips.find((c) => c.backend === b)?.qpu === "unseen" ? " (unseen QPU)" : ""}`}
          onchange={(b) => change({ chip: b })}
        />
        </div>
      </div>
      {#if chip}
        <p class="note">
          {CHIP_LABELS[chip.backend]} · {transferLabel(chip, scatterScope ?? "")}. Each marker is one circuit (mean of its
          repetitions). On the diagonal = perfect prediction.
        </p>
        <EChart
          option={parityChart(scatterPoints, TARGET_LABELS[target] ?? target)}
          replace
          label="Pre-registered prediction against observed value per circuit"
          style="height:380px;width:100%"
        />
        <div class="legend" aria-hidden="true">
          <span><i class="dot blue"></i>Known circuits</span>
          <span><i class="diamond orange"></i>New circuits</span>
          <span><i class="tri"></i>Larger circuits</span>
        </div>
      {/if}
    </article>

    <details class="provenance">
      <summary>How this was run</summary>
      <ul>
        {#each chips as c (c.backend)}
          <li>
            <strong>{CHIP_LABELS[c.backend] ?? c.backend}</strong> ({c.qpu === "unseen" ? "no training data" : "training chip"}):
            {c.configs} circuits, {c.jobs} jobs, executed {day(c.executedFrom)}. Predictions pre-registered
            {day(c.createdAt)} at commit <code>{(c.gitCommit ?? "").slice(0, 8)}</code>.
          </li>
        {/each}
        <li>Models trained on {data.chips[0]?.trainingChips.map((b) => CHIP_LABELS[b] ?? b).join(" and ")} only; validation data never entered training.</li>
        <li>All three chips are IBM Heron (156 qubits): Marrakesh tests an unseen <em>chip</em>, not an unseen provider.</li>
        <li>Intervals: 95% cluster bootstrap, resampling whole circuits. Verdicts use the pre-registered rule only for circuit-footprint models on new circuits.</li>
      </ul>
    </details>
  {/if}
</section>

<style>
  .prospective { padding: clamp(12px, 2.3vw, 28px); display: grid; gap: 18px; min-width: 0; }
  .lead h2 { font: 500 clamp(1.4rem, 2.6vw, 2.1rem) Georgia, serif; margin: 2px 0 8px; }
  .intro-text { max-width: 760px; color: var(--muted); line-height: 1.55; }
  .controls { border-bottom: 1px solid var(--line); padding-bottom: 14px; margin: 0; }
  .controls :global(label) { flex: 1 1 200px; min-width: 0; }
  .controls :global(select) { width: 100%; min-width: 0; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap: 12px; }
  .tile { border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; background: #fff; display: grid; gap: 3px; }
  .tile-chip { font-weight: 650; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .tile-value { font-size: 1.9rem; font-weight: 650; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
  .tile-ci, .tile-meta { font-size: 0.8rem; color: var(--muted); line-height: 1.45; }
  .qpu { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; background: #e8efec; color: var(--ink); }
  .qpu.unseen { background: #fdeee6; }
  .verdict { display: inline-block; padding: 1px 7px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; }
  .verdict.ok { background: #dcfce7; color: #166534; }
  .verdict.bad { background: #fae5dc; color: #9a3412; }
  .verdict.mid { background: #eef1ee; color: #46524f; }
  .card { border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; min-width: 0; background: #fff; display: grid; gap: 8px; }
  .card h3 { font-size: 1rem; }
  .card-head { display: flex; justify-content: space-between; align-items: end; gap: 12px; flex-wrap: wrap; }
  .note { font-size: 0.84rem; color: var(--muted); line-height: 1.45; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 0.78rem; color: var(--muted); }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .legend i { display: inline-block; }
  .dot { width: 10px; height: 10px; border-radius: 50%; }
  .dot.blue { background: #2a78d6; }
  .diamond { width: 9px; height: 9px; background: #eb6834; transform: rotate(45deg); }
  .tri { width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 10px solid #1baf7a; }
  .rule { width: 2px; height: 12px; background: #9a5b12; }
  .table-scroll { overflow-x: auto; }
  .chip-select { margin: 0; width: min(100%, 16rem); }
  .chip-select :global(label) { width: 100%; }
  .chip-select :global(select) { width: 100%; }
  @media (max-width: 640px) {
    thead { display: none; }
    table, tbody, tr, th, td { display: block; width: 100%; }
    tbody tr { border-bottom: 1px solid var(--line); padding: 6px 0; }
    tbody th, tbody td { border: 0; padding: 4px 6px; }
    tbody td::before { content: attr(data-label); display: block; font-size: 0.7rem; font-weight: 650; color: var(--muted); }
    tr.unseen-row th { box-shadow: none; border-left: 3px solid #eb6834; }
  }
  table { border-collapse: collapse; width: 100%; font-size: 0.86rem; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  thead th { font-size: 0.76rem; color: var(--muted); font-weight: 650; }
  tbody th { font-weight: 600; min-width: 11rem; }
  .num { display: block; font-size: 1.02rem; font-weight: 650; font-variant-numeric: tabular-nums; }
  .sub { display: block; font-size: 0.74rem; color: var(--muted); font-weight: 400; }
  td.ref .num { color: var(--muted); font-weight: 500; }
  tr.unseen-row th { box-shadow: inset 3px 0 0 #eb6834; }
  .groups { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); gap: 8px 18px; margin: 6px 0 0; }
  .groups dt { font-weight: 600; font-size: 0.84rem; }
  .groups dd { margin: 2px 0 0; font-size: 0.8rem; color: var(--muted); line-height: 1.4; }
  .provenance { font-size: 0.84rem; color: var(--muted); }
  .provenance summary { cursor: pointer; font-weight: 600; color: var(--ink); }
  .provenance ul { margin: 8px 0 0; padding-left: 18px; line-height: 1.55; }
</style>
