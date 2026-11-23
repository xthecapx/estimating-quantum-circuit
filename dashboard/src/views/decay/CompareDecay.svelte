<script lang="ts">
  import type { DecayChoices } from "../../lib/state/dashboard";
  import { decayData } from "../../lib/data/load";
  import { tick } from "svelte";
  import { derived } from "svelte/store";
  import EChart from "../../lib/charts/EChart.svelte";
  import Select from "../../lib/ui/Select.svelte";
  import { algorithmName } from "../../lib/domain/catalog";
  import type { Explorer } from "../../lib/state/explorer.svelte";
  import { bounds, chart, construction, declineLabels, declineStatus, extraLoss, fixed, key, matchingWindows, medianLoss, partnerOptions, resourceEvidence, signed, resources, short, targets } from "./model";
  let {explorer,reports,choices,onchange}:{explorer:Explorer;reports:Record<string,string>;choices:DecayChoices;onchange:(v:DecayChoices)=>void}=$props();
  const chips = $derived([...new Set([...explorer.backends, ...Object.keys(reports)])].sort());
  const reportStore = $derived(derived(chips.map(chip => decayData.watch(reports[chip], chip)), results => results));
  const snapshots = $derived($reportStore.flatMap(result => result.data ? [result.data] : []));
  const loading = $derived(chips.some((chip, i) => reports[chip] && !$reportStore[i]?.data && !$reportStore[i]?.error));
  const algorithms = $derived([...new Set(snapshots.flatMap(report => report.algorithms))].sort());
  const requested = $derived(choices.pair.split("/"));
  const algorithm = $derived(algorithms.includes(requested[0]) ? requested[0]
    : algorithms.includes("PHASE-ESTIMATION") ? "PHASE-ESTIMATION" : algorithms[0] ?? "");
  const partners = $derived(partnerOptions(snapshots, algorithm));
  const partner = $derived(partners.find(p => p.id === requested[1]) ?? partners[0]);
  const structure = $derived(partner && construction(partner.cell));
  const outcomes = $derived([...new Set(snapshots.flatMap(report =>
    Object.values(report.panels).flatMap(panel => Object.keys(panel))))]);
  const outcome = $derived(outcomes.includes(choices.outcome) ? choices.outcome
    : outcomes.includes("success") ? "success" : outcomes[0] ?? "");
  const rows = $derived(resourceEvidence(snapshots, algorithm, partner?.id ?? "", outcome));
  const metric = $derived(choices.resource);
  const data = $derived(snapshots.find(report => report.backend === explorer.backend));
  const evidence = $derived(rows.find(row => row.metric === metric)?.chips.get(explorer.backend));
  const cell = $derived(evidence?.cell);
  const cells = $derived(data?.panels[metric]?.[outcome] ?? []);
  const directional = $derived(choices.matrix === "direction");
  const signedGaps = $derived(new Map(cells.map(c => [key(c), medianLoss(c)])));
  const matches = $derived(new Set(data ? cells.filter(c => matchingWindows(c, data.tolerance) >= data!.minPeriods).map(key) : []));
  let detailHeading = $state<HTMLHeadingElement>();

  function chooseAlgorithm(id: string) {
    change({ pair: id, resource: "" });
  }
  async function inspectResource(resource: string, chip: string) {
    explorer.setBackend(chip);
    change({ resource, pair: algorithm + "/" + partner!.id, outcome });
    await tick();
    detailHeading?.focus();
  }
  async function inspectPair(rowId: string, columnId: string) {
    change({ pair: rowId + "/" + columnId });
    await tick();
    detailHeading?.focus();
  }
  const periods=$derived(Object.entries(cell?.periods??{}));
  const gapScale = $derived(Math.max(1, 2 * (data?.tolerance ?? 0), ...periods.map(([,p]) => p.gap)));
  const minPeriods = $derived(data?.minPeriods ?? Infinity);
  let showFits = $state(false);
  const reversed = $derived(!!cell && algorithm === cell.b);
  const row = $derived(cell && reversed ? cell.b : cell?.a ?? "");
  const column = $derived(cell && reversed ? cell.a : cell?.b ?? "");
  function directionValue(c: typeof cells[number], rowId: string) {
    const value = signedGaps.get(key(c));
    return value == null ? null : rowId === c.a ? value : -value;
  }
  const axes=$derived(bounds(periods.map(p=>p[1])));
  const ids=$derived(data?.algorithms??[]);
  const unit=$derived(outcome==="success"?"pp":"points");
  const ylabel=$derived(outcome==="success"?"Success rate (%)":(targets[outcome]+" × 100"));
  function change(v:Partial<DecayChoices>){onchange({...choices,...v});}
  function pairLabel(k:string){return k.split("/").map(algorithmName).join(" / ");}
  function lookup(a:string,b:string){return cells.find(c=>(c.a===a&&c.b===b)||(c.a===b&&c.b===a));}
  const dates = $derived(new Map(explorer.periods.map(period => {
    const { campaign, window } = period.jobs[0];
    return [campaign + " / window " + window, period.dateLabel] as const;
  })));
  function dateLabel(period: string) { return dates.get(period) ?? "Date unavailable"; }
