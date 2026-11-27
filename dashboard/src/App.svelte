<script lang="ts">
  import { onMount } from "svelte";
  import { ECHARTS_VERSION } from "./lib/charts/echarts";
  import { unique } from "./lib/domain/format";
  import { createDashboard, sectionGroups } from "./lib/state/dashboard";
  import NavDrawer from "./lib/ui/NavDrawer.svelte";
  import CalibrationView from "./views/calibration/CalibrationView.svelte";
  import JobView from "./views/job/JobView.svelte";
  import ExperimentFilters from "./views/ExperimentFilters.svelte";
  import RangeView from "./views/range/RangeView.svelte";
  import CompareDecay from "./views/decay/CompareDecay.svelte";
  import EstimationView from "./views/estimation/EstimationView.svelte";
  import ProspectiveView from "./views/prospective/ProspectiveView.svelte";
  import CostView from "./views/cost/CostView.svelte";
  import FindingsView from "./views/findings/FindingsView.svelte";

  const DESKTOP_MEDIA = "(min-width: 960px)";
  const dashboard = createDashboard();

  let desktop = $state(
    typeof window !== "undefined"
      ? window.matchMedia(DESKTOP_MEDIA).matches
      : true,
  );
  let drawerOpen = $state(
    typeof window !== "undefined"
      ? window.matchMedia(DESKTOP_MEDIA).matches
      : true,
  );
  let menuButton = $state<HTMLButtonElement>();

  onMount(() => {
    const stopDashboard = dashboard.mount();
    const query = window.matchMedia(DESKTOP_MEDIA);
    desktop = query.matches;
    drawerOpen = query.matches;
    const onMediaChange = (event: MediaQueryListEvent) => {
      desktop = event.matches;
      drawerOpen = event.matches;
    };
    query.addEventListener("change", onMediaChange);
    return () => {
      query.removeEventListener("change", onMediaChange);
      stopDashboard();
    };
  });

  $effect(() => dashboard.saveRoute($dashboard));

  const section = $derived($dashboard.section);
  const explorer = $derived($dashboard.explorer);
  const index = $derived($dashboard.index);
  const view = $derived(explorer?.view ?? "range");

  function toggleDrawer() {
    drawerOpen = !drawerOpen;
  }

  function closeDrawer(restoreFocus = false) {
    drawerOpen = false;
    if (restoreFocus) menuButton?.focus();
  }

  const menuLabel = $derived(
    desktop
      ? drawerOpen
        ? "Collapse navigation menu"
        : "Expand navigation menu"
      : drawerOpen
        ? "Close navigation menu"
        : "Open navigation menu",
  );
</script>

<header class="topbar">
  <button
    bind:this={menuButton}
    type="button"
    class="menu-button"
    class:expanded={drawerOpen}
    aria-expanded={drawerOpen}
    aria-controls="nav-drawer"
    aria-label={menuLabel}
    onclick={toggleDrawer}
  >
    <svg
      class="burger-icon"
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
    >
      <line class="bar-top" x1="4" y1="6" x2="20" y2="6" />
      <line class="bar-mid" x1="4" y1="12" x2="20" y2="12" />
      <line class="bar-bot" x1="4" y1="18" x2="20" y2="18" />
    </svg>
  </button>
  <div class="topbar-brand">
    <span class="brand-name"
      ><span class="mark" aria-hidden="true">∿</span>
      <strong>QWARD</strong></span
    >
    <span class="topbar-sep" aria-hidden="true">/</span>
    <h1 class="app-title">QPU Benchmark</h1>
  </div>
  <a class="topbar-link" href="https://xthecapx.github.io/qiskit-qward/"
    >Documentation ↗</a
  >
</header>

