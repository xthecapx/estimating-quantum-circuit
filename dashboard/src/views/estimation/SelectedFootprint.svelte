<script lang="ts">
  import Icon from "../../lib/ui/Icon.svelte";
  import type { TargetReport } from "./model";
  import { footprintMetric } from "./footprintMetrics";

  let { report }: { report: TargetReport } = $props();
  const selected = $derived(report.footprint
    .filter(f => report.selectedFootprintFeatures?.includes(f.feature) ?? f.selected !== false)
    .map(f => ({...f, ...footprintMetric(f.feature, f.label)})));
  let inspected = $state("");
  const active = $derived(selected.find(f => f.feature === inspected) ?? selected[0]);
  const groups = [
    {prefix:"a.", label:"Logical circuit", icon:"qubits"},
    {prefix:"b.", label:"Compiled circuit", icon:"chip"},
  ] as const;
</script>

<section class="footprint" aria-labelledby="footprint-title">
  <h3 id="footprint-title">Selected footprint</h3>
  <p>The regressors share these inputs when trained on the full scope for {report.label.toLowerCase()}. Select a metric to read its definition.</p>
  <div class="groups">
    {#each groups as group}
      {@const items = selected.filter(f => f.feature.startsWith(group.prefix))}
      <section class:compiled={group.prefix === "b."}>
        <h4><Icon name={group.icon} size={18}/>{group.label} <span>{items.length}</span></h4>
        <div class="variables">{#each items as f (f.feature)}
          <button type="button" aria-pressed={f === active} onclick={() => inspected = f.feature}>{f.name}</button>
        {:else}<p>No metrics selected from this circuit.</p>{/each}</div>
      </section>
    {/each}
  </div>
  {#if active}
    <div class="definition" aria-live="polite">
      <h4>{active.name}</h4><p>{active.meaning}</p><code>{active.feature}</code>
    </div>
  {/if}
</section>

<style>
  .footprint { min-width:0; padding:clamp(14px,2vw,24px); border:1px solid #afc9bf; border-radius:12px; background:#fff; }
  .footprint > h3 { font-size:1.22rem; }
  p { margin:5px 0; font-size:.88rem; line-height:1.5; color:var(--muted); }
  .groups { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,285px),1fr)); gap:12px; margin:16px 0; }
  .groups section { --tone:#156c5d; --fill:#ecf5f0; --edge:#b6d3c6; border-top:3px solid var(--tone); padding:12px; background:var(--fill); }
  .groups .compiled { --tone:#35567b; --fill:#f0f4f8; --edge:#c3d1df; }
  h4 { display:flex; align-items:center; gap:7px; } h4 span { margin-left:auto; font-variant-numeric:tabular-nums; color:var(--tone); }
  .variables { display:flex; gap:6px; flex-wrap:wrap; margin-top:12px; }
  button { cursor:pointer; border:1px solid var(--edge); border-radius:6px; background:#fff; color:var(--tone); padding:7px 10px; font:inherit; font-size:.84rem; }
  button[aria-pressed="true"] { background:var(--tone); color:white; border-color:var(--tone); font-weight:650; }
  .definition { border-inline-start:3px solid var(--teal); padding:3px 12px; }
  code { overflow-wrap:anywhere; font-size:.74rem; color:var(--muted); }
</style>