</script>

<section class="surface compare" aria-label="Decay comparison">
  {#if loading}
    <p role="status">Loading chip comparisons…</p>
  {:else if !snapshots.length}
    {#if $reportStore.some(result => result.error)}
      <p role="alert">The decay reports could not be loaded. Reload to try again.</p>
    {:else}
      <p role="status">No decay reports are available for this export.</p>
    {/if}
  {:else}
    <div class="settings controls">
      <Select label="Algorithm" icon="qubits" value={algorithm} options={algorithms} format={algorithmName} onchange={chooseAlgorithm}/>
      <label><span class="field-name">Compare with</span>
        <select aria-label="Compare with" value={partner?.id} onchange={event => change({pair: algorithm + "/" + event.currentTarget.value, resource: ""})}>
          {#each [true, false] as related}
            {@const group = partners.filter(p => p.related === related)}
            {#if group.length}
              <optgroup label={related ? "Related circuit constructions" : "Other measured algorithms"}>
                {#each group as p (p.id)}<option value={p.id}>{algorithmName(p.id)}</option>{/each}
              </optgroup>
            {/if}
          {/each}
        </select>
      </label>
      <Select label="Outcome" icon="shots" value={outcome} options={outcomes} format={id => targets[id] ?? id}
        onchange={outcome => change({outcome, resource: ""})}/>
    </div>
    {#if structure && partner}
      <header class="relationship">
        <h2>{algorithmName(algorithm)} and {algorithmName(partner.id)}</h2>
        <h3>{structure.title}</h3><p>{structure.detail}</p>
      </header>
      <section class="overview" aria-labelledby="overview-title">
        <h3 id="overview-title">Does the decline in {targets[outcome]?.toLowerCase() ?? outcome} repeat across chips?</h3>
        <p class="note">A window matches when both algorithms decline by similar amounts over the same resource range. Select a count to see the fitted changes on that chip.</p>
        <div class="scroll"><table class="evidence" aria-labelledby="overview-title"><thead><tr><th scope="col">Circuit resource</th>
          {#each chips as chip}<th scope="col">{chip}</th>{/each}
        </tr></thead><tbody>
          {#each rows as row (row.metric)}
            <tr><th scope="row">{resources[row.metric] ?? row.metric}</th>
              {#each chips as chip, i}
                {@const result = row.chips.get(chip)}
                <td>{#if result}
                  <button class:repeat={result.matched >= result.minimum}
                    aria-label={`${resources[row.metric] ?? row.metric}, ${chip}, ${result.matched} of ${result.eligible} windows match${result.eligible < result.minimum ? ", insufficient coverage" : ""}`}
                    aria-pressed={metric === row.metric && explorer.backend === chip}
                    onclick={() => inspectResource(row.metric, chip)}>
                    {#if result.eligible < result.minimum}
                      <strong>{result.eligible} eligible</strong><small>Insufficient coverage</small>
                    {:else}
                      <strong>{result.matched} of {result.eligible}</strong>
                      <small>{result.matched >= result.minimum ? "Repeated match" : "No repeated match"}</small>
                    {/if}
                  </button>
                {:else}<span class="note">{$reportStore[i]?.error ? "Load failed" : reports[chip] ? "No comparison" : "No report"}</span>{/if}</td>
              {/each}
            </tr>
          {/each}
        </tbody></table></div>
        <details><summary>How to read the comparison</summary>
          {#each snapshots as report}
            <p>{report.backend} requires at least {report.minLevels} shared resource levels in a window. Both fitted outcomes must fall and their losses must be within {report.tolerance} {outcome === "success" ? "percentage points" : "points on the outcome × 100 scale"} of each other. A repeated match requires {report.minPeriods} matching windows.</p>
          {/each}
          <p>Each chip uses its own collection windows and shared levels. Rows with repeated matches on more chips appear first.</p>
        </details>
      </section>
    {/if}
    {#if cell && data && evidence}
      <div class="pair-result" class:matched={evidence.matched >= minPeriods}>
        <div class="heading">
          <div><p class="eyebrow">{resources[metric] ?? metric}</p>
            <h2 bind:this={detailHeading} tabindex="-1">{targets[outcome]} on {data.backend}</h2>
            <p class="note">{algorithmName(algorithm)} and {algorithmName(partner?.id ?? "")}</p></div>
          {#if periods.length}<div class="stat"><strong>{directional ? signed(directionValue(cell,row)) : fixed(cell.gap)} {unit}</strong>
            <span>{directional ? `Median extra loss of ${short(column)} relative to ${short(row)}` : "Median gap in fitted change"}</span></div>{/if}
        </div>
        {#if periods.length < data.minPeriods}
          <h3>Too few comparable windows</h3>
          <p>{periods.length} of {data.minPeriods} required windows have at least {data.minLevels} shared levels.
            The largest overlap in one window is {Math.max(0,...Object.values(cell.overlap))}.</p>
        {:else}
          <h3>Similar decline in {evidence.matched} of {periods.length} eligible windows</h3>
          <p>A window matches when both fitted outcomes fall and their losses differ by at most {data.tolerance} {outcome === "success" ? "percentage points" : "points on the outcome × 100 scale"} over the shared range.</p>
        {/if}
      </div>
      {#if periods.length}
        <figure class="gap-chart">
          <figcaption><h3>How far apart were the fitted changes?</h3>
            <span class="threshold-key">Tolerance · {data.tolerance} {unit}</span></figcaption>
          <ul>{#each periods as [name,p] (name)}
            {@const status = declineStatus(p, data.tolerance)}
            <li class:similar={status === "similar"}>
              <span class="window" title={name}>{dateLabel(name)}</span>
              <div class="track" aria-hidden="true"><i style:width={(100*p.gap/gapScale)+"%"}></i><b style:left={(100*data.tolerance/gapScale)+"%"}></b></div>
              <strong>{fixed(p.gap)} {unit}</strong><span class="status">{declineLabels[status]}</span>
            </li>
          {/each}</ul>
        </figure>
        <details class="disclosure" bind:open={showFits}>
          <summary>Observed outcomes and fitted trends</summary>
          {#if showFits}
        <div class="plot-heading"><h3>Fitted trends by collection window</h3>
          <div class="legend"><span>● {algorithmName(cell.a)} · solid</span><span>◆ {algorithmName(cell.b)} · dashed</span></div>
        </div>
        <p class="note">{ylabel}. Each point averages the tested configurations at one shared resource level. Each line fits one algorithm in that window.</p>
        <div class="panels">{#each periods as [p,values] (p)}
          <article><h4 title={p}>{dateLabel(p)}</h4><p class="window-label">{declineLabels[declineStatus(values, data.tolerance)]} · {fixed(values.gap)} {unit} apart</p>
          <EChart option={chart(values,cell,axes,resources[metric]??metric,ylabel)} replace label={pairLabel(key(cell))+" on "+dateLabel(p)} style="height:195px;width:100%"/>
          </article>{/each}</div>
          {/if}
        </details>
        <details class="fit-details disclosure"><summary>Slopes and rank correlations by window</summary>
          <p class="note">Slopes use {unit} per resource unit. The gap measures the difference in fitted changes from the first shared level to the last.
            Spearman ρ ranks the observed means. A value near +1 means the two algorithms rank the levels similarly, even when one loses much more.
            A dash marks a constant profile where ρ is undefined.</p>
          <div class="scroll"><table><thead><tr><th>Collection date (UTC)</th><th>Shared levels</th><th>{short(cell.a)} slope</th><th>{short(cell.b)} slope</th><th>{directional ? `Extra loss of ${short(column)} vs ${short(row)}` : "Gap"} ({unit})</th><th>Profile ρ</th></tr></thead><tbody>
          {#each periods as [p,v]}<tr><td title={p}>{dateLabel(p)}</td><td>{v.points.length}</td><td>{fixed(100*v.slopeA)}</td><td>{fixed(100*v.slopeB)}</td><td>{directional ? signed(extraLoss(v,reversed)) : fixed(v.gap)}</td><td>{fixed(v.rho)}</td></tr>{/each}</tbody></table></div>
        </details>
      {/if}
      <details class="coverage disclosure"><summary>Shared levels by window</summary>
        <ul>{#each Object.entries(cell.overlap) as [name, levels]}<li>{name} <strong>{levels}</strong></li>{/each}</ul>
      </details>
    <details class="disclosure matrix-section"><summary>Explore all algorithm pairs <span>({cells.length})</span></summary>
    <div class="matrix-heading">

      <div class="settings matrix-settings">
        <Select label="Matrix view" value={choices.matrix} options={["similarity","direction"]} format={v=>v==="direction"?"Direction":"Similarity"} onchange={matrix=>change({matrix})}/>
      </div>
    </div>
    <div class="matrix-intro">
      <h4 id="matrix-guide">
        {directional ? "Which algorithm shows the larger fitted decrease in" : "Which algorithm pairs show similar changes in"}
        {targets[outcome].toLowerCase()} across the shared range of {resources[metric].toLowerCase()}?
      </h4>
      <div class="matrix-callout">
        <p id="matrix-reading">
          {#if directional}
            Read from row to column. A positive value means the column algorithm fell more or gained less.
            A negative value means the row algorithm did.
          {:else}
            Values closer to zero mean the two fitted lines changed by similar amounts over the shared range.
            Darker cells indicate smaller gaps, including for flat or rising outcomes. A check marks repeated similar decay.
          {/if}
          Each cell shows the median {directional ? "signed difference" : "absolute gap"} across eligible windows,
          in {outcome === "success" ? "percentage points" : "points on the outcome × 100 scale"}.
        </p>
        {#if cell}<p class="matrix-example" aria-live="polite">
          <strong>{directional ? short(row) + " → " + short(column) : short(cell.a) + " / " + short(cell.b)}</strong>
          {#if periods.length >= (directional ? 1 : data.minPeriods)}
            · Window {directional ? "differences" : "gaps"} ({unit}):
            {periods.map(([,v]) => directional ? signed(extraLoss(v,reversed)) : fixed(v.gap)).join(", ")}.
            Median <strong>{directional ? signed(directionValue(cell,row)) : fixed(cell.gap)} {unit}</strong>.
          {:else}
            · {periods.length} of {directional ? 1 : data.minPeriods} required windows have at least {data.minLevels} shared resource levels.
          {/if}
        </p>{/if}
      </div>
    </div>
    <div class="scroll"><table class="matrix" aria-labelledby="matrix-guide" aria-describedby="matrix-reading"><thead><tr><th>Pair</th>{#each ids as a}<th>{short(a)}</th>{/each}</tr></thead><tbody>
    {#each ids as a}<tr><th>{short(a)}</th>{#each ids as b}{@const c=lookup(a,b)}<td>
    {#if c}{@const selected=directional ? a===row && b===column : !!cell && key(c)===key(cell)}
      {@const delta=directionValue(c,a)}
      <button class:chosen={selected} aria-pressed={selected} aria-label={directional ? `${short(a)} to ${short(b)}: ${signed(delta)} ${unit}` : pairLabel(key(c))} onclick={()=>inspectPair(a,b)}
      style:background-color={directional ? (delta === null || delta === 0 ? "#f1f2ee" : delta > 0 ? "#f6ddca" : "#d9ece6") : c.grouped===null||c.gap===null?"#f1f2ee":`hsl(162 36% ${94-50*Math.exp(-c.gap/data.tolerance)}%)`}>
      {#if !directional && matches.has(key(c))}<span aria-hidden="true">✓ </span>{/if}{directional ? signed(delta,1) : c.grouped===null?"—":c.gap?.toFixed(1)}</button>{:else}·{/if}</td>{/each}</tr>{/each}
    </tbody></table></div>
    <p class="note">
      {#if directional}
        A dash means no window has {data.minLevels} shared levels.
      {:else}
        The clustering tolerance is {data.tolerance} {unit}. A dash means fewer than {data.minPeriods} eligible windows.
      {/if}
      A dot marks the same algorithm. Select any pair to inspect its circuit construction and window coverage.
    </p>
    </details>
    {:else if metric}
      <p role="status">The selected chip and resource have no detail available for this comparison.</p>
    {/if}
  {/if}
</section>
<style>
  .matrix-heading { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
  .matrix-settings { margin: 0; width: min(100%, 12rem); }
  .matrix-intro { display: grid; gap: 8px; }
  #matrix-guide { margin: 0; font-size: 1rem; font-weight: 700; line-height: 1.45; }
  .matrix-callout { background: #f1f6f3; border-inline-start: 3px solid var(--teal); padding: 10px 14px; line-height: 1.5; }
  .matrix-callout p { margin: 0; }
  .matrix-callout .matrix-example { margin-top: 6px; }
.compare{padding:clamp(12px,2.3vw,28px);display:grid;gap:14px}
.heading{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.heading h2{font:500 clamp(1.6rem,3vw,2.5rem) Georgia,serif}.stat{border-left:3px solid var(--teal);padding-left:14px;display:grid}.stat strong{font-size:1.55rem}.stat span{font-size:.78rem;color:var(--muted)}.legend{display:flex;gap:20px;flex-wrap:wrap;font-size:.85rem;font-weight:650}.legend span:first-child{color:var(--teal)}.legend span:last-child{color:#a03e10}.panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,255px),1fr));gap:10px}.panels article{min-width:0;border:1px solid var(--line);padding:12px 6px 0;border-radius:9px}.panels h4,.window-label{padding:0 8px}.scroll{max-width:100%;overflow:auto}.compare{min-width:0}.matrix{table-layout:fixed;min-width:500px}.matrix th,.matrix td{text-align:center;padding:2px}.matrix button{width:100%;min-height:34px;border:0;border-radius:3px;color:var(--ink);cursor:pointer;font:inherit}.matrix button.chosen{outline:2px solid var(--ink);outline-offset:-2px}.matrix button:hover{box-shadow:inset 0 0 0 1px var(--teal)}
  .controls { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,14rem),1fr)); gap:12px; margin:0; }
  .relationship { padding:8px 0; }
  .relationship h2 { font:500 clamp(1.6rem,3vw,2.5rem) Georgia,serif; margin:0 0 10px; }
  .relationship h3, .overview h3 { margin:0; }
  .relationship p, .overview p { line-height:1.5; margin:6px 0; }
  .overview { display:grid; gap:6px; min-width:0; }
  .evidence { width:100%; border-collapse:collapse; }
  .evidence tbody th { position:static; background:white; }
  .evidence td,.evidence th { padding:6px; vertical-align:middle; }
  .evidence button { width:100%; padding:6px 8px; border:1px solid var(--line); border-radius:6px; background:#f6f7f5; text-align:left; color:var(--ink); cursor:pointer; }
  .evidence button.repeat { background:#e5f1ec; color:#16594b; }
  .evidence button[aria-pressed="true"] { outline:2px solid var(--ink); outline-offset:-2px; }
  .evidence small { display:block; line-height:1.25; }
  .plot-heading { display:flex; }
  .plot-heading { justify-content: space-between; flex-wrap: wrap; gap: 8px; }
  .plot-heading + .note { margin-top: -8px; }

  .coverage ul { list-style: none; padding: 0; }
  .coverage li { display: flex; justify-content: space-between; gap: 7px; padding: 3px 0; overflow-wrap: anywhere; }
  summary { cursor: pointer; font-weight: 650; }

  .pair-result { border:1px solid var(--line); border-inline-start:4px solid #929e99; background:#f7f8f6; padding:clamp(14px,2vw,22px); border-radius:10px; }
  .pair-result.matched { background:#eff7f3; border-inline-start-color:var(--teal); }
  .pair-result > h3 { margin-top:16px; font-size:1.12rem; }
  .pair-result > p { margin-top:4px; font-size:.89rem; line-height:1.5; }
  .gap-chart { margin:0; padding:clamp(12px,1.8vw,20px); border:1px solid var(--line); border-radius:10px; }
  .gap-chart figcaption { display:flex; justify-content:space-between; align-items:baseline; gap:10px; flex-wrap:wrap; }
  .threshold-key { font-size:.78rem; color:var(--muted); display:inline-flex; gap:6px; align-items:center; }
  .threshold-key::before { content:""; height:1em; border-inline-start:2px dashed #586962; }
  .gap-chart ul { list-style:none; margin:10px 0 0; padding:0; }
  .gap-chart li { display:grid; grid-template-columns:minmax(7rem,1fr) minmax(70px,3fr) 6.5rem 8rem; align-items:center; gap:10px; padding:7px 0; font-size:.86rem; font-variant-numeric:tabular-nums; }
  .gap-chart strong { text-align:end; }
  .track { position:relative; height:10px; border-radius:3px; background:#e6ebe8; }
  .track i { height:100%; display:block; background:#8a7769; border-radius:3px; }
  .similar .track i { background:var(--teal); }
  .track b { position:absolute; top:-4px; bottom:-4px; border-inline-start:2px dashed #586962; }
  .status { color:#695448; } .similar .status { color:var(--teal); }
  .disclosure { margin:0; border-top:1px solid var(--line); padding-top:6px; min-width:0; }
  .disclosure[open] > :not(summary) { margin-top:10px; }
  .matrix-section summary span { color:var(--muted); font-weight:400; }
  @media (max-width:640px) {
    .gap-chart li { grid-template-columns:minmax(0,1fr) 8rem; gap:4px 12px; }
    .track { grid-column:1; grid-row:2; } .gap-chart strong { grid-column:2; grid-row:2; }
    .gap-chart .status { grid-column:2; grid-row:1; font-size:.78rem; }
  }
</style>
