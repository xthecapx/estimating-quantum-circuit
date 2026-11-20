<script lang="ts" module>
  import type { IconName } from "./Icon.svelte";

  export interface TabItem {
    id: string;
    label: string;
  }
  export interface TabGroup {
    label: string;
    icon: IconName;
    tabs: TabItem[];
  }
</script>

<script lang="ts">
  import type { Snippet } from "svelte";

  import Icon from "./Icon.svelte";

  interface Props {
    tabs?: TabItem[];
    groups?: TabGroup[];
    label: string;
    selected: string;
    onselect: (id: string) => void;
    panel: Snippet<[string]>;
  }

  let { tabs = [], groups, label, selected, onselect, panel }: Props = $props();
  const ordered = $derived(groups ? groups.flatMap(group => group.tabs) : tabs);
  const buttons: Record<string, HTMLButtonElement> = {};

  /** WAI-ARIA tabs pattern: arrows move and activate; Home/End jump. */
  function keydown(event: KeyboardEvent, id: string) {
    const index = ordered.findIndex(tab => tab.id === id);
    const next = {
      ArrowLeft: (index + ordered.length - 1) % ordered.length,
      ArrowRight: (index + 1) % ordered.length,
      Home: 0,
      End: ordered.length - 1,
    }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    const destination = ordered[next].id;
    onselect(destination);
    buttons[destination].focus();
  }
</script>

{#snippet tabButton(tab: TabItem, groupLabelId?: string)}
  <button
    bind:this={buttons[tab.id]}
    id="tab-{tab.id}" type="button" role="tab"
    aria-controls="panel-{tab.id}" aria-describedby={groupLabelId}
    aria-selected={tab.id === selected} tabindex={tab.id === selected ? 0 : -1}
    onclick={() => onselect(tab.id)} onkeydown={event => keydown(event, tab.id)}
  >{tab.label}</button>
{/snippet}

<div class={groups ? "section-tabs" : "finding-tabs"} role="tablist" aria-label={label}>
  {#if groups}
    {#each groups as group (group.label)}
      {@const groupLabelId = "tab-group-" + group.tabs[0].id}
      <div class="section-group" role="presentation">
        <span class="group-name" id={groupLabelId}><Icon name={group.icon} size={16} />{group.label}</span>
        <div class="group-tabs" role="presentation">
          {#each group.tabs as tab (tab.id)}{@render tabButton(tab, groupLabelId)}{/each}
        </div>
      </div>
    {/each}
  {:else}
    {#each ordered as tab (tab.id)}{@render tabButton(tab)}{/each}
  {/if}
</div>
{#each ordered as tab (tab.id)}
  <div
    id="panel-{tab.id}"
    role="tabpanel"
    aria-labelledby="tab-{tab.id}"
    tabindex="0"
    hidden={tab.id !== selected}
  >
    {#if tab.id === selected}{@render panel(tab.id)}{/if}
  </div>
{/each}
