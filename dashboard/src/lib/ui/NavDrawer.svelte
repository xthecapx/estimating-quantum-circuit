<script lang="ts">
  import { tick } from "svelte";
  import Icon from "./Icon.svelte";
  import type { TabGroup, TabItem } from "./Tabs.svelte";

  interface Props {
    id?: string;
    groups: TabGroup[];
    label: string;
    selected: string;
    open: boolean;
    overlay: boolean;
    onselect: (id: string) => void;
    onclose: (restoreFocus?: boolean) => void;
  }

  let { id = "nav-drawer", groups, label, selected, open, overlay, onselect, onclose }: Props = $props();

  const ordered = $derived(groups.flatMap((group) => group.tabs));
  const collapsed = $derived(!overlay && !open);
  const buttons: Record<string, HTMLButtonElement> = {};

  $effect(() => {
    if (open && overlay) {
      tick().then(() => buttons[selected]?.focus());
    }
  });

  /** WAI-ARIA vertical tabs pattern: arrows move and activate; Home/End jump; Escape closes overlay. */
  function keydown(event: KeyboardEvent, tabId: string) {
    if (event.key === "Escape" && overlay && open) {
      event.preventDefault();
      onclose(true);
      return;
    }
    const index = ordered.findIndex((tab) => tab.id === tabId);
    const next = {
      ArrowUp: (index + ordered.length - 1) % ordered.length,
      ArrowLeft: (index + ordered.length - 1) % ordered.length,
      ArrowDown: (index + 1) % ordered.length,
      ArrowRight: (index + 1) % ordered.length,
      Home: 0,
      End: ordered.length - 1,
    }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    const destination = ordered[next].id;
    onselect(destination);
    buttons[destination]?.focus();
  }

  function handleWindowKeydown(event: KeyboardEvent) {
    if (event.key === "Escape" && overlay && open) {
      event.preventDefault();
      onclose(true);
    }
  }

  function choose(tab: TabItem) {
    onselect(tab.id);
    if (overlay) onclose(false);
  }
</script>

<svelte:window onkeydown={handleWindowKeydown} />

