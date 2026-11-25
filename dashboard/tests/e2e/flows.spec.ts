// The browser flows listed in dashboard/README.md, against the production build and real data.
import { expect, test, type Page } from "@playwright/test";

async function openApp(page: Page, hash = "") {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("console", (message) => message.type() === "error" && errors.push(message.text()));
  await page.goto(`./${hash}`);
  await expect(page.locator("#source")).toContainText("jobs");
  return errors;
}

async function openFirstJob(page: Page) {
  await page.getByText("Compare the experiments shown").click();
  await page.locator("#settings-table button.job-value").first().click();
  await expect(page.locator("#histogram-title")).toBeFocused();
}

async function openNavigation(page: Page) {
  const toggle = page.getByRole("banner").getByRole("button", { name: /navigation menu/i });
  if ((await toggle.getAttribute("aria-expanded")) !== "true") {
    await toggle.click();
  }
  return page.getByRole("tablist", { name: "Experiment sections" });
}

async function selectSection(page: Page, name: string, exact = false) {
  const navigation = await openNavigation(page);
  await navigation.getByRole("tab", { name, exact }).click();
}

test("1 · inline axes and scope filters update the plot and open a histogram @narrow", async ({ page }) => {
  const errors = await openApp(page, "#section=range");
  await expect(page.locator("#plot-title")).toContainText("At which qubit counts");
  await page.getByLabel("Algorithm").selectOption({ label: "Grover" });
  const plot = page.getByRole("region", { name: "Operating range plot" });
  const y = plot.getByLabel("Y-axis");
  await expect(y.locator("option:checked")).toHaveText("Success rate: How often was the answer accepted?");
  await expect(y.locator("option")).toHaveCount(7);
  await y.selectOption("dsr");
  await expect(page.locator("#plot-title")).toContainText("strongest wrong answer");
  await expect(page.locator("#coverage")).toContainText("jobs");

  const periods = page.getByLabel("Periods (UTC)");
  await expect(periods.locator("option").first()).toHaveText("All periods");
  const before = await page.locator("#coverage").textContent();
  await periods.selectOption({ index: 1 });
  await expect(page.locator("#coverage")).not.toHaveText(before!);
  await plot.getByLabel("X-axis").selectOption({ label: "Executed ISA depth" });
  await expect(page.locator("#plot-title")).toContainText("At which depths");
  await page.reload();
  await expect(y.locator("option:checked")).toHaveText("Differential Success Rate: Did accepted peaks stand out?");
  await expect(plot.getByLabel("X-axis").locator("option:checked")).toHaveText("Executed ISA depth");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  await openFirstJob(page);
  await expect(page.locator("#hist svg")).toBeVisible();
  await page.getByRole("button", { name: "Operating range" }).click();
  await expect(page.locator("#plot-title")).toBeVisible();
  expect(errors).toEqual([]);
});

test("overview legend sits directly below the Y-axis selector on desktop", async ({ page }) => {
  await openApp(page, "#section=range&mode=overview&a=PHASE-ESTIMATION&q=hellinger");
  const plot = page.getByRole("region", { name: "Operating range plot" });
  const box = (await plot.getByLabel("Y-axis").boundingBox())!;
  const legend = (await plot.locator(".legend").boundingBox())!;
  const gap = legend.y - box.y - box.height;
  expect(gap).toBeGreaterThanOrEqual(0);
  expect(gap).toBeLessThanOrEqual(12);
});

test("run dots show measurement details and open the run histogram @narrow", async ({ page, isMobile }) => {
  await openApp(page, "#section=range&t=none");
  await expect(page.getByText("One dot per run")).toBeVisible();
  await expect(page.getByText(isMobile ? "Tap for histogram" : "Hover for details · Click for histogram")).toBeVisible();
  const dot = page.locator('#trend svg path[fill="#087363"]').last();
  if (isMobile) {
    await dot.tap();
  } else {
    await dot.scrollIntoViewIfNeeded();
    const box = (await dot.boundingBox())!;
    const x = box.x + box.width / 2, y = box.y + box.height / 2;
    await page.mouse.move(x, y);
    await expect(page.locator("#interval-lens")).toContainText("Repetition");
    await page.mouse.click(x, y);
  }
  await expect(page.locator("#histogram-title")).toBeVisible();
  await expect(page.locator("#hist svg")).toBeVisible();
});