<div class="app-shell" class:drawer-collapsed={desktop && !drawerOpen}>
  <NavDrawer
    groups={sectionGroups}
    label="Experiment sections"
    selected={section}
    open={drawerOpen}
    overlay={!desktop}
    onselect={dashboard.selectSection}
    onclose={closeDrawer}
  />

  <main class="content">
    <div class="content-wrap">
      {#if $dashboard.error}
        <div id="error" role="alert">{$dashboard.error}</div>
      {/if}
      {#if explorer}
        <div
          id="panel-{section}"
          role="tabpanel"
          aria-labelledby="tab-{section}"
          tabindex="0"
          class="section-panel"
        >
          {#if section === "cost"}
            <p class="intro">
              Predict the billed QPU time, in IBM resource units, of a job
              before submitting it. One model for every chip.
            </p>
          {:else if section === "validation"}
            <p class="intro">
              The pre-registered test: predictions were committed before the
              jobs ran on three IBM chips, including one the models never saw.
            </p>
          {:else if section === "footprint"}
            <p class="intro">
              Which circuit metrics earned a place in the footprint? Explore the
              selection experiment for each chip and prediction target.
            </p>
          {:else if section === "estimation"}
            <p class="intro">
              How the models were built and selected on the training data:
              regressors, circuit footprints, analytical baselines and the H2–H4
              analyses. For the conclusions, see Findings.
            </p>
          {/if}

          {#if section === "findings"}
            <FindingsView
              comparison={index?.comparisonReports ?? {}}
              estimation={index?.findingsEstimationReports ?? index?.estimationReports ?? {}}
              onnavigate={dashboard.selectSection}
            />
          {:else if section === "decay"}
            <CompareDecay
              {explorer}
              reports={index?.decayReports ?? {}}
              choices={$dashboard.decay}
              onchange={(decay) => dashboard.setChoices({ decay })}
            />
          {:else if section === "cost"}
            <CostView
              reports={index?.costReports ?? {}}
              choices={$dashboard.cost}
              onchange={(cost) => dashboard.setChoices({ cost })}
            />
          {:else if section === "validation"}
            <ProspectiveView
              reports={index?.prospectiveReports ?? {}}
              choices={$dashboard.prospective}
              onchange={(prospective) => dashboard.setChoices({ prospective })}
            />
          {:else if section === "estimation" || section === "footprint"}
            <EstimationView
              footprintOnly={section === "footprint"}
              {explorer}
              reports={index?.estimationReports ?? {}}
              choices={$dashboard.estimation}
              onchange={(estimation) => dashboard.setChoices({ estimation })}
            />
          {:else}
            <section class="surface" aria-label="Experiment explorer">
              {#if view !== "range"}
                <div
                  class="explorer-path"
                  id="explorer-path"
                  aria-label="Explorer location"
                >
                  <button
                    type="button"
                    id="range-return"
                    onclick={() => explorer!.returnToRange()}
                    >Operating range</button
                  >
                  {#if view === "job"}
                    <span
                      ><span aria-hidden="true">{" / "}</span><span
                        aria-current="page">Job histogram</span
                      ></span
                    >
                  {:else}
                    {#if explorer.calibration.origin === "job"}
                      <span
                        ><span aria-hidden="true">{" / "}</span><button
                          type="button"
                          id="histogram-return"
                          onclick={() => explorer!.calibration.close()}
                          >Job histogram</button
                        ></span
                      >
                    {/if}
                    <span aria-current="page">{" / Calibration"}</span>
                  {/if}
                </div>
              {/if}
              <!-- Range and job views stay mounted while hidden so returning restores focus targets,
                   open disclosures and scroll position exactly. -->
              <div hidden={view !== "range"}>
                <ExperimentFilters
                  {explorer}
                  onalgorithmchange={() => {
                    if (explorer.mode === "overview")
                      explorer.targetValue = 0.5;
                  }}
                />
                <RangeView {explorer} />
              </div>
              {#if explorer.selectedJob}
                <div hidden={view !== "job"}><JobView {explorer} /></div>
              {/if}
              {#if view === "calibration"}
                <CalibrationView {explorer} />
              {/if}
            </section>
          {/if}
        </div>
      {:else if !$dashboard.error}
        <p role="status" class="note">Reading the exported observations…</p>
      {/if}
      <footer>
        <span id="source"
          >{explorer
            ? `Exported observations · ${explorer.jobsAll.length} jobs · ${unique(explorer.jobsAll.map((j) => j.algorithm)).length} algorithms · ECharts ${ECHARTS_VERSION}`
            : "Reading the exported snapshot…"}</span
        >
      </footer>
    </div>
  </main>
</div>