{#if overlay}
  <div class="drawer-backdrop" class:open aria-hidden="true" onclick={() => onclose(true)}></div>
{/if}

<aside
  {id}
  class="drawer"
  class:open
  class:overlay
  class:collapsed
  aria-label="Experiment navigation"
  inert={overlay && !open}
>
  <div class="drawer-header">
    <span class="eyebrow">Experiment explorer</span>
    {#if overlay}
      <button type="button" class="drawer-close" aria-label="Close drawer" onclick={() => onclose(true)}>
        <Icon name="close" size={18} />
      </button>
    {/if}
  </div>

  <div class="drawer-nav" role="tablist" aria-orientation="vertical" aria-label={label}>
    {#each groups as group (group.label)}
      {@const groupLabelId = "tab-group-" + group.tabs[0].id}
      <div class="drawer-group" role="presentation">
        <span class="drawer-group-name" id={groupLabelId}>{group.label}</span>
        <div class="drawer-group-items" role="presentation">
          {#each group.tabs as tab (tab.id)}
            <button
              bind:this={buttons[tab.id]}
              id="tab-{tab.id}"
              type="button"
              role="tab"
              aria-controls="panel-{tab.id}"
              aria-describedby={groupLabelId}
              aria-selected={tab.id === selected}
              tabindex={tab.id === selected ? 0 : -1}
              title={collapsed ? tab.label : undefined}
              onclick={() => choose(tab)}
              onkeydown={(event) => keydown(event, tab.id)}
            >
              <span class="tab-icon" aria-hidden="true">
                <Icon name={tab.icon ?? group.icon} size={18} />
              </span>
              <span class="tab-label">{tab.label}</span>
            </button>
          {/each}
        </div>
      </div>
    {/each}
  </div>

  <div class="drawer-footer">
    <a href="https://xthecapx.github.io/qiskit-qward/">Documentation ↗</a>
  </div>
</aside>

<style>
  .drawer-backdrop {
    position: fixed;
    inset: var(--topbar-h) 0 0 0;
    z-index: 35;
    background: #152e2966;
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transition: opacity 200ms ease, visibility 0s linear 200ms;
  }
  .drawer-backdrop.open {
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    transition: opacity 200ms ease, visibility 0s linear 0s;
  }
  .drawer {
    position: sticky;
    top: var(--topbar-h);
    height: calc(100dvh - var(--topbar-h));
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    background: #fff;
    border-right: 1px solid var(--line);
    padding: 14px 12px 18px;
    min-width: 0;
    width: 100%;
  }
  .drawer.overlay {
    position: fixed;
    top: var(--topbar-h);
    left: 0;
    bottom: 0;
    height: auto;
    width: min(276px, 86vw);
    z-index: 40;
    box-shadow: 0 12px 36px #132e3733;
    transform: translateX(-100%);
    visibility: hidden;
    transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1), visibility 0s linear 220ms;
  }
  .drawer.overlay.open {
    transform: translateX(0);
    visibility: visible;
    transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1), visibility 0s linear 0s;
  }
  .drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    max-height: 44px;
    padding: 2px 10px 12px;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--line);
    overflow: hidden;
    white-space: nowrap;
    transition: max-height 200ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 150ms ease, padding 200ms ease, margin 200ms ease, border-color 150ms ease;
  }
  .drawer.collapsed .drawer-header {
    max-height: 0;
    opacity: 0;
    padding-block: 0;
    margin-bottom: 0;
    border-bottom-color: transparent;
  }
  .drawer-header .eyebrow {
    margin: 0;
  }
  .drawer-close {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    flex: none;
    border: 1px solid var(--line);
    border-radius: 7px;
    background: #fff;
    color: var(--muted);
    cursor: pointer;
    transition: background 140ms ease, color 140ms ease;
  }
  .drawer-close:hover {
    background: var(--paper);
    color: var(--ink);
  }
  .drawer-nav {
    display: flex;
    flex-direction: column;
    gap: 16px;
    flex: 1;
    transition: gap 200ms ease;
  }
  .drawer.collapsed .drawer-nav {
    gap: 8px;
  }
  .drawer-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
    border-top: 1px solid transparent;
    padding-top: 0;
    transition: border-color 180ms ease, padding-top 180ms ease;
  }
  .drawer.collapsed .drawer-group + .drawer-group {
    border-top-color: var(--line);
    padding-top: 8px;
  }
  .drawer-group-name {
    display: flex;
    align-items: center;
    max-height: 26px;
    padding: 4px 10px;
    color: var(--muted);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    transition: max-height 200ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 140ms ease, padding 200ms ease;
  }
  .drawer.collapsed .drawer-group-name {
    max-height: 0;
    opacity: 0;
    padding-block: 0;
  }
  .drawer-group-items {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .drawer-group-items button {
    display: flex;
    align-items: center;
    width: 100%;
    text-align: left;
    white-space: nowrap;
    padding: 0;
    min-height: 40px;
    border: 0;
    border-radius: 9px;
    background: transparent;
    color: var(--ink);
    font: inherit;
    font-size: 0.88rem;
    font-weight: 550;
    cursor: pointer;
    overflow: hidden;
    transition: background 150ms ease, color 150ms ease, transform 120ms ease;
  }
  .drawer-group-items button:hover {
    background: #edf4ef;
  }
  .drawer-group-items button:active {
    transform: scale(0.985);
  }
  .drawer-group-items button[aria-selected="true"] {
    background: var(--ink);
    color: #fff;
  }
  .tab-icon {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    flex: none;
    color: var(--teal);
    transition: color 150ms ease, transform 160ms ease;
  }
  .drawer-group-items button:hover .tab-icon {
    transform: scale(1.06);
  }
  .drawer-group-items button[aria-selected="true"] .tab-icon {
    color: #c5df86;
  }
  .tab-label {
    padding-right: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    opacity: 1;
    transform: translateX(0);
    transition: opacity 150ms ease, transform 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  .drawer.collapsed .tab-label {
    opacity: 0;
    transform: translateX(-6px);
    pointer-events: none;
  }
  .drawer.overlay .drawer-group-items button {
    min-height: 44px;
  }
  .drawer.overlay .tab-icon {
    height: 44px;
  }
  .drawer-footer {
    display: none;
    margin-top: 16px;
    padding: 12px 10px 0;
    border-top: 1px solid var(--line);
    font-size: 0.84rem;
    white-space: nowrap;
  }
  .drawer-footer a {
    color: var(--teal);
    font-weight: 600;
    text-decoration: none;
  }
  .drawer-footer a:hover {
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  @media (max-width: 640px) {
    .drawer-footer {
      display: block;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .drawer-backdrop,
    .drawer,
    .drawer-header,
    .drawer-close,
    .drawer-nav,
    .drawer-group,
    .drawer-group-name,
    .drawer-group-items button,
    .tab-icon,
    .tab-label {
      transition-duration: 0.01ms !important;
    }
  }
</style>