test("2 · experiment picker searches, selects by keyboard, and Escape keeps the selection", async ({ page }) => {
  await openApp(page, "#section=range");
  await openFirstJob(page);
  const trigger = page.locator("#choose-config");
  const original = await trigger.textContent();

  await trigger.click();
  const search = page.locator("#experiment-search");
  await expect(search).toBeFocused();
  await search.fill("zzzz-no-match");
  await expect(page.locator("#picker-empty")).toBeVisible();
  await page.getByRole("button", { name: "Clear search" }).click();
  await search.press("ArrowDown");
  await page.keyboard.press("ArrowDown");
  const target = (await page.locator("#experiment-results button:focus strong").textContent())!;
  await page.keyboard.press("Enter");
  await expect(page.locator("#experiment-picker")).not.toBeVisible();
  await expect(trigger).toHaveText(target);
  expect(target).not.toBe(original);

  await trigger.click();
  await page.keyboard.press("Escape");
  await expect(page.locator("#experiment-picker")).not.toBeVisible();
  await expect(trigger).toHaveText(target);
  await expect(trigger).toBeFocused();
});

test("3 · chart detail groups bitstrings without changing metrics", async ({ page }) => {
  await openApp(page, "#section=range");
  // Open the job with the most distinct outcomes so grouping is guaranteed.
  const busiest = await page.evaluate(async () => {
    const data = await (await fetch("data/index.json")).json();
    return data.jobs.reduce((a: any, b: any) =>
      Object.keys(b.counts).length > Object.keys(a.counts).length ? b : a,
    );
  });
  await page.goto(`./#a=${busiest.algorithm}&v=job&c=${busiest.config}&r=${busiest.ref}:${busiest.rep}`);
  await expect(page.locator("#histogram-title")).toBeVisible();
  const metrics = await page.locator("#numbers").textContent();
  const rows = await page.locator("#outcomes tr").count();
  await expect(page.locator("#bins-help")).toContainText("grouped as “Other outcomes”");
  await page.getByLabel("Chart detail").selectOption({ label: "Expanded · up to 32 bitstrings" });
  await expect(page.locator("#bins-help")).toContainText(/^(3[0-2]|[12]?\d) individual bitstrings/);
  await expect(page.locator("#numbers")).toHaveText(metrics!);
  expect(await page.locator("#outcomes tr").count()).toBe(rows);
});

test("4 · run calibration round-trip preserves the histogram run and settings", async ({ page }) => {
  await openApp(page, "#section=range");
  await openFirstJob(page);
  await page.getByLabel("Chart detail").selectOption({ label: "Standard · up to 16 bitstrings" });
  const run = await page.getByLabel("Recorded run").inputValue();
  const experiment = await page.locator("#choose-config").textContent();

  await page.getByRole("button", { name: /Inspect run calibration/ }).click();
  await expect(page.locator("#calibration-title")).toHaveText("Calibration for this run");
  await expect(page.getByLabel("Calibration snapshot (UTC)")).toBeDisabled();
  await page.locator("#cal-mode").selectOption({ label: "T1 · relaxation time" });
  await expect(page.locator("#cal-value")).toContainText("μs");
  await page.getByRole("button", { name: "Explore this component’s history" }).click();
  await expect(page.locator("#calibration-title")).toHaveText("Chip calibration history");
  await expect(page.getByLabel("Calibration snapshot (UTC)")).toBeEnabled();

  await page.getByRole("button", { name: "← Back to job histogram" }).click();
  await expect(page.locator("#job-calibration")).toBeFocused();
  await expect(page.getByLabel("Recorded run")).toHaveValue(run);
  await expect(page.locator("#choose-config")).toHaveText(experiment!);
  await expect(page.getByLabel("Chart detail")).toHaveValue("1");
});

test("5 · chip calibration history opens independently and searches components @narrow", async ({ page }) => {
  const errors = await openApp(page, "#section=range&mode=overview");
  const history = page.getByRole("button", { name: "Chip calibration history" });
  const toggle = page.getByRole("switch", { name: "Show run details" });
  await expect(history).toBeVisible();
  await history.click();
  await page.reload();
  await page.getByRole("button", { name: "← Back to operating range" }).click();
  await expect(toggle).not.toBeChecked();
  await toggle.click();
  await expect(history).toBeVisible();
  await history.click();
  await expect(page.locator("#calibration-title")).toHaveText("Chip calibration history");
  await expect(page.locator("#cal-map svg")).toBeVisible();
  await page.getByLabel("Find a qubit or connection").fill("Q99999");
  await expect(page.getByText("No matching components.")).toBeVisible();
  await page.getByLabel("Find a qubit or connection").fill("");
  await page.locator("#cal-mode").selectOption({ label: "Two-qubit gate errors" });
  await expect(page.getByLabel("Operation")).toBeVisible();
  await expect(page.locator("#cal-component-title")).toContainText("→");
  const width = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  expect(width).toBeLessThanOrEqual(0);
  await page.getByRole("button", { name: "← Back to operating range" }).click();
  await expect(page.locator("#open-calibration")).toBeFocused();
  expect(errors).toEqual([]);
});

test("deep links restore the histogram view", async ({ page }) => {
  await openApp(page, "#section=range");
  await openFirstJob(page);
  const url = page.url();
  await page.goto("about:blank");
  await page.goto(url);
  await expect(page.locator("#histogram-title")).toBeVisible();
  expect(new URL(url).hash).toContain("v=job");
});

