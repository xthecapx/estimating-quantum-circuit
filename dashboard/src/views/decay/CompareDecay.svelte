<script lang="ts">
  import { tick } from "svelte";
  import Icon from "../../lib/ui/Icon.svelte";
  import EChart from "../../lib/charts/EChart.svelte";
  import Select from "../../lib/ui/Select.svelte";
  import { algorithmName } from "../../lib/domain/catalog";
  import type { Explorer } from "../../lib/state/explorer.svelte";
  import { bounds, chart, construction, declineLabels, declineStatus, extraLoss, fixed, key, matchingWindows, medianLoss, rankResources, signed, resources, short, targets, type Cell, type Snapshot } from "./model";
  type Choices={matrix:string;pair:string;resource:string;outcome:string};
  let {explorer,reports,choices,onchange}:{explorer:Explorer;reports:Record<string,string>;choices:Choices;onchange:(v:Choices)=>void}=$props();
  let data=$state<Snapshot>();
  let error=$state("");
  $effect(()=>{
    const backend=explorer.backend, filename=reports[backend], controller=new AbortController();
    data=undefined; error="";
    if(filename) {
      fetch(new URL("data/"+filename,document.baseURI),{signal:controller.signal}).then(async r=>{
        if(!r.ok) throw Error("fetch"); const s:Snapshot=await r.json();
        if(s.schemaVersion!==1 || s.backend!==backend || !s.panels) throw Error("schema");
        if(!controller.signal.aborted)data=s;
      }).catch(()=>{if(!controller.signal.aborted)error="The decay measurements could not be loaded. Reload to try again.";});
    }
    return ()=>controller.abort();
  });
  const ranked = $derived(data ? rankResources(data) : []);
  const resourceOption = $derived(ranked.find(r => r.id === choices.resource) ?? ranked[0]);
  const outcomeOptions = $derived(resourceOption?.outcomes ?? []);
  const outcomeOption = $derived(outcomeOptions.find(o => o.id === choices.outcome) ?? outcomeOptions[0]);
  const resourceLabels = $derived(new Map(ranked.map(r => [r.id, (resources[r.id] ?? r.id) + " · " + pairCount(r.count)])));
  const outcomeLabels = $derived(new Map(outcomeOptions.map(o => [o.id, (targets[o.id] ?? o.id) + " · " + pairCount(o.matches.length)])));
  const metric = $derived(resourceOption?.id ?? "");
  const outcome = $derived(outcomeOption?.id ?? "");
  const cells=$derived(data?.panels[metric]?.[outcome]??[]);
  const directional = $derived(choices.matrix === "direction");
  const signedGaps = $derived(new Map(cells.map(c => [key(c), medianLoss(c)])));
  const matches = $derived(outcomeOption?.matches ?? []);
  const requested = $derived(cells.find(c => choices.pair === key(c) || choices.pair === c.b + "/" + c.a));
  const cell = $derived(requested ?? matches[0]?.cell);
  const structure = $derived(cell && construction(cell));
  const selectedMatch = $derived(matches.find(m => m.cell === cell));
  let detailHeading = $state<HTMLHeadingElement>();
  $effect(() => {
    if (data?.backend !== explorer.backend || !metric || !outcome) return;
    const pair = requested ? choices.pair : cell ? key(cell) : "";
    if (choices.resource !== metric || choices.outcome !== outcome || choices.pair !== pair) {
      change({resource: metric, outcome, pair});
    }
  });
  function pairCount(n: number) {
    return n + (n === 1 ? " pair" : " pairs");
  }
  function chooseOutcome(id: string) {
    const keep = outcomeOptions.find(o => o.id === id)?.matches.some(m => cell && key(m.cell) === key(cell));
    change({outcome: id, pair: keep ? choices.pair : ""});
  }
  async function inspect(c: Cell, rowId: string, columnId: string) {
    change({pair: directional ? rowId + "/" + columnId : key(c)});
    await tick();
    detailHeading?.focus();
  }
  const periods=$derived(Object.entries(cell?.periods??{}));
  const reversed = $derived(!!cell && choices.pair === cell.b+"/"+cell.a);
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
  function change(v:Partial<Choices>){onchange({...choices,...v});}
  function pairLabel(k:string){return k.split("/").map(algorithmName).join(" / ");}
  function lookup(a:string,b:string){return cells.find(c=>(c.a===a&&c.b===b)||(c.a===b&&c.b===a));}
  const dates = $derived(new Map(explorer.periods.map(period => {
    const { campaign, window } = period.jobs[0];
    return [campaign + " / window " + window, period.dateLabel] as const;
  })));
  function dateLabel(period: string) { return dates.get(period) ?? "Date unavailable"; }
</script>

