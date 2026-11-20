<script lang="ts">
  import type { Snippet } from "svelte";
  import { on } from "svelte/events";
  import { format } from "../lib/domain/format";
  import type { Explorer } from "../lib/state/explorer.svelte";

  let { explorer, grid, children }: {
    explorer: Explorer;
    grid: { top: number; right: number; bottom: number; left: number };
    children: Snippet;
  } = $props();
  const value = $derived(explorer.threshold);
  let slider: HTMLDivElement | undefined = $state();
  let nearLine = $state(false);

  function adjust(v: number) {
    explorer.targetValue = Math.round(Math.max(0, Math.min(1, v)) * 100) / 100;
  }

  function keydown(event: KeyboardEvent) {
    if (value === null) return;
    const step = event.shiftKey ? 0.1 : 0.01;
    const keys: Record<string, number> = {
      ArrowUp: value + step, ArrowRight: value + step, ArrowDown: value - step, ArrowLeft: value - step,
      Home: 0, End: 1,
    };
    if (Object.hasOwn(keys, event.key)) {
      event.preventDefault();
      adjust(keys[event.key]);
    }
  }

  // Listen on the chart so ordinary hovers and clicks still reach points on the line.
  function track(stage: HTMLElement) {
    let drag: { id: number; y: number; value: number; height: number } | undefined;
    let moved = false;
    function hit(event: PointerEvent) {
      const rect = slider?.getBoundingClientRect();
      if (slider && event.target instanceof Node && slider.contains(event.target)) return true;
      return !!rect && event.clientX >= rect.left && event.clientX <= rect.right &&
        event.clientY >= rect.top && event.clientY <= rect.bottom;
    }
    const cleanup = [
      on(stage, "pointerdown", event => {
        if (!event.isPrimary || event.button !== 0) return;
        moved = false;
        if (!hit(event) || value === null) return;
        if (event.target instanceof Node && slider?.contains(event.target)) stage.setPointerCapture(event.pointerId);
        drag = { id: event.pointerId, y: event.clientY, value, height: stage.clientHeight - grid.top - grid.bottom };
      }, { capture: true }),
      on(stage, "pointermove", event => {
        nearLine = hit(event);
        if (!drag || drag.id !== event.pointerId || !drag.height) return;
        const delta = drag.y - event.clientY;
        if (!moved && Math.abs(delta) < 3) return;
        if (!moved) stage.setPointerCapture(event.pointerId);
        moved = true;
        adjust(drag.value + delta / drag.height);
      }, { capture: true }),
      on(stage, "pointerleave", () => { nearLine = false; if (!moved) drag = undefined; }),
      on(stage, "pointerup", () => { drag = undefined; }, { capture: true }),
      on(stage, "pointercancel", () => { drag = undefined; moved = false; }),
      on(stage, "click", event => {
        if (moved) { event.stopPropagation(); moved = false; }
      }, { capture: true }),
    ];
    return { destroy() { cleanup.forEach(remove => remove()); } };
  }
</script>

<div class="stage" class:nearLine use:track>
  {@render children()}
  {#if value !== null}
    <div class="overlay" style:inset={`${grid.top}px ${grid.right}px ${grid.bottom}px ${grid.left}px`}>
      <div bind:this={slider} class="target" style:top={`${100 * (1 - value)}%`}
        role="slider" tabindex="0" aria-label="Plot target" aria-orientation="vertical"
        aria-valuemin={0} aria-valuemax={explorer.targetScale} aria-valuenow={explorer.displayTarget}
        aria-valuetext={format(explorer.question, value)} onkeydown={keydown}>
        <span aria-hidden="true" title="Drag up or down to adjust the target">↕</span>
      </div>
    </div>
  {/if}
</div>

<style>
  .stage { position:relative; }
  .stage.nearLine :global(svg) { cursor:ns-resize !important; }
  .overlay { position:absolute; pointer-events:none; }
  .target { position:absolute; width:100%; height:24px; transform:translateY(-50%); }
  .target:focus-visible { outline:2px solid #68449b; }
  .target span { position:absolute; right:-12px; width:24px; height:24px; display:grid; place-items:center;
    background:#f7f1ff; border:1px solid #68449b; border-radius:5px; color:#533583; font-weight:700;
    pointer-events:auto; cursor:ns-resize; touch-action:none; user-select:none; }
</style>