test("compare decay shows matched fits, shares selections and restores range settings @narrow", async ({ page }) => {
  const errors = await openApp(page, "#section=range");
  await page.getByLabel("Algorithm", { exact: true }).selectOption({ label: "Grover" });
  await selectSection(page, "Compare decay");
  const panel = page.getByRole("region", { name: "Decay comparison" });
  const partner = panel.getByLabel("Compare with");
  const outcomePicker = panel.getByLabel("Outcome");
  const outcomeOrder = [
    "Success rate · 11 matching pairs", "Hellinger fidelity · 10 matching pairs",
    "TVD similarity · 10 matching pairs", "Chance-adjusted, ideal-normalized success · 8 matching pairs",
    "Differential success rate · 7 matching pairs",
  ];
  await expect(outcomePicker.locator("option")).toHaveText(outcomeOrder);
  const primary = panel.getByLabel("Algorithm", { exact: true });
  await expect(primary.locator("option:checked")).toHaveText("vTP · 5 matching partners");
  await expect(primary.locator("option").last()).toHaveText("Grover · 0 matching partners");
  await primary.selectOption({ label: "Phase estimation · 3 matching partners" });
  await expect(partner).toHaveValue("QFT");
  await expect(panel.locator(".worked-example")).toBeHidden();
  await panel.getByText("How to read this comparison", { exact: true }).click();
  await expect(panel.getByRole("heading", { name: "Phase estimation contains an inverse QFT" })).toBeVisible();
  const ratios = panel.getByRole("row", { name: /^Entanglement ratio/ });
  await expect(panel.locator(".worked-example")).toContainText("this window counts toward the first number");
  await expect(ratios.locator("button")).toHaveText(["2 of 3 ✓", "2 of 3 ✓"]);
  await expect(ratios.locator("td strong")).toHaveText(["4 of 6", "2 of 3", "2 of 3"]);
  const gates = panel.getByRole("row", { name: /^Logical two-qubit gates/ });
  await expect(gates.locator("td strong")).toHaveText(["2 of 6", "2 of 3", "0 of 3"]);
  await gates.getByRole("button", { name: /ibm_fez/ }).click();
  await expect(panel.locator(".gap-chart li strong")).toHaveText(["31.01 pp", "2.25 pp", "4.34 pp"]);
  await panel.getByText("Observed outcomes and fitted trends", { exact: true }).click();
  await expect(panel.locator(".panels article")).toHaveCount(3);
  await gates.getByRole("button", { name: /ibm_kingston/ }).click();
  await expect(panel.getByRole("heading", { name: "Similar decline in 0 of 3 eligible windows" })).toBeVisible();
  await page.reload();
  await expect(gates.getByRole("button", { name: /ibm_kingston/ })).toHaveAttribute("aria-pressed", "true");
  await panel.getByText("Slopes and rank correlations by window").click();
  await expect(panel.locator(".fit-details tbody tr td:last-child")).toHaveText(["0.90", "0.90", "0.90"]);
  await expect(outcomePicker.locator("option")).toHaveText(outcomeOrder);
  await outcomePicker.selectOption({ label: "Hellinger fidelity · 10 matching pairs" });
  await expect(panel.getByRole("heading", { name: /how often did Hellinger fidelity fall/i })).toBeVisible();
  await expect(partner).toHaveValue("QFT");
  await selectSection(page, "Operating range");
  await expect(page.getByLabel("Algorithm", { exact: true }).locator("option:checked")).toHaveText("Grover");
  expect(errors).toEqual([]);
});