<section class="surface compare" aria-label="Decay comparison">
  <ol class="settings controls" aria-label="Choose a decay comparison">
    <li><Select label="Chip" icon="chip" value={explorer.backend} options={explorer.backends} onchange={b=>{change({resource:"", outcome:"", pair:""}); explorer.setBackend(b);}}/></li>
    {#if resourceOption}
      <li>
        <Select label="Resource" icon="depth" value={metric} options={[...resourceLabels.keys()]}
          format={id=>resourceLabels.get(id)??id}
          aria-describedby="resource-ranking" onchange={resource=>change({resource, outcome:"", pair:""})}/>
        <small id="resource-ranking">Distinct pairs across all outcomes on this chip.</small>
      </li>
      <li>
        <Select label="Outcome" icon="shots" value={outcome} options={[...outcomeLabels.keys()]} disabled={!outcomeOptions.length}
          format={id=>outcomeLabels.get(id)??id}
          aria-describedby="outcome-ranking" onchange={chooseOutcome}/>
        <small id="outcome-ranking">Pairs for this resource and outcome.</small>
      </li>
      <li><label class="pair-picker"><span><Icon name="compare" size={15}/> Algorithm pair</span>
        <select aria-label="Algorithm pair" aria-describedby="match-rule" disabled={!matches.length}
          onchange={event=>change({pair:event.currentTarget.value})}>
          {#if !selectedMatch}<option selected disabled value="">{matches.length ? "Choose a matching pair" : "No matching pairs"}</option>{/if}
          {#each matches as m (key(m.cell))}
            <option value={key(m.cell)} selected={m.cell === cell}>{pairLabel(key(m.cell))} · {m.count}/{Object.keys(m.cell.periods).length} windows</option>
          {/each}
        </select>
      </label></li>
    {/if}
  </ol>
  {#if error}<p role="alert">{error}</p>
  {:else if !reports[explorer.backend]}<p role="status">No decay analysis matches the current export for {explorer.backend}.</p>
  {:else if !data}<p role="status">Loading decay measurements…</p>
  {:else if !resourceOption || !outcomeOption}<p role="status">No decay comparisons are available for this selection.</p>
  {:else}
    <p id="match-rule"><strong>{matches.length} of {cells.length} pairs show repeated similar decay.</strong>
      Both fitted outcomes must decline and their losses must differ by at most {data.tolerance} {outcome === "success" ? "percentage points" : "points on the outcome × 100 scale"} in at least {data.minPeriods} windows.
      Each fit needs {data.minLevels} or more exact shared resource levels.</p>
    {#if cell && structure}
      <div class="heading">
        <div><h2 bind:this={detailHeading} tabindex="-1">{algorithmName(cell.a)} and {algorithmName(cell.b)}</h2>
          <p class="note">{targets[outcome]} across shared values of {(resources[metric]??metric).toLowerCase()} on {explorer.backend}.</p></div>
        {#if periods.length}<div class="stat"><strong>{directional ? signed(directionValue(cell,row)) : fixed(cell.gap)} {unit}</strong>
          <span>{directional ? `Median extra loss of ${short(column)} relative to ${short(row)}` : "Median gap in fitted change"}</span></div>{/if}
      </div>
      <div class="evidence">
        <section><p class="eyebrow">Circuit construction</p><h3>{structure.title}</h3><p>{structure.detail}</p></section>
        <section><p class="eyebrow">Measured decay</p>
          {#if periods.length < data.minPeriods}
            <h3>Too few comparable windows</h3>
            <p>{periods.length} of {data.minPeriods} required windows have at least {data.minLevels} shared levels. The largest overlap in one window is {Math.max(0,...Object.values(cell.overlap))}.</p>
          {:else}
            <h3>Similar decline in {selectedMatch?.count ?? matchingWindows(cell,data.tolerance)} of {periods.length} eligible windows</h3>
            <p>{selectedMatch ? "This pair meets the repeatability rule for this resource and outcome." : "This pair falls outside the selector’s repeatability rule for this resource and outcome."}
              {#if directional}{short(column)} lost more or gained less than {short(row)} in {periods.filter(([,v])=>extraLoss(v,reversed)>0).length} windows.{/if}</p>
          {/if}
          <details class="coverage"><summary>Shared levels by window</summary>
            <ul>{#each Object.entries(cell.overlap) as [name, levels]}<li>{name} <strong>{levels}</strong></li>{/each}</ul>
          </details>
        </section>
      </div>
      {#if periods.length}
        <div class="plot-heading"><h3>Fitted trends by collection window</h3>
          <div class="legend"><span>● {algorithmName(cell.a)} · solid</span><span>◆ {algorithmName(cell.b)} · dashed</span></div>
        </div>
        <p class="note">{ylabel}. Each point averages the tested configurations at one shared resource level. Each line fits one algorithm in that window.</p>
        <div class="panels">{#each periods as [p,values] (p)}
          <article><h4 title={p}>{dateLabel(p)}</h4><p class="window-label">{declineLabels[declineStatus(values, data.tolerance)]} · {fixed(values.gap)} {unit} apart</p>
          <EChart option={chart(values,cell,axes,resources[metric]??metric,ylabel)} replace label={pairLabel(key(cell))+" on "+dateLabel(p)} style="height:195px;width:100%"/>
          </article>{/each}</div>
        <details class="fit-details"><summary>Slopes and rank correlations by window</summary>
          <p class="note">Slopes use {unit} per resource unit. The gap measures the difference in fitted changes from the first shared level to the last.
            Spearman ρ ranks the observed means. A value near +1 means the two algorithms rank the levels similarly, even when one loses much more.
            A dash marks a constant profile where ρ is undefined.</p>
          <div class="scroll"><table><thead><tr><th>Collection date (UTC)</th><th>Shared levels</th><th>{short(cell.a)} slope</th><th>{short(cell.b)} slope</th><th>{directional ? `Extra loss of ${short(column)} vs ${short(row)}` : "Gap"} ({unit})</th><th>Profile ρ</th></tr></thead><tbody>
          {#each periods as [p,v]}<tr><td title={p}>{dateLabel(p)}</td><td>{v.points.length}</td><td>{fixed(100*v.slopeA)}</td><td>{fixed(100*v.slopeB)}</td><td>{directional ? signed(extraLoss(v,reversed)) : fixed(v.gap)}</td><td>{fixed(v.rho)}</td></tr>{/each}</tbody></table></div>
        </details>
      {/if}
    {:else}
      <p class="empty" role="status">Choose another resource or outcome to look for repeated decay, or select a pair in the matrix to inspect its evidence.</p>
    {/if}
    <div class="matrix-heading">
      <h3>All algorithm pairs</h3>
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
      <button class:chosen={selected} aria-pressed={selected} aria-label={directional ? `${short(a)} to ${short(b)}: ${signed(delta)} ${unit}` : pairLabel(key(c))} onclick={()=>inspect(c,a,b)}
      style:background-color={directional ? (delta === null || delta === 0 ? "#f1f2ee" : delta > 0 ? "#f6ddca" : "#d9ece6") : c.grouped===null||c.gap===null?"#f1f2ee":`hsl(162 36% ${94-50*Math.exp(-c.gap/data.tolerance)}%)`}>
      {#if !directional && matches.some(m => m.cell === c)}<span aria-hidden="true">✓ </span>{/if}{directional ? signed(delta,1) : c.grouped===null?"—":c.gap?.toFixed(1)}</button>{:else}·{/if}</td>{/each}</tr>{/each}
    </tbody></table></div>
    <p class="note">
      {#if directional}
        A dash means no window has {data.minLevels} shared levels.
      {:else}
        The clustering tolerance is {data.tolerance} {unit}. A dash means fewer than {data.minPeriods} eligible windows.
      {/if}
      A dot marks the same algorithm. Select any pair to inspect its circuit construction and window coverage.
    </p>
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
  .controls { display: grid; grid-template-columns: minmax(9rem,.65fr) repeat(3,minmax(0,1fr)); margin: 0; padding: 0; list-style: none; }
  .controls li { position: relative; min-width: 0; }
  .controls li::before { content: counter(list-item); position: absolute; top: 0; left: 0; display: grid; place-items: center;
    width: 1.4rem; height: 1.4rem; background: #e5f1ec; color: var(--teal); border-radius: 50%; font-size: .76rem; font-weight: 700; pointer-events: none; }
  .controls :global(.field-name), .pair-picker > span { min-height: 1.4rem; padding-inline-start: 1.8rem; }
  .controls small { display: block; margin-top: 5px; font-size: .76rem; color: var(--muted); line-height: 1.4; }
  @media (max-width: 960px) { .controls { grid-template-columns: repeat(2,minmax(0,1fr)); } }
  @media (max-width: 560px) { .controls { grid-template-columns: minmax(0,1fr); } }
  .pair-picker > span, .plot-heading { display: flex; gap: 6px; align-items: center; }
  .plot-heading { justify-content: space-between; flex-wrap: wrap; gap: 8px; }
  .plot-heading + .note { margin-top: -8px; }
  #match-rule, .empty { line-height: 1.5; color: var(--muted); }
  #match-rule { padding-bottom: 14px; border-bottom: 1px solid var(--line); font-size: .85rem; }
  #match-rule strong { color: var(--ink); }
  .evidence { display: grid; grid-template-columns: repeat(auto-fit,minmax(min(100%,270px),1fr)); gap: 12px; }
  .evidence section { padding: 15px 18px; border: 1px solid var(--line); border-radius: 9px; }
  .evidence section:last-child { background: #f2f7f4; }
  .evidence section > p:last-of-type, .window-label { margin-top: 5px; font-size: .85rem; color: var(--muted); line-height: 1.5; }
  .coverage, .fit-details { font-size: .86rem; }
  .coverage { margin-top: 10px; }
  .coverage ul { list-style: none; padding: 0; }
  .coverage li { display: flex; justify-content: space-between; gap: 7px; padding: 3px 0; overflow-wrap: anywhere; }
  summary { cursor: pointer; font-weight: 650; }
  .fit-details > p { margin: 8px 0; }
  .matrix-heading { border-top: 1px solid var(--line); padding-top: 16px; }
</style>
