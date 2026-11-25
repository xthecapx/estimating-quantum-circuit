<script lang="ts">
  import { onMount } from "svelte";
  import { ECHARTS_VERSION } from "./lib/charts/echarts";
  import { unique } from "./lib/domain/format";
  import { createDashboard, sectionGroups } from "./lib/state/dashboard";
  import CalibrationView from "./views/calibration/CalibrationView.svelte";
  import JobView from "./views/job/JobView.svelte";
  import ExperimentFilters from "./views/ExperimentFilters.svelte";
  import RangeView from "./views/range/RangeView.svelte";

  import Tabs from "./lib/ui/Tabs.svelte";
  import CompareDecay from "./views/decay/CompareDecay.svelte";
  import EstimationView from "./views/estimation/EstimationView.svelte";
  import ProspectiveView from "./views/prospective/ProspectiveView.svelte";
  import CostView from "./views/cost/CostView.svelte";
  import FindingsView from "./views/findings/FindingsView.svelte";

  const dashboard = createDashboard();
  onMount(dashboard.mount);
  $effect(() => dashboard.saveRoute($dashboard));

  const section = $derived($dashboard.section);
  const explorer = $derived($dashboard.explorer);
  const index = $derived($dashboard.index);
  const view = $derived(explorer?.view ?? "range");
</script>

<nav>
  <div class="wrap nav-inner">
    <strong><span class="mark" aria-hidden="true">∿</span> QWARD</strong><span>Hardware experiments</span><a
      href="https://xthecapx.github.io/qiskit-qward/">Documentation ↗</a
    >
  </div>
</nav>
<main class="wrap">
  <header>
    <p class="eyebrow">Experiment explorer</p>
    <h1>QPU Benchmark</h1>
  </header>
  {#if $dashboard.error}
    <div id="error" role="alert">{$dashboard.error}</div>
  {/if}
  {#if explorer}
    <Tabs groups={sectionGroups} label="Experiment sections" selected={section} onselect={dashboard.selectSection}>
    {#snippet panel(id)}
    {#if id === "cost"}
      <p class="intro">Predict the billed QPU time, in IBM resource units, of a job before submitting it. One model for every chip.</p>
    {:else if id === "validation"}
      <p class="intro">The pre-registered test: predictions were committed before the jobs ran on three IBM chips, including one the models never saw.</p>
    {:else if id === "footprint"}
      <p class="intro">Which circuit metrics earned a place in the footprint? Explore the selection experiment for each chip and prediction target.</p>
    {:else if id === "estimation"}
      <p class="intro">How the models were built and selected on the training data: regressors, circuit footprints, analytical baselines and the H2–H4 analyses. For the conclusions, see Findings.</p>
    {/if}
    {#if id === "findings"}
      <FindingsView comparison={index?.comparisonReports ?? {}} estimation={index?.estimationReports ?? {}} onnavigate={dashboard.selectSection} />
    {:else if id === "decay" && explorer}
      <CompareDecay {explorer} reports={index?.decayReports ?? {}} choices={$dashboard.decay} onchange={decay => dashboard.setChoices({ decay })} />
    {:else if id === "cost"}
      <CostView reports={index?.costReports ?? {}} choices={$dashboard.cost} onchange={cost => dashboard.setChoices({ cost })} />
    {:else if id === "validation"}
      <ProspectiveView reports={index?.prospectiveReports ?? {}} choices={$dashboard.prospective} onchange={prospective => dashboard.setChoices({ prospective })} />
    {:else if (id === "estimation" || id === "footprint") && explorer}
      <EstimationView footprintOnly={id === "footprint"} {explorer} reports={index?.estimationReports ?? {}} choices={$dashboard.estimation} onchange={estimation => dashboard.setChoices({ estimation })} />
    {:else if explorer}
    <section class="surface" aria-label="Experiment explorer">
      {#if view !== "range"}
        <div class="explorer-path" id="explorer-path" aria-label="Explorer location">
          <button
            type="button"
            id="range-return"
            onclick={() => explorer!.returnToRange()}
            >Operating range</button
          >
          {#if view === "job"}
            <span><span aria-hidden="true">{" / "}</span><span aria-current="page">Job histogram</span></span>
          {:else}
            {#if explorer.calibration.origin === "job"}
              <span
                ><span aria-hidden="true">{" / "}</span><button
                  type="button"
                  id="histogram-return"
                  onclick={() => explorer!.calibration.close()}>Job histogram</button
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
        <ExperimentFilters {explorer} onalgorithmchange={() => { if (explorer.mode === "overview") explorer.targetValue = 0.5; }} />
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
    {/snippet}
    </Tabs>
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
</main>