test("compare decay distinguishes limited coverage and includes other measured partners @narrow", async ({ page }) => {
  const errors = await openApp(page, "#section=decay");
  const panel = page.getByRole("region", { name: "Decay comparison" });
  await panel.getByLabel("Algorithm", { exact: true }).selectOption({ label: "Phase estimation · 3 matching partners" });
  await panel.getByLabel("Compare with").selectOption("SHOR");
  const width = panel.getByRole("row", { name: /^Total logical qubits/ });
  await expect(width.locator(".match")).toHaveText(["3 of 4", "3 of 3 ✓"]);
  await expect(panel.locator("#count-guide")).toContainText("Unavailable for comparison");
  await expect(width.locator("td strong")).toHaveText(["3 of 4", "0 of 1", "3 of 3"]);
  const unavailable = panel.getByRole("checkbox", { name: "Show unavailable comparisons" });
  const gates = panel.getByRole("row", { name: /^Logical two-qubit gates/ });
  await expect(gates).toHaveCount(0);
  await unavailable.check();
  await expect(panel.locator("#coverage-guide")).toBeVisible();
  await expect(gates.getByRole("button", { name: /ibm_fez, 0 of 3 shared levels/ })).toBeVisible();
  await unavailable.uncheck();
  await expect(panel.locator("#coverage-guide")).toHaveCount(0);
  await expect(gates).toHaveCount(0);
  await width.getByRole("button", { name: /ibm_fez/ }).click();
  await expect(panel.getByRole("heading", { name: "Too few comparable windows" })).toBeVisible();
  await width.getByRole("button", { name: /ibm_kingston/ }).click();
  await expect(panel.locator(".stat strong")).toHaveText("2.59 pp");
  await panel.getByLabel("Algorithm", { exact: true }).selectOption({ label: "Grover · 0 matching partners" });
  await panel.getByLabel("Compare with").selectOption("QFT");
  await page.reload();
  await expect(panel.getByRole("heading", { name: "Grover and QFT", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  expect(errors).toEqual([]);
});

test("all-data GHZ and BV comparison includes the new Fez window @narrow", async ({ page }) => {
  const errors = await openApp(page, "#section=decay&pair=GHZ%2FBERNSTEIN-VAZIRANI&outcome=success");
  const panel = page.getByRole("region", { name: "Decay comparison" });
  await expect(panel.getByRole("columnheader")).toHaveText([
    "Circuit resource", "All data", "ibm_fez", "ibm_kingston",
  ]);
  const gates = panel.getByRole("row", { name: /^Logical two-qubit gates/ });
  await expect(gates.locator("td strong")).toHaveText(["0 of 7", "0 of 4", "0 of 3"]);
  await gates.getByRole("button", { name: /ibm_fez/ }).click();
  const window = panel.locator(".gap-chart li").filter({ hasText: "Nov 23, 2026" });
  await expect(window).toContainText("25.94 pp");
  expect(errors).toEqual([]);
});

test("Marrakesh validation contributes only to the all-data count @narrow", async ({ page }) => {
  await openApp(page, "#section=decay&pair=PHASE-ESTIMATION%2FRANDOM-VOLUMETRIC&outcome=success");
  const panel = page.getByRole("region", { name: "Decay comparison" });
  const widths = panel.getByRole("row", { name: /^Total logical qubits/ });
  await expect(widths.locator("td strong")).toHaveText(["2 of 7", "0 of 3", "1 of 3"]);
  await expect(panel.getByRole("columnheader")).toHaveText(["Circuit resource", "All data", "ibm_fez", "ibm_kingston"]);
});

test("footprint tab traces metric selection, subset scores and model results @narrow", async ({ page }) => {
  const errors = await openApp(page, "#section=range");
  await selectSection(page, "Footprint", true);
  const panel = page.getByRole("region", { name: "Footprint selection experiment" });
  await panel.getByLabel("Target quality metric").selectOption({ label: "Success Rate" });
  const selected = panel.getByRole("region", { name: "Selected footprint" });
  await expect(selected.getByRole("button")).toHaveCount(10);
  await expect(panel.getByRole("list", { name: "Footprint generation process" }).getByRole("listitem")).toHaveCount(3);
  const volume = selected.getByRole("button", { name: "Circuit volume", exact: true });
  await volume.click();
  await expect(volume).toHaveAttribute("aria-pressed", "true");
  await expect(selected.getByText(/Circuit width multiplied by depth/)).toBeVisible();
  await expect(panel.locator(".evidence details[open]")).toHaveCount(0);
  await panel.getByText("Why each metric was kept or left out", { exact: true }).click();
  const metrics = panel.getByRole("table", { name: "Metric selection evidence" });
  await expect(metrics.locator("tbody tr")).toHaveCount(11);
  await expect(metrics.getByText("Retained", { exact: true })).toHaveCount(10);
  await panel.getByText("How many metrics were enough?", { exact: true }).click();
  await expect(panel.getByRole("table", { name: "LightGBM footprint size experiment" }).getByRole("row", { name: /10 · Selected/ })).toContainText("0.8323");
  await panel.getByText("How did the regressors perform?", { exact: true }).click();
  await expect(panel.getByRole("table", { name: "Circuit-only regressor performance" }).locator("tbody tr")).toHaveCount(8);
  await panel.getByText("Ranking formula and SHAP contributions").click();
  await expect(panel.getByRole("img", { name: "Mean absolute SHAP by circuit metric" }).locator("svg")).toBeVisible();
  await panel.getByLabel("Chip / Scope").selectOption({ label: "IBM Fez (ibm_fez)" });
  await expect(selected.getByRole("button")).toHaveCount(8);
  await page.reload();
  await panel.getByText("Why each metric was kept or left out", { exact: true }).click();
  await expect(metrics.locator("tbody tr")).toHaveCount(15);
  await expect(panel.getByLabel("Target quality metric").locator("option:checked")).toHaveText("Success Rate");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  await selectSection(page, "Model training");
  await expect(page.getByLabel("Thesis view")).toBeVisible();
  expect(errors).toEqual([]);
});

test("direction compares column loss to row loss and preserves the question on reload @narrow", async ({ page }) => {
  const errors = await openApp(page, "#section=decay&b=ibm_kingston&resource=a.num_qubits&outcome=success&pair=QFT%2FPHASE-ESTIMATION");
  const panel = page.getByRole("region", { name: "Decay comparison" });
  await panel.locator(".matrix-section > summary").click();
  await expect(panel.locator("#matrix-guide")).toContainText("Which algorithm pairs show similar changes");
  await panel.getByLabel("Matrix view").selectOption({ label: "Direction" });
  await expect(panel.locator("#matrix-guide")).toContainText("larger fitted decrease in success rate");
  const forward = panel.getByRole("button", { name: /^QFT to PE:/ });
  const reverse = panel.getByRole("button", { name: /^PE to QFT:/ });
  const shown = Number(await forward.innerText());
  expect(Number.isFinite(shown)).toBeTruthy();
  expect(Number(await reverse.innerText()) + shown).toBeCloseTo(0);
  await reverse.click();
  await expect(panel.locator(".stat span")).toContainText("QFT relative to PE");
  await expect(panel.locator(".stat strong")).toContainText((await reverse.getAttribute("aria-label"))!.split(": ")[1]);
  await page.reload();
  await panel.locator(".matrix-section > summary").click();
  await expect(reverse).toHaveAttribute("aria-pressed", "true");
  await expect(panel.locator(".gap-chart")).toBeVisible();
  await panel.getByLabel("Matrix view").selectOption({ label: "Similarity" });
  await expect(panel.locator(".stat span")).toHaveText("Median gap in fitted change");
  expect(errors).toEqual([]);
});

test("average explorer selects measured settings and updates both axes @narrow", async ({ page }) => {
  const errors = await openApp(page, "#section=range&mode=overview");
  const panel = page.getByRole("region", { name: "Experiment explorer", exact: true });
  const filters = panel.getByRole("group", { name: "Experiment filters" });
  for (const name of ["Chip", "Periods (UTC)", "Experiment group"]) {
    const field = filters.getByRole("combobox", { name, exact: true });
    await field.selectOption({ index: 1 });
    await expect(field).toHaveValue("1");
    await field.selectOption({ index: 0 });
  }
  await panel.getByLabel("Minimum success rate").fill("80");
  await panel.getByLabel("Algorithm").selectOption({ label: "Grover" });
  await expect(panel.getByRole("heading")).toHaveText("At which qubit counts do at least 50% of shots return an accepted answer on average?");
  await expect(panel.getByLabel("Minimum success rate")).toHaveValue("50");
  await panel.getByLabel("Minimum success rate").fill("");
  await panel.getByLabel("Y-axis").selectOption("tvd");
  await expect(panel.getByRole("heading")).toHaveText("At which qubit counts must at most 50% of probability shift to match the ideal output on average?");
  await panel.getByLabel("X-axis").selectOption({ label: "Executed ISA depth" });
  await expect(panel.getByRole("heading")).toHaveText("At which depths must at most 50% of probability shift to match the ideal output on average?");
  const svg = panel.locator("#average-plot svg");
  await expect(svg.locator('path[stroke="#387b9a"]').first()).toBeVisible();
  const line = svg.locator('path[stroke="#087363"]').first();
  await panel.getByRole("slider", { name: "Selected tested setting" }).press("Home");
  const point = await line.evaluate((path: SVGPathElement) => {
    const local = path.getPointAtLength(path.getTotalLength() * 0.9);
    const screen = local.matrixTransform(path.getScreenCTM()!);
    const rect = path.ownerSVGElement!.getBoundingClientRect();
    return { x: screen.x - rect.left, y: screen.y - rect.top };
  });
  await expect(svg.locator("text").filter({ hasText: /Full TVD\s+0\./ })).toHaveCount(1);
  const reading = panel.locator("#average-reading");
  const before = await reading.innerText();
  await svg.click({ position: point });
  await expect(reading).not.toHaveText(before);
  await expect(reading).toContainText("ISA layers");
  await expect(reading).toContainText("probability mass");
  const clicked = await reading.innerText();
  await page.reload();
  await expect(reading).toHaveText(clicked);
  await panel.getByLabel("Maximum full tvd").fill("0.3");
  await expect(panel.getByRole("heading")).toHaveText("At which depths must at most 30% of probability shift to match the ideal output on average?");
  await expect(panel.locator(".target-answer")).toBeVisible();
  await expect(panel.locator(".legend")).toContainText("0 is better");
  const targetLine = panel.getByRole("slider", { name: "Plot target" });
  await targetLine.scrollIntoViewIfNeeded();
  const box = (await targetLine.boundingBox())!;
  const gripX = box.x + box.width - 30;
  const gripY = box.y + box.height / 2;
  await page.mouse.move(gripX, gripY);
  await page.mouse.down();
  await page.mouse.move(gripX, gripY - 35, { steps: 5 });
  await page.mouse.up();
  const dragged = Number(await panel.getByLabel("Maximum full tvd").inputValue());
  expect(dragged).toBeGreaterThan(0.3);
  await expect(targetLine).toHaveAttribute("aria-valuenow", String(dragged));
  await targetLine.press("ArrowDown");
  await expect(targetLine).toHaveAttribute("aria-valuenow", String(Math.round(dragged * 100 - 1) / 100));
  const slider = panel.getByRole("slider", { name: "Selected tested setting" });
  await expect(panel.locator('input[type="range"]')).toHaveCount(0);
  await slider.focus();
  await slider.press("Home");
  await expect(reading).toContainText(/Observed best .* · worst /);
  await expect(reading).not.toHaveText(clicked);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  expect(errors).toEqual([]);
});

test("Operating range accepts decimal percentages and steps in tenths @narrow", async ({ page }) => {
  await openApp(page, "#section=range");
  const target = page.getByLabel("Minimum success rate");
  await target.fill("");
  await target.pressSequentially("55.5");
  await expect(target).toHaveValue("55.5");
  await target.press("ArrowUp");
  await expect(target).toHaveValue("55.6");
  await target.press("ArrowDown");
  await expect(target).toHaveValue("55.5");
  await expect(page.locator("#coverage")).toBeHidden();
  await page.getByText("Experiment details", { exact: true }).click();
  await expect(page.locator("#coverage")).toBeVisible();
  await expect(page.locator("#coverage")).toContainText("Target ≥ 55.5%");
});

test("Run details shows all tested settings and preserves the overview question and point @narrow", async ({ page }) => {
  await openApp(page, "#section=regression&a=GROVER&t=0.73");
  const point = page.getByRole("slider", { name: "Selected tested setting" });
  await point.press("End");
  const setting = await point.getAttribute("aria-valuenow");
  const coverage = (await page.locator("#coverage").textContent())!;
  const axes = page.getByLabel(/^[XY]-axis$/);
  const axisState = () => axes.evaluateAll(elements => elements.map(element => {
    const select = element as HTMLSelectElement;
    return { value: select.value, options: Array.from(select.options, option => option.text) };
  }));
  async function checkAxisPositions(chartId: string) {
    const chart = (await page.locator(chartId).boundingBox())!;
    const y = (await page.getByLabel("Y-axis").boundingBox())!;
    const x = (await page.getByLabel("X-axis").boundingBox())!;
    expect(y.y + y.height).toBeLessThanOrEqual(chart.y + 1);
    expect(x.y).toBeGreaterThanOrEqual(chart.y + chart.height - 1);
  }
  await checkAxisPositions("#average-plot");
  const overviewAxes = await axisState();
  const question = await page.locator("#plot-title").innerText();
  const answer = await page.locator(".target-answer").innerText();
  const toggle = page.getByRole("switch", { name: "Show run details" });
  const target = page.getByRole("spinbutton", { name: "Minimum success rate" });
  await toggle.scrollIntoViewIfNeeded();
  const targetBox = (await target.boundingBox())!;
  const switchBox = (await toggle.boundingBox())!;
  expect(switchBox.y).toBeGreaterThanOrEqual(targetBox.y + targetBox.height);
  await toggle.click();
  await expect(toggle).toBeChecked();
  expect(await toggle.boundingBox()).toEqual(switchBox);
  expect(await target.boundingBox()).toEqual(targetBox);
  expect(await axisState()).toEqual(overviewAxes);
  await checkAxisPositions("#trend");
  await expect(page.locator("#plot-title")).toHaveText(question);
  await expect(page.locator(".target-answer")).toHaveText(answer);
  const widths = await page.locator("#settings-table tr td:nth-child(3)").allTextContents();
  expect(new Set(widths).size).toBeGreaterThan(1);
  await expect(page.locator("#coverage")).toHaveText(coverage);
  await expect(page.getByLabel("Minimum success rate")).toHaveValue("73");
  await expect(page.getByLabel("Algorithm", { exact: true }).locator("option:checked")).toHaveText("Grover");
  await page.reload();
  await expect(page.locator("#coverage")).toHaveText(coverage);
  await openFirstJob(page);
  await page.getByRole("button", { name: "Operating range", exact: true }).click();
  await toggle.click();
  await expect(point).toHaveAttribute("aria-valuenow", setting!);
  await expect(page.getByLabel("Minimum success rate")).toHaveValue("73");
});

test("report tabs share the pooled export and load other reports on demand", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (path.includes("/data/")) requests.push(path.split("/").pop()!);
  });
  const errors = await openApp(page, "#section=range");
  expect(requests).toEqual(["index.json"]);
  await page.getByRole("tab", { name: "Footprint" }).click();
  await expect(page.getByRole("region", { name: "Selected footprint" })).toBeVisible();
  await page.getByRole("tab", { name: "Model training" }).click();
  await expect(page.getByRole("heading", { name: /Model leaderboard/ })).toBeVisible();
  expect(requests.filter(name => name.startsWith("estimation-pooled"))).toHaveLength(1);
  await page.getByRole("tab", { name: "Execution cost" }).click();
  await expect(page.getByRole("heading", { name: "What will a job cost before it runs?" })).toBeVisible();
  await page.getByRole("tab", { name: "Model validation" }).click();
  await expect(page.getByRole("heading", { name: "How well do frozen QAQS models predict new QPU runs?" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("target units and midpoint follow the Y-axis on both plots @narrow", async ({ page }) => {
  await openApp(page, "#q=success&t=0.75");
  await expect(page.getByLabel("Minimum success rate")).toHaveValue("75");
  for (const details of [true, false]) {
    await page.getByRole("switch", { name: "Show run details" }).setChecked(details);
    const axis = page.getByLabel("Y-axis");
    const field = page.getByRole("spinbutton");
    const line = page.getByRole("slider", { name: "Plot target" });
    for (const metric of ["dsr", "contrast", "coarse", "tvd", "hellinger", "chance", "success"]) {
      await axis.selectOption(metric);
      const percent = metric === "success";
      await expect(field).toHaveValue(percent ? "50" : "0.5");
      await expect(field).toHaveAttribute("max", percent ? "100" : "1");
      if (metric === "dsr" || percent) {
        await expect(line).toHaveAttribute("aria-valuenow", percent ? "50" : "0.5");
        await field.fill(percent ? "100" : "1");
        await expect(line).toHaveAttribute("aria-valuetext", percent ? "100.0%" : "1.000");
        await line.press("Home");
        await expect(field).toHaveValue("0");
        await line.press("ArrowUp");
        await expect(field).toHaveValue(percent ? "1" : "0.01");
        await field.fill("");
        await expect(line).toHaveCount(0);
      }
    }
  }
});

test("dragging the operating range target updates the chart, input and URL @narrow", async ({ page }) => {
  await openApp(page, "#q=dsr&t=0.25");
  const line = page.getByRole("slider", { name: "Plot target" });
  await line.scrollIntoViewIfNeeded();
  const box = (await line.boundingBox())!;
  const x = box.x + box.width * 0.7;
  const y = box.y + box.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x, y - 35, { steps: 5 });
  await page.mouse.up();
  const field = page.getByLabel("Minimum differential success rate");
  const target = Number(await field.inputValue());
  expect(target).toBeGreaterThan(0.25);
  await expect(page.locator("#trend svg")).toContainText("Target ≥ " + target.toFixed(3));
  await page.reload();
  await expect(field).toHaveValue(String(target));
});

test("touch dragging the target grip changes the success percentage @narrow", async ({ page, isMobile }) => {
  test.skip(!isMobile, "Touch gesture on the mobile browser profile");
  await openApp(page, "#section=range");
  const line = page.getByRole("slider", { name: "Plot target" });
  const grip = line.locator("span");
  await grip.scrollIntoViewIfNeeded();
  const box = (await grip.boundingBox())!;
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  const browser = await page.context().newCDPSession(page);
  await browser.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] });
  for (const dy of [5, 15, 25, 35]) {
    await browser.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x, y: y + dy }] });
  }
  await browser.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await browser.detach();
  expect(Number(await page.getByLabel("Minimum success rate").inputValue())).toBeLessThan(50);
});

