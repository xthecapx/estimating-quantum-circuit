<script lang="ts">
  import type { DecayChoices } from "../../lib/state/dashboard";
  import { decayData } from "../../lib/data/load";
  import { tick } from "svelte";
  import { derived } from "svelte/store";
  import EChart from "../../lib/charts/EChart.svelte";
  import type { EChartsType } from "../../lib/charts/echarts";
  import Icon from "../../lib/ui/Icon.svelte";
  import Select from "../../lib/ui/Select.svelte";
  import { algorithmName } from "../../lib/domain/catalog";
  import { periods as chipPeriods } from "../../lib/domain/scope";
  import type { Explorer } from "../../lib/state/explorer.svelte";
  import {
    CHIP_COLORS,
    bounds,
    chart,
    chipName,
    collectWindows,
    combinedPairMatrix,
    construction,
    crossChipGapChart,
    declineLabels,
    declineStatus,
    extraLoss,
    fixed,
    key,
    matchingWindows,
    median,
    medianLoss,
    pairConclusion,
    partnerResourceMap,
    relationshipRanking,
    resourceEvidence,
    resourceShort,
    resources,
    short,
    signed,
    targets,
  } from "./model";

  let { explorer, reports, choices, onchange }: {
    explorer: Explorer;
    reports: Record<string, string>;
    choices: DecayChoices;
    onchange: (v: DecayChoices) => void;
  } = $props();

  const validationChip = "ibm_marrakesh";
  const reportChips = $derived(Object.keys(reports).sort());
  const chips = $derived(reportChips.filter(chip => chip !== validationChip));
  const reportStore = $derived(derived(reportChips.map(chip => decayData.watch(reports[chip], chip)), results => results));
  const snapshots = $derived($reportStore.flatMap(result => result.data ? [result.data] : []));
  const chipSnapshots = $derived(snapshots.filter(report => report.backend !== validationChip));
  const hasValidation = $derived(snapshots.some(report => report.backend === validationChip));
  const loading = $derived($reportStore.some(result => !result.data && !result.error));

  const outcomeOptions = $derived.by(() => {
    const ids = new Set(chipSnapshots.flatMap(report =>
      Object.values(report.panels).flatMap(panel => Object.keys(panel))));
    return [...ids].map(id => {
      const ranking = relationshipRanking(chipSnapshots, id);
      // Each matched pair appears once in each algorithm's partner list.
      const pairs = ranking.reduce((sum, algorithm) => sum + algorithm.count, 0) / 2;
      return { id, pairs, ranking };
    }).sort((a, b) => b.pairs - a.pairs || (targets[a.id] ?? a.id).localeCompare(targets[b.id] ?? b.id));
  });
  const selectedOutcome = $derived(outcomeOptions.find(item => item.id === choices.outcome)
    ?? outcomeOptions.find(item => item.id === "success") ?? outcomeOptions[0]);
  const outcome = $derived(selectedOutcome?.id ?? "");
  const ranking = $derived(selectedOutcome?.ranking ?? []);
  const requested = $derived(choices.pair.split("/"));
  const selected = $derived(ranking.find(a => a.id === requested[0]) ?? ranking[0]);
  const algorithm = $derived(selected?.id ?? "");
  const partners = $derived(selected?.partners ?? []);
  const partner = $derived(partners.find(p => p.id === requested[1]) ?? partners[0]);
  const structure = $derived(partner && construction(partner.cell));
  const rows = $derived(resourceEvidence(snapshots, algorithm, partner?.id ?? "", outcome));

  let showUnavailable = $state(false);
  const visibleRows = $derived(showUnavailable ? rows : rows.filter(row => row.eligible > 0));
  const hasUnavailable = $derived(rows.some(row => !row.eligible || chips.some(chip => !row.chips.get(chip)?.eligible)));
  const tolerance = $derived(chipSnapshots[0]?.tolerance ?? snapshots[0]?.tolerance ?? 5);
  const unit = $derived(outcome === "success" ? "pp" : "points");
  const ylabel = $derived(outcome === "success" ? "Success rate (%)" : (targets[outcome] + " × 100"));
  const scoreUnits = $derived(outcome === "success" ? "percentage points" : "points on the 0–100 scale");

  const conclusion = $derived(partner ? pairConclusion(rows, algorithm, partner.id, outcome, tolerance) : null);
  const shorRawWarning = $derived(outcome === "success" && (algorithm === "SHOR" || partner?.id === "SHOR"));
  const partnerMap = $derived(algorithm && partners.length ? partnerResourceMap(snapshots, algorithm, partners, outcome) : { metrics: [], rows: [] });
  const matchingPartnerCount = $derived(partnerMap.rows.filter(r => r.repeatedCount > 0).length);

  const comparableRows = $derived(rows.filter(r => r.eligible > 0));
  const bestOrderedRows = $derived([...comparableRows].sort((a, b) => (a.medianGap ?? Infinity) - (b.medianGap ?? Infinity)));

  // Default to the best-correlating comparable resource on "all".
  const metric = $derived(choices.resource || bestOrderedRows[0]?.metric || "");
  const scope = $derived(
    choices.scope === "all"
      ? "all"
      : choices.scope && chips.includes(choices.scope)
        ? choices.scope
        : choices.resource && !choices.scope
          ? (chips.includes(explorer.backend) ? explorer.backend : "all")
          : "all",
  );
  const isAll = $derived(scope === "all");

  const scopedRows = $derived(
    isAll ? comparableRows : comparableRows.filter(r => (r.chips.get(scope)?.eligible ?? 0) > 0),
  );
  const chartBackends = $derived(
    (isAll ? snapshots.map(s => s.backend) : [scope]).filter(b =>
      scopedRows.some(r => (r.chips.get(b)?.eligible ?? 0) > 0),
    ),
  );
  const gapPlotOption = $derived(
    scopedRows.length && chartBackends.length
      ? crossChipGapChart(scopedRows, chartBackends, tolerance, unit, metric)
      : null,
  );

  const activeRow = $derived(rows.find(row => row.metric === metric));
  const data = $derived(isAll ? chipSnapshots[0] : chipSnapshots.find(report => report.backend === scope));
  const evidence = $derived(isAll ? undefined : activeRow?.chips.get(scope));
  const cell = $derived(evidence?.cell);

  const windowEntries = $derived(
    metric && partner ? collectWindows(snapshots, metric, algorithm, partner.id, outcome, scope) : [],
  );
  const directional = $derived(choices.matrix === "direction");
  const cells = $derived(!isAll && data ? (data.panels[metric]?.[outcome] ?? []) : []);
  const combinedMatrix = $derived(isAll && metric ? combinedPairMatrix(snapshots, metric, outcome) : new Map());
  const signedGaps = $derived(new Map(cells.map(c => [key(c), medianLoss(c)])));
  const matches = $derived(new Set(data && !isAll ? cells.filter(c => matchingWindows(c, data.tolerance) >= data.minPeriods).map(key) : []));

  const activeGap = $derived.by(() => {
    if (!windowEntries.length) return null;
    if (directional) return median(windowEntries.map(w => extraLoss(w.period, w.reversed)));
    if (!isAll && cell?.gap != null) return cell.gap;
    return median(windowEntries.map(w => w.period.gap));
  });
  const activeCi = $derived(
    !isAll && cell?.ciLow != null && cell?.ciHigh != null
      ? [cell.ciLow, cell.ciHigh] as const
      : windowEntries.length === 1 && windowEntries[0].period.ciLow != null && windowEntries[0].period.ciHigh != null
        ? [windowEntries[0].period.ciLow, windowEntries[0].period.ciHigh] as const
        : null,
  );
  const activePWithin = $derived(!isAll ? (cell?.pWithin ?? null) : null);
  const activeMatched = $derived(windowEntries.filter(w => declineStatus(w.period, w.tolerance) === "similar").length);
  const activeChips = $derived([...new Set(windowEntries.map(w => w.backend))]);
  const gapScale = $derived(Math.max(1, 2 * tolerance, ...windowEntries.flatMap(w => [w.period.gap, w.period.ciHigh ?? 0])));
  const minPeriods = $derived(data?.minPeriods ?? 2);
  const axes = $derived(windowEntries.length ? bounds(windowEntries.map(w => w.period)) : null);
  const ids = $derived(isAll ? [...new Set(snapshots.flatMap(report => report.algorithms))].sort() : data?.algorithms ?? []);
  const rowAlg = $derived(algorithm);
  const colAlg = $derived(partner?.id ?? "");

  const baseRateSummary = $derived(
    chipSnapshots
      .map(report => {
        const rates = report.baseRates ?? [];
        const fam = rates.find(r => r.pairClass === "family");
        const ctrl = rates.find(r => r.pairClass === "random-volumetric control");
        const unrel = rates.find(r => r.pairClass === "unrelated");
        return fam && unrel ? { backend: report.backend, fam, ctrl, unrel } : null;
      })
      .filter((x): x is NonNullable<typeof x> => x !== null),
  );

  const example = $derived.by(() => {
    for (const row of rows) {
      for (const report of chipSnapshots) {
        const result = row.chips.get(report.backend);
        if (!result?.eligible) continue;
        const periods = Object.values(result.cell.periods);
        const period = periods.find(p => declineStatus(p, report.tolerance) === "similar") ?? periods[0];
        return { report, result, period, metric: row.metric };
      }
    }
  });

  function fittedChange(slope: number, span: number) {
    const change = 100 * slope * span;
    if (Math.abs(change) < 0.005) return "changed by less than 0.01";
    return (change < 0 ? "fell by " : "rose by ") + fixed(Math.abs(change));
  }

  let workspaceCard = $state<HTMLElement>();
  // Deep links with an explicit resource open directly in Window details; bare visits start on All metrics.
  let detailView = $state(false);
  let initializedView = false;
  $effect(() => {
    if (!initializedView && snapshots.length) {
      initializedView = true;
      detailView = Boolean(choices.resource);
    }
  });
  let showFits = $state(false);

  function change(v: Partial<DecayChoices>) {
    onchange({ ...choices, ...v });
  }
  function chooseAlgorithm(id: string) {
    detailView = false;
    change({ pair: id, resource: "", scope });
  }
  function choosePartner(id: string) {
    detailView = false;
    change({ pair: algorithm + "/" + id, resource: "", scope });
  }
  function chooseChip(nextScope: string) {
    if (nextScope !== "all") explorer.setBackend(nextScope);
    change({ scope: nextScope, pair: partner ? algorithm + "/" + partner.id : algorithm, outcome });
  }
  function chooseOutcome(nextOutcome: string) {
    detailView = false;
    change({ outcome: nextOutcome, pair: partner ? algorithm + "/" + partner.id : algorithm, resource: "", scope });
  }
  async function inspectResource(
    resource: string,
    targetScope: string,
    options: { openDetail?: boolean; scroll?: boolean } = {},
  ) {
    if (targetScope !== "all") explorer.setBackend(targetScope);
    if (options.openDetail !== undefined) detailView = options.openDetail;
    change({ resource, scope: targetScope, pair: algorithm + "/" + partner!.id, outcome });
    if (options.scroll) {
      await tick();
      workspaceCard?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }
  async function inspectPartnerResource(partnerId: string, resource: string) {
    detailView = false;
    change({ pair: algorithm + "/" + partnerId, resource, scope: "all", outcome });
    await tick();
    workspaceCard?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  async function inspectPair(rowId: string, columnId: string) {
    detailView = true;
    change({ pair: rowId + "/" + columnId });
    await tick();
    workspaceCard?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  function bindGapPlotClick(instance: EChartsType) {
    instance.on("click", (params: unknown) => {
      const event = params as { componentType?: string; value?: string; data?: { metric?: string; backend?: string } };
      if (event.data?.metric && event.data?.backend) {
        const targetScope = chips.includes(event.data.backend) ? event.data.backend : "all";
        void inspectResource(event.data.metric, targetScope, { openDetail: true });
        return;
      }
      if (event.componentType === "yAxis" && typeof event.value === "string") {
        const clean = event.value.replace(/^▸\s*/, "");
        const hit = scopedRows.find(r => (resources[r.metric] ?? r.metric) === clean);
        if (hit) void inspectResource(hit.metric, scope, { openDetail: true });
      }
    });
  }

  function directionValue(a: string, b: string): number | null {
    if (isAll) {
      const c = combinedMatrix.get(`${a}/${b}`) ?? combinedMatrix.get(`${b}/${a}`);
      if (!c || c.signedDelta == null) return null;
      return a === c.a ? c.signedDelta : -c.signedDelta;
    }
    const c = lookup(a, b);
    if (!c) return null;
    const value = signedGaps.get(key(c));
    return value == null ? null : a === c.a ? value : -value;
  }

  function pairLabel(k: string) { return k.split("/").map(algorithmName).join(" / "); }
  function lookup(a: string, b: string) { return cells.find(c => (c.a === a && c.b === b) || (c.a === b && c.b === a)); }
  const pct = (v: number | null | undefined) => (v == null ? "—" : `${Math.round(v * 100)}%`);

  // Resolve collection dates across ALL chips (including Kingston & Marrakesh when viewing All data).
  const dates = $derived(new Map(
    explorer.backends.flatMap(backend =>
      chipPeriods(explorer.jobsAll, backend).map(period => {
        const { campaign, window } = period.jobs[0];
        return [JSON.stringify([backend, campaign + " / window " + window]), period.dateLabel] as const;
      }),
    ),
  ));
  function dateLabel(backend: string, period: string) { return dates.get(JSON.stringify([backend, period])) ?? "Date unavailable"; }
</script>

<section class="surface compare" aria-label="Decay comparison">
  {#if loading}
    <p role="status">Loading chip comparisons…</p>
  {:else if !snapshots.length}
    {#if $reportStore.some(result => result.error)}
      <p role="alert">The decay reports could not be loaded. Reload to try again.</p>
    {:else}
      <p role="status">No decay reports are available for this export.</p>
    {/if}
  {:else}
    <div class="settings controls" role="group" aria-label="Decay filters">
      <Select label="Algorithm" icon="qubits" value={algorithm} options={ranking.map(a => a.id)}
        format={id => algorithmName(id) + " · " + ranking.find(a => a.id === id)!.count + " matching partners"} onchange={chooseAlgorithm} />
      <label><span class="field-name"><Icon name="compare" size={15} />Compare with</span>
        <select aria-label="Compare with" value={partner?.id} onchange={event => choosePartner(event.currentTarget.value)}>
          {#each partners as p (p.id)}
            <option value={p.id}>{algorithmName(p.id)} · {p.resources.size ? p.resources.size + " matched " + (p.resources.size === 1 ? "resource" : "resources") : p.comparable ? "No repeated match" : "Insufficient coverage"}</option>
          {/each}
        </select>
      </label>
      <Select label="Chip" icon="chip" value={scope} options={["all", ...chips]}
        format={id => id === "all" ? "All data" : chipName(id)} onchange={chooseChip} />
      <Select label="Outcome" icon="shots" value={outcome} options={outcomeOptions.map(item => item.id)}
        format={id => (targets[id] ?? id) + " · " + outcomeOptions.find(item => item.id === id)!.pairs + " matching pairs"}
        onchange={chooseOutcome} />
    </div>

    {#if structure && partner && conclusion}
      <section class="summary-band {conclusion.status}" aria-label="Pair conclusion">
        <div class="summary-columns" class:has-metric={Boolean(metric && activeRow && (isAll || (cell && data && evidence)))}>
          <div class="summary-main">
            <div class="takeaway-tags">
              <span class="verdict-badge {conclusion.status}">{conclusion.badge}</span>
              <span class="role-tag">{structure.tag}</span>
            </div>
            <h2>{algorithmName(algorithm)} and {algorithmName(partner.id)}</h2>
            <p class="takeaway-headline">{conclusion.headline}</p>
            <p class="takeaway-detail">{conclusion.detail}</p>
          </div>

          {#if metric && activeRow && (isAll || (cell && data && evidence))}
            <div class="summary-metric" role="region" aria-label="Selected metric summary">
              <p class="metric-kicker">
                <span>{detailView ? "Inspecting" : "Selected metric"}</span>
                <strong>{resources[metric] ?? metric}</strong>
                <span class="scope-tag">{isAll ? "All data" : chipName(data!.backend)}</span>
              </p>

              {#if windowEntries.length}
                <div class="stat">
                  <strong>{directional ? signed(activeGap) : fixed(activeGap)} {unit}</strong>
                  <span>
                    {directional ? `Median extra loss of ${short(colAlg)} relative to ${short(rowAlg)}` : "Median gap in fitted change"}
                    {#if activeCi && !directional} · 95% CI [{fixed(activeCi[0])}, {fixed(activeCi[1])}]{/if}
                    {#if activePWithin != null && !directional} · P(≤{tolerance}) = {pct(activePWithin)}{/if}
                  </span>
                </div>
              {/if}

              {#if !isAll && data && cell && windowEntries.length < data.minPeriods}
                <h3>Too few comparable windows</h3>
                <p class="metric-verdict">{windowEntries.length} of {data.minPeriods} required windows have at least {data.minLevels} shared levels.
                  Largest overlap: {Math.max(0, ...Object.values(cell.overlap))}.</p>
              {:else if !windowEntries.length}
                <h3>No comparable windows</h3>
                <p class="metric-verdict">No chip window has at least {data?.minLevels ?? 3} shared levels for this resource.</p>
              {:else}
                <h3>Similar decline in {activeMatched} of {windowEntries.length} eligible {windowEntries.length === 1 ? "window" : "windows"}{isAll ? ` across ${activeChips.length} ${activeChips.length === 1 ? "chip" : "chips"}` : ""}</h3>
                <p class="metric-verdict">
                  {targets[outcome]}{#if isAll && activeChips.length} · {activeChips.map(chipName).join(", ")}{/if} · cutoff ≤ {tolerance} {unit}
                </p>
              {/if}
            </div>
          {/if}
        </div>

        <div class="summary-foot">
          <details class="context-disclosure">
            <summary>About this pair &amp; cross-chip base rates</summary>
            <p class="construction-note"><strong>{structure.title}.</strong> {structure.detail}</p>
            {#if baseRateSummary.length}
              <p class="base-rate-note">
                <strong>Across all algorithm pairs:</strong>
                {#each baseRateSummary as br, i}
                  {i > 0 ? " · " : ""}{chipName(br.backend)}: family {pct(br.fam.shareRepeated)} ({br.fam.repeatedCells}/{br.fam.cells}) vs unrelated {pct(br.unrel.shareRepeated)} ({br.unrel.repeatedCells}/{br.unrel.cells}) repeated
                {/each}. Shared circuit family alone does not guarantee shared decay.
              </p>
            {/if}
          </details>
          {#if gapPlotOption && metric && activeRow}
            {#if detailView}
              <button type="button" class="text-action card-action" onclick={() => { detailView = false; }}>
                ← Pick another metric
              </button>
            {:else}
              <button type="button" class="text-action card-action" onclick={() => { detailView = true; }}>
                Inspect {windowEntries.length} {windowEntries.length === 1 ? "window" : "windows"} →
              </button>
            {/if}
          {/if}
        </div>
      </section>

      {#if shorRawWarning}
        {@const shorOutcome = outcomeOptions.some(o => o.id === "chance_corrected") ? "chance_corrected" : "normalized"}
        <div class="shor-warning" role="note">
          <span><strong>Shor raw-success caveat:</strong> Shor's chance floor falls with qubit count, so raw success can look like a match even where Shor returns noise.</span>
          <button type="button" onclick={() => chooseOutcome(shorOutcome)}>
            Switch to {targets[shorOutcome]?.toLowerCase() ?? shorOutcome}
          </button>
        </div>
      {/if}

      {#if gapPlotOption || (metric && activeRow)}
        <article bind:this={workspaceCard} class="visual-card workspace" aria-label="Decay alignment workspace">
          <div class="workspace-bar">
            <div class="view-switch" role="group" aria-label="Decay view">
              {#if gapPlotOption}
                <button type="button" aria-pressed={!detailView} onclick={() => { detailView = false; }}>
                  All metrics ({scopedRows.length})
                </button>
              {/if}
              {#if metric && activeRow}
                <button type="button" aria-pressed={detailView} onclick={() => { detailView = true; }}>
                  Window details · {resourceShort[metric] ?? resources[metric] ?? metric} ({windowEntries.length})
                </button>
              {/if}
            </div>
            {#if !detailView && gapPlotOption}
              <div class="chip-legend" aria-hidden="true">
                {#each chartBackends as b}
                  <span><i class="dot {b}" style="--c:{CHIP_COLORS[b]}"></i>{chipName(b)}</span>
                {/each}
              </div>
            {:else if detailView && gapPlotOption}
              <button type="button" class="text-action back-link" onclick={() => { detailView = false; }}>
                ← Back to all metrics
              </button>
            {/if}
          </div>

          {#if !detailView && gapPlotOption}
            <div class="workspace-head">
              <h3>Which circuit metrics align their decay best?</h3>
              <p class="note">
                Each point measures how far apart the two algorithms' fitted {targets[outcome]?.toLowerCase() ?? outcome} drops were across a metric's shared range (bars = 95% bootstrap CI).
                <strong>Closer to 0 is better</strong> — metrics inside the green ≤ {tolerance} {unit} band best correlate their decay. Sorted best to worst; click any metric or dot to inspect its windows.
              </p>
            </div>
            <EChart
              option={gapPlotOption}
              replace
              onready={bindGapPlotClick}
              label="Median decay gap by circuit resource across chips for {algorithmName(algorithm)} and {algorithmName(partner.id)}"
              style="height:{Math.max(220, scopedRows.length * 34 + 74)}px;width:100%"
            />
          {:else if metric && activeRow}
            {#if windowEntries.length && axes}
              <figure class="gap-chart">
                <figcaption>
                  <div>
                    <h3>How far apart were the fitted changes in each window?</h3>
                    <p class="note">{resources[metric] ?? metric} · {isAll ? "All data" : chipName(data!.backend)} · {algorithmName(algorithm)} and {algorithmName(partner.id)}</p>
                  </div>
                  <span class="threshold-key">Cutoff · ≤ {tolerance} {unit} (brackets = 95% bootstrap CI)</span>
                </figcaption>
                <ul>
                  {#each windowEntries as entry (`${entry.backend}:${entry.name}`)}
                    {@const p = entry.period}
                    {@const status = declineStatus(p, entry.tolerance)}
                    <li class:similar={status === "similar"}>
                      <span class="window" title={`${entry.backend} · ${entry.name}`}>
                        {#if isAll}<span class="chip-pill" style="--c:{CHIP_COLORS[entry.backend]}">{chipName(entry.backend)}</span>{/if}
                        {dateLabel(entry.backend, entry.name)}
                      </span>
                      <div class="track" aria-hidden="true">
                        <i style:width={(100 * p.gap / gapScale) + "%"}></i>
                        {#if p.ciLow != null && p.ciHigh != null}
                          <span class="ci-band" style:left={(100 * p.ciLow / gapScale) + "%"} style:width={(100 * Math.max(0, p.ciHigh - p.ciLow) / gapScale) + "%"}></span>
                        {/if}
                        <b style:left={(100 * entry.tolerance / gapScale) + "%"}></b>
                      </div>
                      <div class="gap-value">
                        <strong>{fixed(p.gap)} {unit}</strong>
                        {#if p.ciLow != null && p.ciHigh != null}<small class="ci-text">[{fixed(p.ciLow)}–{fixed(p.ciHigh)}]</small>{/if}
                      </div>
                      <span class="status">{declineLabels[status]}</span>
                    </li>
                  {/each}
                </ul>
              </figure>

              <details class="disclosure" bind:open={showFits}>
                <summary>Observed outcomes and fitted trends <span class="summary-meta">({windowEntries.length} {windowEntries.length === 1 ? "window" : "windows"})</span></summary>
                {#if showFits}
                  <div class="plot-heading">
                    <h3>Fitted trends by collection window</h3>
                    <div class="legend">
                      <span>● {algorithmName(windowEntries[0].cell.a)} · solid</span>
                      <span>◆ {algorithmName(windowEntries[0].cell.b)} · dashed</span>
                    </div>
                  </div>
                  <p class="note">{ylabel}. Each point averages the tested configurations at one shared resource level. Each line fits one algorithm in that window.</p>
                  <div class="panels">
                    {#each windowEntries as entry (`${entry.backend}:${entry.name}`)}
                      <article>
                        <h4 title={`${entry.backend} · ${entry.name}`}>
                          {#if isAll}<span class="chip-pill" style="--c:{CHIP_COLORS[entry.backend]}">{chipName(entry.backend)}</span>{/if}
                          {dateLabel(entry.backend, entry.name)}
                        </h4>
                        <p class="window-label">
                          {declineLabels[declineStatus(entry.period, entry.tolerance)]} · {fixed(entry.period.gap)} {unit} apart
                          {#if entry.period.pMatch != null} · P(match) {pct(entry.period.pMatch)}{/if}
                        </p>
                        <EChart
                          option={chart(entry.period, entry.cell, axes, resources[metric] ?? metric, ylabel)}
                          replace
                          label={pairLabel(key(entry.cell)) + " on " + chipName(entry.backend) + " " + dateLabel(entry.backend, entry.name)}
                          style="height:195px;width:100%"
                        />
                      </article>
                    {/each}
                  </div>
                {/if}
              </details>

              <details class="fit-details disclosure">
                <summary>Slopes and rank correlations by window</summary>
                <p class="note">Slopes use {unit} per resource unit. The gap measures the difference in fitted changes from the first shared level to the last, with its 95% bootstrap interval.
                  Spearman ρ ranks the observed means. A value near +1 means the two algorithms rank the levels similarly, even when one loses much more.
                  A dash marks a constant profile where ρ is undefined.</p>
                <div class="scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Collection date (UTC)</th>
                        {#if isAll}<th>Chip</th>{/if}
                        <th>Shared levels</th>
                        <th>{short(windowEntries[0].cell.a)} slope</th>
                        <th>{short(windowEntries[0].cell.b)} slope</th>
                        <th>{directional ? `Extra loss of ${short(colAlg)} vs ${short(rowAlg)}` : "Gap"} ({unit})</th>
                        <th>95% CI ({unit})</th>
                        <th>P(match)</th>
                        <th>Profile ρ</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each windowEntries as entry (`${entry.backend}:${entry.name}`)}
                        {@const v = entry.period}
                        <tr>
                          <td title={entry.name}>{dateLabel(entry.backend, entry.name)}</td>
                          {#if isAll}<td>{chipName(entry.backend)}</td>{/if}
                          <td>{v.points.length}</td>
                          <td>{fixed(100 * v.slopeA)}</td>
                          <td>{fixed(100 * v.slopeB)}</td>
                          <td>{directional ? signed(extraLoss(v, entry.reversed)) : fixed(v.gap)}</td>
                          <td>{v.ciLow != null && v.ciHigh != null ? `[${fixed(v.ciLow)}, ${fixed(v.ciHigh)}]` : "—"}</td>
                          <td>{pct(v.pMatch)}</td>
                          <td>{fixed(v.rho)}</td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </details>
            {:else}
              <p class="note">No windows have enough shared levels for {resources[metric] ?? metric} on {isAll ? "any chip" : chipName(scope)}.</p>
            {/if}

            <details class="coverage disclosure">
              <summary>Shared levels by window</summary>
              <ul>
                {#if isAll}
                  {#each [...activeRow.chips.entries()] as [backend, ev]}
                    {#each Object.entries(ev.cell.overlap) as [name, levels]}
                      <li><span>{chipName(backend)} · {name}</span> <strong>{levels}</strong></li>
                    {/each}
                  {/each}
                {:else if cell}
                  {#each Object.entries(cell.overlap) as [name, levels]}
                    <li>{name} <strong>{levels}</strong></li>
                  {/each}
                {/if}
              </ul>
            </details>
          {/if}
        </article>
      {/if}

      <section class="more-views" aria-label="Additional comparison tables">
        {#if partnerMap.metrics.length}
          <details class="disclosure">
            <summary>
              Which partners preserve decay with {algorithmName(algorithm)}?
              <span class="summary-meta">({matchingPartnerCount} of {partnerMap.rows.length} partners match on ≥1 metric)</span>
            </summary>
            <div class="visual-head">
              <p class="note">Rows are partner algorithms; columns are circuit resources. Click any cell to switch partner and inspect that metric at the top.</p>
              <div class="map-legend" aria-hidden="true">
                <span><i class="swatch cross"></i>Both chips</span>
                <span><i class="swatch repeated"></i>One chip ✓</span>
                <span><i class="swatch isolated"></i>Isolated</span>
                <span><i class="swatch different"></i>Different</span>
              </div>
            </div>
            <div class="scroll">
              <table class="partner-map" aria-label="Partner by resource preservation map">
                <thead>
                  <tr>
                    <th scope="col">Partner</th>
                    {#each partnerMap.metrics as m}
                      <th scope="col" title={resources[m] ?? m}>{resourceShort[m] ?? m}</th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each partnerMap.rows as prow (prow.partnerId)}
                    <tr class:active-partner={prow.partnerId === partner.id}>
                      <th scope="row">{short(prow.partnerId)}</th>
                      {#each prow.cells as cellItem (cellItem.metric)}
                        <td>
                          {#if cellItem.eligible > 0}
                            <button
                              type="button"
                              class="map-cell {cellItem.level}"
                              class:selected={prow.partnerId === partner.id && cellItem.metric === metric}
                              aria-label={`${algorithmName(algorithm)} and ${algorithmName(prow.partnerId)}, ${resources[cellItem.metric] ?? cellItem.metric}: ${cellItem.matched} of ${cellItem.eligible} windows matched, median gap ${fixed(cellItem.medianGap)} ${unit}`}
                              title={`${algorithmName(prow.partnerId)} · ${resources[cellItem.metric] ?? cellItem.metric}: ${cellItem.matched}/${cellItem.eligible} matched · median ${fixed(cellItem.medianGap)} ${unit}`}
                              onclick={() => inspectPartnerResource(prow.partnerId, cellItem.metric)}
                            >
                              {cellItem.repeats >= 2 ? "✓✓" : cellItem.repeats === 1 ? "✓" : `${cellItem.matched}/${cellItem.eligible}`}
                            </button>
                          {:else}
                            <span class="map-empty" aria-hidden="true">·</span>
                          {/if}
                        </td>
                      {/each}
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </details>
        {/if}

        <details class="disclosure overview-disclosure">
          <summary id="overview-title">
            How often did {targets[outcome]?.toLowerCase() ?? outcome} fall by similar amounts?
            <span class="summary-meta">({comparableRows.length} comparable {comparableRows.length === 1 ? "resource" : "resources"} · per-chip table)</span>
          </summary>
          <div class="overview">
            <div id="count-guide" class="count-key">
              <span><b class="sample match">1 of 3</b> Click any cell (including All data) to open its window details</span>
              <span><b class="sample match">✓</b> Repeated on this chip</span>
              {#if hasUnavailable}<span><b class="sample">—</b> Unavailable for comparison</span>{/if}
            </div>
            {#if showUnavailable && hasUnavailable}
              <p class="note" id="coverage-guide">“0 of 3 shared levels” means the two algorithms needed three resource values in common, but shared none in a single collection on that chip.</p>
            {/if}
            <div class="scroll">
              <table class="evidence" aria-labelledby="overview-title" aria-describedby="count-guide">
                <thead>
                  <tr>
                    <th scope="col">Circuit resource</th>
                    <th scope="col">All data</th>
                    {#each chips as chip}<th scope="col">{chip}</th>{/each}
                  </tr>
                </thead>
                <tbody>
                  {#each visibleRows as row (row.metric)}
                    {@const hasMarrakesh = (row.chips.get(validationChip)?.eligible ?? 0) > 0}
                    <tr>
                      <th scope="row">{resources[row.metric] ?? row.metric}</th>
                      <td>
                        {#if row.eligible}
                          <button
                            type="button"
                            class:match={row.matched > 0}
                            aria-label={`${resources[row.metric] ?? row.metric}, All data, ${row.matched} of ${row.eligible} comparable windows had similar declines${hasMarrakesh ? ", includes IBM Marrakesh" : ""}`}
                            aria-pressed={metric === row.metric && scope === "all"}
                            onclick={() => inspectResource(row.metric, "all", { openDetail: true, scroll: true })}
                          >
                            <strong class="total">{row.matched} of {row.eligible}</strong>
                            {#if hasMarrakesh}<small class="val-tag">+ Marrakesh</small>{/if}
                          </button>
                        {:else}
                          <small>No comparable windows</small>
                        {/if}
                      </td>
                      {#each chips as chip}
                        {@const result = row.chips.get(chip)}
                        <td>
                          {#if result && (result.eligible || showUnavailable)}
                            <button
                              type="button"
                              class:match={result.matched > 0}
                              aria-label={!result.eligible ? `${resources[row.metric] ?? row.metric}, ${chip}, ${result.coverage}` : `${resources[row.metric] ?? row.metric}, ${chip}, ${result.matched} of ${result.eligible} comparable windows had similar declines${result.matched >= result.minimum ? ", repeated on this chip" : ""}`}
                              aria-pressed={metric === row.metric && scope === chip}
                              onclick={() => inspectResource(row.metric, chip, { openDetail: true, scroll: true })}
                            >
                              {#if result.eligible}
                                <strong>{result.matched} of {result.eligible}</strong>
                                {#if result.matched >= result.minimum}<span aria-hidden="true"> ✓</span>{/if}
                              {:else}
                                <small>Unavailable<br />{result.coverage}</small>
                              {/if}
                            </button>
                          {:else if $reportStore[reportChips.indexOf(chip)]?.error}<span class="note">Load failed</span>
                          {:else if showUnavailable}<small>Pair absent from report</small>
                          {:else}<span aria-label="No comparable windows" class="note">—</span>{/if}
                        </td>
                      {/each}
                    </tr>
                  {:else}
                    <tr><td colspan={chips.length + 2}>No resources have comparable windows for this selection.</td></tr>
                  {/each}
                </tbody>
              </table>
            </div>
            {#if hasUnavailable}
              <label class="unavailable-toggle"><input type="checkbox" bind:checked={showUnavailable} /> Show unavailable comparisons</label>
            {/if}
            <details class="comparison-help">
              <summary>How to read this comparison</summary>
              <h4>{structure.title}</h4>
              <p>{structure.detail}</p>
              <p>Each collection window covers one chip. We compare fitted changes over the resource levels both algorithms tested in that window.</p>
              {#if example}
                {@const { report, result, period } = example}
                {@const span = period.points[period.points.length - 1][0] - period.points[0][0]}
                {@const status = declineStatus(period, report.tolerance)}
                <p class="worked-example"><strong>For example,</strong> on {report.backend}, as {(resources[example.metric] ?? example.metric).toLowerCase()} increased,
                  {algorithmName(result.cell.a)} {fittedChange(period.slopeA, span)} and {algorithmName(result.cell.b)} {fittedChange(period.slopeB, span)} {scoreUnits} in one window.
                  {#if status === "similar"}Both fell within {report.tolerance} points of each other, so this window counts toward the first number.
                  {:else if status === "different"}Their losses were {fixed(period.gap)} points apart, above the {report.tolerance}-point cutoff, so this window counts only toward the second number.
                  {:else}A similar decline requires both fitted outcomes to fall, so this window counts only toward the second number.{/if}</p>
              {/if}
              <p class="note">All data counts each comparable chip window once.{#if hasValidation} It includes eligible Marrakesh validation windows — click any All data cell to inspect the individual chip windows.{:else if explorer.backends.includes(validationChip)} Marrakesh validation data is unavailable for this export.{/if}</p>
              {#each chipSnapshots as report}
                <p>{report.backend} requires at least {report.minLevels} shared resource levels in a window. Both fitted outcomes must fall and their losses must be within {report.tolerance} {outcome === "success" ? "percentage points" : "points on the outcome × 100 scale"} of each other. A repeated match requires {report.minPeriods} matching windows.</p>
              {/each}
              <p>Algorithms rank by matching partners, partners by matched resources, and resource rows by the number of chips showing a repeated match.</p>
            </details>
          </div>
        </details>

        {#if metric && activeRow && (isAll || (cell && data && evidence))}
          <details class="disclosure matrix-section">
            <summary>Explore all algorithm pairs <span class="summary-meta">({isAll ? combinedMatrix.size : cells.length} pairs · {resources[metric] ?? metric})</span></summary>
            <div class="matrix-heading">
              <div class="settings matrix-settings">
                <Select label="Matrix view" value={choices.matrix} options={["similarity", "direction"]} format={v => v === "direction" ? "Direction" : "Similarity"} onchange={matrix => change({ matrix })} />
              </div>
            </div>
            <div class="matrix-intro">
              <h4 id="matrix-guide">
                {directional ? "Which algorithm shows the larger fitted decrease in" : "Which algorithm pairs show similar changes in"}
                {targets[outcome].toLowerCase()} across the shared range of {resources[metric].toLowerCase()} ({isAll ? "All data" : data!.backend})?
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
                <p class="matrix-example" aria-live="polite">
                  <strong>{directional ? short(rowAlg) + " → " + short(colAlg) : short(rowAlg) + " / " + short(colAlg)}</strong>
                  {#if windowEntries.length >= (directional ? 1 : (isAll ? 1 : minPeriods))}
                    · Window {directional ? "differences" : "gaps"} ({unit}):
                    {windowEntries.map(w => directional ? signed(extraLoss(w.period, w.reversed)) : fixed(w.period.gap)).join(", ")}.
                    Median <strong>{directional ? signed(activeGap) : fixed(activeGap)} {unit}</strong>.
                  {:else}
                    · {windowEntries.length} of {directional ? 1 : minPeriods} required windows have at least {data?.minLevels ?? 3} shared resource levels.
                  {/if}
                </p>
              </div>
            </div>
            <div class="scroll">
              <table class="matrix" aria-labelledby="matrix-guide" aria-describedby="matrix-reading">
                <thead><tr><th>Pair</th>{#each ids as a}<th>{short(a)}</th>{/each}</tr></thead>
                <tbody>
                  {#each ids as a}
                    <tr>
                      <th>{short(a)}</th>
                      {#each ids as b}
                        <td>
                          {#if a === b}
                            ·
                          {:else if isAll}
                            {@const c = combinedMatrix.get(`${a}/${b}`) ?? combinedMatrix.get(`${b}/${a}`)}
                            {#if c}
                              {@const selectedCell = directional ? a === rowAlg && b === colAlg : (a === rowAlg && b === colAlg) || (a === colAlg && b === rowAlg)}
                              {@const delta = directionValue(a, b)}
                              <button
                                type="button"
                                class:chosen={selectedCell}
                                aria-pressed={selectedCell}
                                aria-label={directional ? `${short(a)} to ${short(b)}: ${signed(delta)} ${unit}` : pairLabel(`${a}/${b}`)}
                                onclick={() => inspectPair(a, b)}
                                style:background-color={directional
                                  ? (delta === null || delta === 0 ? "#f1f2ee" : delta > 0 ? "#f6ddca" : "#d9ece6")
                                  : c.gap === null ? "#f1f2ee" : `hsl(162 36% ${94 - 50 * Math.exp(-c.gap / tolerance)}%)`}
                              >
                                {#if !directional && c.repeated}<span aria-hidden="true">✓ </span>{/if}{directional ? signed(delta, 1) : c.gap === null ? "—" : c.gap.toFixed(1)}
                              </button>
                            {:else}·{/if}
                          {:else}
                            {@const c = lookup(a, b)}
                            {#if c}
                              {@const selectedCell = directional ? a === rowAlg && b === colAlg : !!cell && key(c) === key(cell)}
                              {@const delta = directionValue(a, b)}
                              <button
                                type="button"
                                class:chosen={selectedCell}
                                aria-pressed={selectedCell}
                                aria-label={directional ? `${short(a)} to ${short(b)}: ${signed(delta)} ${unit}` : pairLabel(key(c))}
                                onclick={() => inspectPair(a, b)}
                                style:background-color={directional
                                  ? (delta === null || delta === 0 ? "#f1f2ee" : delta > 0 ? "#f6ddca" : "#d9ece6")
                                  : c.grouped === null || c.gap === null ? "#f1f2ee" : `hsl(162 36% ${94 - 50 * Math.exp(-c.gap / data!.tolerance)}%)`}
                              >
                                {#if !directional && matches.has(key(c))}<span aria-hidden="true">✓ </span>{/if}{directional ? signed(delta, 1) : c.grouped === null ? "—" : c.gap?.toFixed(1)}
                              </button>
                            {:else}·{/if}
                          {/if}
                        </td>
                      {/each}
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
            <p class="note">
              {#if directional}
                A dash means no window has {data?.minLevels ?? 3} shared levels.
              {:else}
                The clustering tolerance is {tolerance} {unit}. A dash means fewer than {isAll ? 1 : minPeriods} eligible windows.
              {/if}
              A dot marks the same algorithm. Select any pair to inspect its circuit construction and window coverage.
            </p>
          </details>
        {/if}
      </section>
    {/if}
  {/if}
</section>

<style>
  .compare { padding: clamp(12px, 2.3vw, 28px); display: grid; gap: 16px; min-width: 0; }
  .controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 165px), 1fr)); gap: 12px; margin: 0; }
  .controls :global(label) { min-width: 0; }
  .controls :global(select) { text-overflow: ellipsis; }
  .field-name { display: inline-flex; align-items: center; gap: 6px; }

  .summary-band { border: 1px solid var(--line); border-inline-start: 4px solid #929e99; border-radius: 10px; background: #fbfcf9; padding: clamp(14px, 2vw, 20px); display: grid; gap: 14px; min-width: 0; }
  .summary-band.strong { border-inline-start-color: var(--teal); background: #eff7f3; }
  .summary-band.partial { border-inline-start-color: #2f7d6e; background: #f3f9f6; }
  .summary-columns { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px 24px; align-items: start; }
  .summary-columns.has-metric { grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); }
  .summary-main { display: grid; gap: 6px; min-width: 0; }
  .summary-metric { display: grid; gap: 8px; min-width: 0; padding-left: 22px; border-left: 1px solid var(--line); align-content: start; }

  .takeaway-tags { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .verdict-badge, .role-tag { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; padding: 3px 8px; border-radius: 5px; }
  .verdict-badge.strong { background: #d4efe2; color: #0f5239; }
  .verdict-badge.partial { background: #e1f2ea; color: #165c44; }
  .verdict-badge.none { background: #f3ebe4; color: #6e4526; }
  .verdict-badge.insufficient { background: #eef1ee; color: #46524f; }
  .role-tag { background: #e8efec; color: var(--ink); }
  .summary-main h2 { font: 500 clamp(1.4rem, 2.4vw, 1.95rem)/1.16 Georgia, serif; letter-spacing: -0.02em; margin: 2px 0 0; }
  .takeaway-headline { font-size: 0.96rem; font-weight: 650; color: var(--ink); }
  .takeaway-detail { font-size: 0.86rem; color: var(--muted); line-height: 1.5; }

  .metric-kicker { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 0.76rem; color: var(--muted); }
  .metric-kicker > span:first-child { font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--teal); font-size: 0.68rem; }
  .metric-kicker strong { font-size: 0.92rem; color: var(--ink); font-weight: 650; }
  .scope-tag { font-size: 0.72rem; font-weight: 600; padding: 1px 7px; border-radius: 999px; background: #e5eee9; color: var(--ink); }
  .summary-metric h3 { font-size: 0.92rem; margin: 0; }
  .metric-verdict { font-size: 0.81rem; color: var(--muted); line-height: 1.45; }

  .summary-foot { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 8px 18px; padding-top: 10px; border-top: 1px solid var(--line); }
  .context-disclosure { border: 0; padding: 0; margin: 0; flex: 1 1 260px; min-width: 0; }
  .context-disclosure summary { font-size: 0.8rem; color: var(--muted); font-weight: 600; padding: 2px 0; }
  .construction-note { font-size: 0.84rem; color: var(--ink); line-height: 1.5; margin-top: 8px; }
  .base-rate-note { font-size: 0.8rem; color: var(--muted); line-height: 1.45; margin-top: 6px; }
  .card-action { padding: 2px 0; font-size: 0.82rem; flex: none; }

  @media (max-width: 760px) {
    .summary-columns.has-metric { grid-template-columns: minmax(0, 1fr); }
    .summary-metric { padding-left: 0; padding-top: 12px; border-left: 0; border-top: 1px solid var(--line); }
  }

  .shor-warning { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; background: #fdf3d7; border: 1px solid #e7cd84; border-radius: 8px; padding: 10px 12px; font-size: 0.84rem; color: #5b3c00; }
  .shor-warning button { font: inherit; font-weight: 650; background: #fff; color: var(--ink); border: 1px solid #c9ad63; border-radius: 6px; padding: 6px 10px; cursor: pointer; white-space: nowrap; }
  .shor-warning button:hover { background: #f6f8f4; }

  .visual-card { border: 1px solid var(--line); border-radius: 10px; padding: clamp(12px, 1.8vw, 18px); background: #fff; display: grid; gap: 12px; min-width: 0; }
  .workspace-bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; padding-bottom: 10px; border-bottom: 1px solid var(--line); }
  .view-switch { display: inline-flex; flex-wrap: wrap; gap: 4px; background: #edf3ef; padding: 3px; border-radius: 8px; }
  .view-switch button { border: 0; border-radius: 6px; padding: 6px 12px; background: transparent; color: var(--ink); font: inherit; font-size: 0.82rem; font-weight: 600; cursor: pointer; }
  .view-switch button[aria-pressed="true"] { background: var(--ink); color: #fff; }
  .back-link { padding: 4px 0; font-size: 0.82rem; }
  .workspace-head h3 { font-size: 1.04rem; margin: 0 0 4px; }
  .workspace-head .note { max-width: 78ch; }

  .visual-head { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 10px; }
  .chip-legend, .map-legend { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 0.76rem; color: var(--muted); align-items: center; }
  .chip-legend span, .map-legend span { display: inline-flex; align-items: center; gap: 5px; }
  .dot { display: inline-block; width: 10px; height: 10px; background: var(--c); border-radius: 50%; }
  .dot.ibm_kingston { border-radius: 1px; transform: rotate(45deg); width: 8px; height: 8px; }
  .dot.ibm_marrakesh { width: 0; height: 0; background: none; border-radius: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-bottom: 9px solid var(--c); }
  .swatch { display: inline-block; width: 11px; height: 11px; border-radius: 3px; }
  .swatch.cross { background: #0f6b56; }
  .swatch.repeated { background: #cce8da; border: 1px solid #7ab59a; }
  .swatch.isolated { background: #eef6f1; border: 1px solid #bfd8ca; }
  .swatch.different { background: #f2f3f0; border: 1px solid #d5dcd7; }

  .more-views { display: grid; gap: 8px; min-width: 0; }
  .summary-meta { color: var(--muted); font-weight: 450; font-size: 0.84rem; margin-left: 4px; }

  .partner-map { width: 100%; border-collapse: collapse; font-size: 0.78rem; min-width: 520px; }
  .partner-map th, .partner-map td { text-align: center; padding: 3px; border-bottom: 1px solid var(--line); }
  .partner-map thead th { font-size: 0.72rem; color: var(--muted); font-weight: 650; white-space: nowrap; }
  .partner-map tbody th { text-align: left; padding-inline: 6px 10px; font-weight: 650; white-space: nowrap; background: #fff; position: static; }
  .partner-map tr.active-partner th { color: var(--teal); box-shadow: inset 3px 0 0 var(--teal); }
  .map-cell { width: 100%; min-width: 40px; min-height: 30px; border-radius: 5px; border: 1px solid transparent; font: inherit; font-size: 0.76rem; font-weight: 650; font-variant-numeric: tabular-nums; cursor: pointer; padding: 2px 4px; }
  .map-cell.cross { background: #0f6b56; color: #fff; }
  .map-cell.repeated { background: #cce8da; color: #124c35; border-color: #84bca0; }
  .map-cell.isolated { background: #eef6f1; color: #2b634d; border-color: #c5ded0; }
  .map-cell.different { background: #f3f4f1; color: #5d6f69; border-color: #dde3df; }
  .map-cell:hover { filter: brightness(0.95); }
  .map-cell.selected { outline: 2px solid var(--ink); outline-offset: -2px; }
  .map-empty { color: #b7c5bf; }

  .overview { display: grid; gap: 6px; min-width: 0; }
  .overview p { line-height: 1.5; margin: 6px 0; }
  .comparison-help h4 { margin: 10px 0 0; }
  .worked-example { background: var(--paper); border-inline-start: 3px solid var(--teal); padding: 8px 12px; }
  .unavailable-toggle { flex-direction: row; align-items: center; width: fit-content; cursor: pointer; }
  .evidence { width: 100%; border-collapse: collapse; }
  .evidence tbody th { position: static; background: white; }
  .evidence td, .evidence th { padding: 6px; vertical-align: middle; }
  .evidence button { width: 100%; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: #f6f7f5; text-align: left; color: var(--ink); cursor: pointer; font: inherit; }
  .evidence button:hover { background: #edf4ef; border-color: #93b5a9; }
  .count-key { display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: center; font-size: 0.83rem; color: var(--muted); }
  .count-key span { display: inline-flex; gap: 6px; align-items: center; }
  .sample { display: inline-block; border-radius: 5px; padding: 3px 7px; background: #f2f4f2; }
  .total { display: inline-block; }
  .count-key .match, .evidence button.match { background: #dbefe3; color: #14543a; }
  .evidence button.match { border-color: #8ebca2; }
  .evidence button[aria-pressed="true"] { outline: 2px solid var(--ink); outline-offset: -2px; }
  .evidence small { display: block; line-height: 1.25; }
  .val-tag { font-size: 0.7rem; color: var(--muted); font-weight: 550; }

  .stat { border-left: 3px solid var(--teal); padding-left: 12px; display: grid; }
  .stat strong { font-size: 1.4rem; font-variant-numeric: tabular-nums; }
  .stat span { font-size: 0.78rem; color: var(--muted); }

  .gap-chart { margin: 0; }
  .gap-chart figcaption { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .gap-chart figcaption h3 { font-size: 1rem; margin: 0 0 2px; }
  .threshold-key { font-size: 0.78rem; color: var(--muted); display: inline-flex; gap: 6px; align-items: center; }
  .threshold-key::before { content: ""; height: 1em; border-inline-start: 2px dashed #586962; }
  .gap-chart ul { list-style: none; margin: 10px 0 0; padding: 0; }
  .gap-chart li { display: grid; grid-template-columns: minmax(11.5rem, 1.45fr) minmax(70px, 2.4fr) 9.5rem 8rem; align-items: center; gap: 10px; padding: 7px 0; font-size: 0.85rem; font-variant-numeric: tabular-nums; }
  .gap-chart .window { display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .gap-chart .gap-value { text-align: end; line-height: 1.25; }
  .gap-chart strong { display: block; }
  .ci-text { display: block; font-size: 0.72rem; font-weight: 450; color: var(--muted); }
  .chip-pill { display: inline-block; font-size: 0.68rem; font-weight: 700; padding: 1px 6px; border-radius: 4px; color: #fff; background: var(--c, var(--teal)); white-space: nowrap; }
  .track { position: relative; height: 10px; border-radius: 3px; background: #e6ebe8; }
  .track i { height: 100%; display: block; background: #8a7769; border-radius: 3px; }
  .similar .track i { background: var(--teal); }
  .track .ci-band { position: absolute; top: 3px; height: 4px; background: #143e3966; border-inline: 2px solid var(--ink); border-radius: 1px; }
  .track b { position: absolute; top: -4px; bottom: -4px; border-inline-start: 2px dashed #586962; }
  .status { color: #695448; }
  .similar .status { color: var(--teal); }

  .legend { display: flex; gap: 20px; flex-wrap: wrap; font-size: 0.85rem; font-weight: 650; }
  .legend span:first-child { color: var(--teal); }
  .legend span:last-child { color: #a03e10; }
  .plot-heading { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
  .plot-heading + .note { margin-top: -8px; }
  .panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 255px), 1fr)); gap: 10px; }
  .panels article { min-width: 0; border: 1px solid var(--line); padding: 12px 6px 0; border-radius: 9px; }
  .panels h4, .window-label { padding: 0 8px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .scroll { max-width: 100%; overflow: auto; }

  .matrix-heading { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
  .matrix-settings { margin: 0; width: min(100%, 12rem); }
  .matrix-intro { display: grid; gap: 8px; }
  #matrix-guide { margin: 0; font-size: 1rem; font-weight: 700; line-height: 1.45; }
  .matrix-callout { background: #f1f6f3; border-inline-start: 3px solid var(--teal); padding: 10px 14px; line-height: 1.5; }
  .matrix-callout p { margin: 0; }
  .matrix-callout .matrix-example { margin-top: 6px; }
  .matrix { table-layout: fixed; min-width: 500px; }
  .matrix th, .matrix td { text-align: center; padding: 2px; }
  .matrix button { width: 100%; min-height: 34px; border: 0; border-radius: 3px; color: var(--ink); cursor: pointer; font: inherit; }
  .matrix button.chosen { outline: 2px solid var(--ink); outline-offset: -2px; }
  .matrix button:hover { box-shadow: inset 0 0 0 1px var(--teal); }

  .coverage ul { list-style: none; padding: 0; }
  .coverage li { display: flex; justify-content: space-between; gap: 7px; padding: 3px 0; overflow-wrap: anywhere; }
  summary { cursor: pointer; font-weight: 650; }
  .disclosure { margin: 0; border-top: 1px solid var(--line); padding-top: 6px; min-width: 0; }
  .disclosure[open] > :not(summary) { margin-top: 10px; }

  @media (max-width: 640px) {
    .gap-chart li { grid-template-columns: minmax(0, 1fr) 8rem; gap: 4px 12px; }
    .track { grid-column: 1; grid-row: 2; }
    .gap-chart .gap-value { grid-column: 2; grid-row: 2; }
    .gap-chart .status { grid-column: 2; grid-row: 1; font-size: 0.78rem; }
  }
</style>
