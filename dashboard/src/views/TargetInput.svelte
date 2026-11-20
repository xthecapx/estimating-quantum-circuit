<script lang="ts">
  import { questions } from "../lib/domain/catalog";
  import { lowerIsBetter } from "../lib/domain/format";
  import type { Explorer } from "../lib/state/explorer.svelte";

  let { explorer }: { explorer: Explorer } = $props();
  const percent = $derived(explorer.question === "success");
</script>

<div class="field">
  <label>{lowerIsBetter(explorer.question) ? "Maximum" : "Minimum"} {questions[explorer.question].label.toLowerCase()}{percent ? " (%)" : ""}
    <input type="number" min="0" max={explorer.targetScale} step={percent ? 0.1 : 0.01}
      inputmode="decimal" placeholder="No target" aria-invalid={explorer.targetInvalid}
      aria-describedby="target-help" bind:value={explorer.displayTarget} />
  </label>
  <small id="target-help" class:invalid={explorer.targetInvalid}>
    {explorer.targetInvalid ? `Enter a value from 0 to ${explorer.targetScale}.` : "Optional · clear to hide the line"}
  </small>
</div>

<style>
  .field { display:grid; gap:3px; }
  label { display:flex; flex-direction:row; flex-wrap:wrap; align-items:center; gap:6px; color:var(--muted); }
  input { width:6rem; padding:7px; font:inherit; color:var(--ink); border:1px solid #abbdb3; border-radius:6px; }
  small { color:var(--muted); text-align:end; }
  small.invalid { color:#a31532; }
</style>