test("navigation drawer collapses to icon rail on desktop and slides as overlay on mobile @narrow", async ({ page, isMobile }) => {
  await openApp(page, "#section=range&mode=overview");
  const toggle = page.getByRole("banner").getByRole("button", { name: /navigation menu/i });
  const drawer = page.locator("#nav-drawer");

  if (isMobile) {
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(drawer).toBeHidden();
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(drawer).toBeVisible();
  } else {
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(drawer).toBeVisible();
    const expandedBox = (await drawer.boundingBox())!;
    expect(expandedBox.width).toBeGreaterThanOrEqual(240);

    // Collapsing on desktop shrinks to the icon rail instead of hiding completely.
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(drawer).toBeVisible();
    await expect(drawer).toHaveClass(/collapsed/);
    await expect.poll(async () => (await drawer.boundingBox())!.width).toBeLessThanOrEqual(70);
    await expect(drawer.getByRole("tab")).toHaveCount(7);
    await expect(drawer.getByRole("tab", { name: "Compare decay" })).toHaveAttribute("title", "Compare decay");

    // Collapsed icon buttons stay interactive.
    await drawer.getByRole("tab", { name: "Compare decay" }).click();
    await expect(page).toHaveURL(/section=decay/);
    await drawer.getByRole("tab", { name: "Operating range" }).click();
    await expect(page).toHaveURL(/section=range/);

    // Expanding restores the full labeled drawer.
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(drawer).not.toHaveClass(/collapsed/);
    await expect.poll(async () => (await drawer.boundingBox())!.width).toBeGreaterThanOrEqual(240);
  }

  const navigation = page.getByRole("tablist", { name: "Experiment sections" });
  await expect(navigation).toHaveAttribute("aria-orientation", "vertical");
  const tabs = navigation.getByRole("tab");
  await expect(tabs).toHaveText([
    "Findings", "Operating range", "Compare decay", "Footprint",
    "Model validation", "Model training", "Execution cost model",
  ]);
  await expect(tabs.nth(1)).toHaveAttribute("aria-selected", "true");
  await expect(tabs.first()).toHaveAccessibleDescription("Summary");
  await expect(tabs.nth(1)).toHaveAccessibleDescription("Experiment plots");
  await expect(tabs.nth(3)).toHaveAccessibleDescription("Prediction models");

  // All section links stack in a single vertical column.
  const boxes = await Promise.all(Array.from({ length: 7 }, (_, i) => tabs.nth(i).boundingBox()));
  for (let i = 1; i < boxes.length; i++) {
    expect(boxes[i]!.y).toBeGreaterThan(boxes[i - 1]!.y);
    expect(Math.abs(boxes[i]!.x - boxes[0]!.x)).toBeLessThanOrEqual(1);
  }

  const position = await navigation.boundingBox();
  if (isMobile) {
    await tabs.nth(2).click();
    await expect(drawer).toBeHidden();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await toggle.click();
    await expect(tabs.nth(2)).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
    await expect(toggle).toBeFocused();
    await toggle.click();
  } else {
    await expect(page.getByRole("switch", { name: "Show run details" })).not.toBeChecked();
    await tabs.nth(2).click();
    expect(await navigation.boundingBox()).toEqual(position);
  }

  await tabs.nth(2).press("ArrowDown");
  await expect(tabs.nth(3)).toBeFocused();
  await expect(page).toHaveURL(/section=footprint/);
  await tabs.nth(3).press("End");
  await expect(tabs.last()).toBeFocused();
  await expect(page).toHaveURL(/section=cost/);
  await tabs.last().press("Home");
  await expect(tabs.first()).toBeFocused();
  await expect(tabs.first()).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("region", { name: "Findings" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
});

test("execution cost label stays on one line without moving on selection", async ({ page }) => {
  await openApp(page);
  const toggle = page.getByRole("banner").getByRole("button", { name: /navigation menu/i });
  for (const width of [1280, 1024, 901, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(toggle).toHaveAttribute("aria-expanded", width >= 960 ? "true" : "false");
    await selectSection(page, "Model training");
    const navigation = await openNavigation(page);
    const cost = navigation.getByRole("tab", { name: "Execution cost model" });
    const before = await cost.boundingBox();
    await cost.click();
    const afterNav = await openNavigation(page);
    const activeCost = afterNav.getByRole("tab", { name: "Execution cost model" });
    await expect(activeCost).toHaveAttribute("aria-selected", "true");
    if (width >= 960) {
      expect(await activeCost.boundingBox()).toEqual(before);
    }
    await expect.poll(() => activeCost.evaluate(button => {
      const label = button.querySelector(".tab-label") ?? button;
      const range = document.createRange();
      range.selectNodeContents(label);
      const lines = range.getClientRects();
      const bounds = button.getBoundingClientRect();
      return lines.length === 1 && lines[0].left >= bounds.left && lines[0].right <= bounds.right &&
        bounds.left >= 0 && bounds.right <= innerWidth;
    }), { message: `Label fits at ${width}px` }).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
    if (width < 960) {
      await toggle.click();
      await expect(toggle).toHaveAttribute("aria-expanded", "false");
    }
  }
});

test("findings is the landing page and explains the result in plain terms @narrow", async ({ page }) => {
  const errors = await openApp(page);
  const panel = page.getByRole("region", { name: "Findings" });
  await expect(panel.getByRole("heading", { name: /before paying to run it/ })).toBeVisible();
  await expect(panel.getByRole("list", { name: "Prediction accuracy per chip" }).getByRole("listitem")).toHaveCount(3);
  await expect(panel.getByRole("row", { name: /One model per chip/ })).toContainText("Best");
  await expect(panel.getByText("H3 · One model works across providers")).toBeVisible();
  await expect(panel.getByText("Waiting for data")).toBeVisible();
  await panel.getByLabel("Quality measure").selectOption({ label: "Hellinger fidelity" });
  await expect(panel.getByText(/Hellinger fidelity: how close/)).toBeVisible();
  await panel.getByRole("button", { name: "Pre-registered test" }).click();
  const navigation = await openNavigation(page);
  await expect(navigation.getByRole("tab", { name: "Model validation", exact: true })).toHaveAttribute("aria-selected", "true");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
  expect(errors).toEqual([]);
});
