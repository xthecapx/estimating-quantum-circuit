<script lang="ts">
  import { questions } from "../lib/domain/catalog";
  import { lowerIsBetter } from "../lib/domain/format";
  import type { Explorer } from "../lib/state/explorer.svelte";

  let { explorer }: { explorer: Explorer } = $props();
  const percent = $derived(explorer.question === "success");
</script>

<div class="controls">
  <label>{lowerIsBetter(explorer.question) ? "Maximum" : "Minimum"} {questions[explorer.question].label.toLowerCase()}{percent ? " (%)" : ""}
    <input type="number" min="0" max={explorer.targetScale} step={percent ? 0.1 : 0.01}
      inputmode="decimal" placeholder="—" aria-invalid={explorer.targetInvalid}
      aria-describedby={explorer.targetInvalid ? "target-help" : undefined} bind:value={explorer.displayTarget} />
  </label>
  {#if explorer.targetInvalid}
    <small id="target-help">Enter a value from 0 to {explorer.targetScale}.</small>
  {/if}
  <button class="mode" type="button" role="switch" aria-label="Show run details"
    aria-checked={explorer.mode === "details"} onclick={() => explorer.mode = explorer.mode === "details" ? "overview" : "details"}>
    <span class="track" aria-hidden="true"></span>{explorer.mode === "details" ? "Run details" : "Overview"}
  </button>
</div>

<style>
  .controls { display:grid; justify-items:start; gap:4px; max-width:100%; }
  .mode { min-width:8rem; display:inline-flex; align-items:center; gap:6px; min-height:32px; background:none; border:0; padding:3px; color:var(--ink); font-size:.83rem; }
  .track { display:inline-flex; align-items:center; width:30px; height:18px; border-radius:12px; background:#61746e; padding:3px; box-sizing:border-box; }
  .track::after { content:""; width:12px; height:12px; border-radius:50%; background:white; }
  .mode[aria-checked="true"] .track { background:var(--teal); justify-content:flex-end; }
  label { display:flex; flex-direction:row; flex-wrap:wrap; align-items:center; gap:6px; color:var(--muted); }
  input { width:4.6rem; padding:7px; font:inherit; color:var(--ink); border:1px solid #abbdb3; border-radius:6px; }
  small { color:#a31532; }
</style>
