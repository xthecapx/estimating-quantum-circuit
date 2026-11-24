<script lang="ts">
  import { algorithmName } from "../lib/domain/catalog";
  import { ALL_GROUPS, ALL_PERIODS } from "../lib/domain/scope";
  import type { Explorer } from "../lib/state/explorer.svelte";
  import Select from "../lib/ui/Select.svelte";

  let { explorer, onalgorithmchange }: {
    explorer: Explorer;
    onalgorithmchange?: () => void;
  } = $props();
</script>

<div class="settings scope-fields" role="group" aria-label="Experiment filters">
    <Select icon="depth" label="Algorithm" value={explorer.algorithm} options={explorer.algorithms}
      format={algorithmName} onchange={(v) => { explorer.setAlgorithm(v); onalgorithmchange?.(); }} />
    <div class="chip-field">
      <Select icon="chip" label="Chip" value={explorer.backend} options={explorer.backends}
        onchange={(v) => explorer.setBackend(v)} />
        <button type="button" id="open-calibration" class="text-action"
          onclick={event => explorer.calibration.open(null, event.currentTarget)}>
          Chip calibration history <span aria-hidden="true">→</span>
        </button>
    </div>
    <Select icon="date" label="Periods (UTC)" value={explorer.period}
      options={[ALL_PERIODS, ...explorer.periods.map(p => p.id)]}
      format={(v) => explorer.periods.find(p => p.id === v)?.label ?? "All periods"}
      onchange={(v) => explorer.setPeriod(v)} />
    <Select icon="group" label="Experiment group" value={explorer.family}
      options={[ALL_GROUPS, ...explorer.families]} format={(v) => v || "All experiments"}
      onchange={(v) => explorer.setFamily(v)} />
  </div>

<style>
  .scope-fields { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%, 165px),1fr)); margin:0 0 16px; }
  .chip-field { min-width:0; }
  .chip-field button { padding:5px 0; white-space:normal; text-align:start; font-size:.78rem; }
  .scope-fields :global(label) { min-width:0; }
  .scope-fields :global(select) { text-overflow:ellipsis; }
</style>
