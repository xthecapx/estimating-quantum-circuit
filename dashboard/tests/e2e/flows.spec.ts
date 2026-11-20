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

test("1 · inline axes and scope filters update the plot and open a histogram @narrow", async ({ page }) => {
  const errors = await openApp(page, "#section=range");
  await expect(page.locator("#plot-title")).toHaveText("Success rate by logical qubits");
  await page.getByLabel("Algorithm").selectOption({ label: "Grover" });
  const plot = page.getByRole("region", {name:"Operating range plot"});
  const y = plot.getByLabel("Y-axis");
  await expect(y.locator("option:checked")).toHaveText("Success rate: How often was the answer accepted?");
  expect(await y.locator("option").allTextContents()).toEqual(Array(7).fill(expect.stringMatching(/^.+: .+\?$/)));
  await y.selectOption({ label: "Differential Success Rate: Did accepted peaks stand out?" });
  await expect(page.locator("#plot-title")).toHaveText("Differential Success Rate by logical qubits");
  await expect(page.locator("#coverage")).toContainText("jobs");

  const periods = page.getByLabel("Periods (UTC)");
  await expect(periods.locator("option").first()).toHaveText("All periods");
  const before = await page.locator("#coverage").textContent();
  await periods.selectOption({ index: 1 });
  await expect(page.locator("#coverage")).not.toHaveText(before!);
  await plot.getByLabel("X-axis").selectOption({label:"Executed ISA depth"});
  await expect(page.locator("#plot-title")).toHaveText("Differential Success Rate by executed isa depth");
  await page.reload();
  await expect(y.locator("option:checked")).toContainText("Differential Success Rate:");
  await expect(plot.getByLabel("X-axis").locator("option:checked")).toHaveText("Executed ISA depth");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  await openFirstJob(page);
  await expect(page.locator("#hist svg")).toBeVisible();
  await page.getByRole("button", { name: "Operating range" }).click();
  await expect(page.locator("#plot-title")).toBeVisible();
  expect(errors).toEqual([]);
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
  const errors = await openApp(page, "#section=range");
  await page.getByRole("group", { name: "Experiment filters" }).getByRole("button", { name: "Chip calibration history" }).click();
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
  await page.getByLabel("Algorithm", {exact:true}).selectOption({label:"Grover"});
  await page.getByRole("tab", {name:"Compare decay"}).click();
  const panel = page.getByRole("region", {name:"Decay comparison"});
  await expect(panel.locator(".gap-chart")).toBeVisible();
  await expect(panel.locator(".panels svg")).toHaveCount(0);
  await expect(panel.getByText("Explore all algorithm pairs", {exact:false}).first()).toBeVisible();
  const resource = panel.getByLabel("Resource", {exact:true});
  const outcome = panel.getByLabel("Outcome", {exact:true});
  await expect(resource.locator("option:checked")).toHaveText("Logical operations · 4 pairs");
  await expect(outcome.locator("option:checked")).toHaveText("Differential success rate · 3 pairs");
  const counts = (await resource.locator("option").allTextContents()).map(text => Number(text.match(/· (\d+) pairs?$/)![1]));
  expect(counts).toEqual([...counts].sort((a, b) => b - a));
  await resource.selectOption({label:"Logical two-qubit gates · 2 pairs"});
  await outcome.selectOption({label:"Success rate · 1 pair"});
  await expect(panel.getByRole("heading", {name:"QFT and Phase estimation"})).toBeVisible();
  await expect(panel.getByText("Phase estimation contains an inverse QFT",{exact:true})).toBeVisible();
  const picker = panel.getByRole("combobox", {name:"Algorithm pair", exact:true});
  await expect(picker.locator("option:enabled")).toHaveText(["QFT / Phase estimation · 2/3 windows"]);
  await expect(panel.locator(".gap-chart li.similar")).toHaveCount(2);
  await expect(panel.locator(".gap-chart li strong")).toHaveText(["31.01 pp","2.25 pp","4.34 pp"]);
  await panel.getByText("Observed outcomes and fitted trends", {exact:true}).click();
  await expect(panel.locator(".panels article")).toHaveCount(3);
  await expect(panel.locator(".stat strong")).toHaveText("4.34 pp");
  await resource.selectOption({label:"Total logical qubits · 3 pairs"});
  await outcome.selectOption({label:"Success rate · 1 pair"});
  await expect(picker.locator("option:enabled")).toHaveText(["Bernstein–Vazirani / vTP · 2/3 windows"]);
  await expect(panel.getByText("Compared across algorithm families",{exact:true})).toBeVisible();
  await panel.locator(".matrix-section > summary").click();
  await panel.getByRole("button",{name:"Grover / Bernstein–Vazirani",exact:true}).first().click();
  await expect(panel.getByText("Two different oracle circuits",{exact:true})).toBeVisible();
  await expect(panel.getByRole("heading",{name:"Similar decline in 0 of 4 eligible windows"})).toBeVisible();
  await expect(picker).toHaveValue("");
  await page.reload();
  await expect(panel.getByRole("heading",{name:"Grover and Bernstein–Vazirani"})).toBeVisible();
  await panel.getByLabel("Outcome",{exact:true}).selectOption({label:"Hellinger fidelity · 2 pairs"});
  await picker.selectOption("QFT/PHASE-ESTIMATION");
  await page.reload();
  await expect(picker).toHaveValue("QFT/PHASE-ESTIMATION");
  await expect(panel.locator(".heading .note")).toContainText("Hellinger fidelity");
  await page.getByRole("tab",{name:"Operating range"}).click();
  await expect(page.getByLabel("Algorithm",{exact:true}).locator("option:checked")).toHaveText("Grover");
  expect(errors).toEqual([]);
});

test("empty decay selector keeps the matrix and explains missing coverage @narrow", async ({page}) => {
  const errors = await openApp(page, "#section=decay&b=ibm_kingston&resource=a.ComplexityMetrics.gate_based_metrics.two_qubit_count&outcome=success");
  const panel = page.getByRole("region", {name:"Decay comparison"});
  await expect(panel.getByRole("combobox", {name:"Algorithm pair", exact:true})).toBeDisabled();
  await expect(panel.getByRole("status")).toContainText("Choose another resource");
  await panel.locator(".matrix-section > summary").click();
  await panel.getByRole("button",{name:"QFT / Phase estimation",exact:true}).first().click();
  await expect(panel.getByRole("heading",{name:"Similar decline in 0 of 3 eligible windows"})).toBeVisible();
  await panel.getByText("Slopes and rank correlations by window").click();
  await expect(panel.locator(".fit-details tbody tr td:last-child")).toHaveText(["0.90","0.90","0.90"]);
  await panel.getByRole("button",{name:"Phase estimation / Shor",exact:true}).first().click();
  await expect(panel.getByRole("heading",{name:"Too few comparable windows"})).toBeVisible();
  await panel.getByText("Shared levels by window").click();
  await expect(panel.locator(".coverage li strong")).toHaveText(["0","0","0"]);
  await panel.getByLabel("Resource",{exact:true}).selectOption({label:"Total logical qubits · 5 pairs"});
  await panel.getByLabel("Outcome",{exact:true}).selectOption({label:"Success rate · 1 pair"});
  await expect(panel.getByRole("combobox", {name:"Algorithm pair", exact:true}).locator("option:checked")).toHaveText("Phase estimation / Shor · 3/3 windows");
  await expect(panel.getByText("Shor order finding uses the phase-estimation construction",{exact:true})).toBeVisible();
  await expect(panel.locator(".stat strong")).toHaveText("2.59 pp");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  expect(errors).toEqual([]);
});

test("footprint tab traces metric selection, subset scores and model results @narrow", async ({page}) => {
  const errors = await openApp(page);
  await page.getByRole("tab", {name:"Footprint", exact:true}).click();
  const panel = page.getByRole("region", {name:"Footprint selection experiment"});
  await panel.getByLabel("Target quality metric").selectOption({label:"Success Rate"});
  const selected = panel.getByRole("region", {name:"Selected footprint"});
  await expect(selected.getByRole("button")).toHaveCount(10);
  await expect(panel.getByRole("list", {name:"Footprint generation process"}).getByRole("listitem")).toHaveCount(3);
  const volume = selected.getByRole("button", {name:"Circuit volume",exact:true});
  await volume.click();
  await expect(volume).toHaveAttribute("aria-pressed", "true");
  await expect(selected.getByText(/Circuit width multiplied by depth/)).toBeVisible();
  await expect(panel.locator(".evidence details[open]")).toHaveCount(0);
  await panel.getByText("Why each metric was kept or left out", {exact:true}).click();
  const metrics = panel.getByRole("table", {name:"Metric selection evidence"});
  await expect(metrics.locator("tbody tr")).toHaveCount(11);
  await expect(metrics.getByText("Retained", {exact:true})).toHaveCount(10);
  await panel.getByText("How many metrics were enough?", {exact:true}).click();
  await expect(panel.getByRole("table", {name:"LightGBM footprint size experiment"}).getByRole("row", {name:/10 · Selected/})).toContainText("0.8323");
  await panel.getByText("How did the regressors perform?", {exact:true}).click();
  await expect(panel.getByRole("table", {name:"Circuit-only regressor performance"}).locator("tbody tr")).toHaveCount(8);
  await panel.getByText("Ranking formula and SHAP contributions").click();
  await expect(panel.getByRole("img", {name:"Mean absolute SHAP by circuit metric"}).locator("svg")).toBeVisible();
  await panel.getByLabel("Chip / Scope").selectOption({label:"IBM Fez (ibm_fez)"});
  await expect(selected.getByRole("button")).toHaveCount(8);
  await page.reload();
  await panel.getByText("Why each metric was kept or left out", {exact:true}).click();
  await expect(metrics.locator("tbody tr")).toHaveCount(15);
  await expect(panel.getByLabel("Target quality metric").locator("option:checked")).toHaveText("Success Rate");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  await page.getByRole("tab", {name:"Model training"}).click();
  await expect(page.getByLabel("Thesis view")).toBeVisible();
  expect(errors).toEqual([]);
});

test("direction compares column loss to row loss and preserves the question on reload @narrow", async ({page}) => {
  const errors = await openApp(page, "#section=decay&b=ibm_kingston&resource=a.num_qubits&outcome=success&pair=QFT%2FPHASE-ESTIMATION");
  const panel = page.getByRole("region", {name:"Decay comparison"});
  await panel.locator(".matrix-section > summary").click();
  await expect(panel.locator("#matrix-guide")).toContainText("Which algorithm pairs show similar changes");
  await panel.getByLabel("Matrix view").selectOption({label:"Direction"});
  await expect(panel.locator("#matrix-guide")).toContainText("larger fitted decrease in success rate");
  const forward = panel.getByRole("button", {name:/^QFT to PE:/});
  const reverse = panel.getByRole("button", {name:/^PE to QFT:/});
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
  await panel.getByLabel("Matrix view").selectOption({label:"Similarity"});
  await expect(panel.locator(".stat span")).toHaveText("Median gap in fitted change");
  expect(errors).toEqual([]);
});

test("regression explorer answers curve clicks and updates both axes @narrow", async ({ page }) => {
  const errors = await openApp(page);
  await page.getByRole("tab", { name: "Regression explorer" }).click();
  const panel = page.getByRole("region", { name: "Regression explorer" });
  const filters = panel.getByRole("group", { name: "Experiment filters" });
  for (const name of ["Chip", "Periods (UTC)", "Experiment group"]) {
    const field = filters.getByRole("combobox", { name, exact: true });
    await field.selectOption({ index: 1 });
    await expect(field).toHaveValue("1");
    await field.selectOption({ index: 0 });
  }
  await panel.getByLabel("Minimum success rate").fill("80");
  await panel.getByLabel("Algorithm").selectOption({ label: "Grover" });
  await expect(panel.getByRole("heading")).toHaveText("How many qubits can the circuit use while still returning a marked bitstring in at least 50% of shots?");
  await expect(panel.getByLabel("Minimum success rate")).toHaveValue("50");
  await panel.getByLabel("Minimum success rate").fill("");
  await panel.getByLabel("Y-axis").selectOption({ label: "Full TVD" });
  await expect(panel.getByRole("heading")).toHaveText("How many qubits can the circuit use before matching the ideal bitstring distribution requires moving more than 50% of the probability?");
  await panel.getByLabel("X-axis").selectOption({ label: "Executed ISA depth" });
  await expect(panel.getByRole("heading")).toHaveText("How deep can the circuit be before matching the ideal bitstring distribution requires moving more than 50% of the probability?");
  const svg = panel.locator("#regression-plot svg");
  const line = svg.locator('path[stroke="#087363"]').first();
  const point = await line.evaluate((path: SVGPathElement) => {
    const local = path.getPointAtLength(path.getTotalLength() * 0.55);
    const screen = local.matrixTransform(path.getScreenCTM()!);
    const rect = path.ownerSVGElement!.getBoundingClientRect();
    return { x: screen.x - rect.left, y: screen.y - rect.top };
  });
  await expect(svg.locator("text").filter({ hasText: /Full TVD\s+0\./ })).toHaveCount(1);
  const reading = panel.locator("#fit-reading");
  const before = await reading.innerText();
  await svg.click({ position: point });
  await expect(reading).not.toHaveText(before);
  await expect(reading).toContainText("ISA layers");
  await expect(reading).toContainText("probability mass");
  const clicked = await reading.innerText();
  await page.reload();
  await expect(reading).toHaveText(clicked);
  await panel.getByLabel("Maximum full tvd").fill("0.3");
  await expect(panel.getByRole("heading")).toHaveText("How deep can the circuit be before matching the ideal bitstring distribution requires moving more than 30% of the probability?");
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
  const slider = panel.getByRole("slider", { name: "Selected point on fitted curve" });
  await expect(panel.locator('input[type="range"]')).toHaveCount(0);
  await slider.focus();
  await slider.press("Home");
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
  await expect(page.locator(".plot-caption")).toContainText("Target ≥ 55.5%");
});

test("each tab restores its own target and axes through navigation and reload", async ({ page, context }) => {
  const errors = await openApp(page, "#section=range");
  const range = page.getByRole("tab", { name: "Operating range" });
  const regression = page.getByRole("tab", { name: "Regression explorer" });
  const minimum = page.getByRole("spinbutton", { name: "Minimum success rate" });
  const fitted = page.getByRole("spinbutton", { name: "Minimum success rate (%)", exact: true });
  const x = page.getByLabel("X-axis");

  await minimum.fill("73");
  await regression.click();
  await expect(fitted).toHaveValue("50");
  await fitted.fill("31");
  await x.selectOption({ label: "Executed ISA depth" });
  await expect(page).toHaveURL(/section=regression.*t=0\.31/);
  const sharedUrl = page.url();

  await page.goBack();
  await expect(range).toHaveAttribute("aria-selected", "true");
  await expect(minimum).toHaveValue("73");
  await expect(x.locator("option:checked")).toHaveText("Logical qubits");
  await page.goForward();
  await expect(fitted).toHaveValue("31");
  await expect(x.locator("option:checked")).toHaveText("Executed ISA depth");

  await range.click();
  await minimum.fill("0");
  await regression.click();
  await expect(fitted).toHaveValue("31");
  await fitted.fill("");
  await expect(page).toHaveURL(/t=none/);
  await page.goBack();
  await expect(minimum).toHaveValue("0");
  await page.reload();
  await expect(minimum).toHaveValue("0");
  await regression.click();
  await expect(fitted).toHaveValue("");
  await expect(x.locator("option:checked")).toHaveText("Executed ISA depth");

  const shared = await context.newPage();
  await shared.goto(sharedUrl);
  await expect(shared.getByRole("spinbutton", { name: "Minimum success rate (%)", exact: true })).toHaveValue("31");
  await shared.getByRole("tab", { name: "Operating range" }).click();
  await expect(shared.getByRole("spinbutton", { name: "Minimum success rate" })).toHaveValue("50");
  expect(errors).toEqual([]);
});

test("report tabs share the pooled export and load other reports on demand", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (path.includes("/data/")) requests.push(path.split("/").pop()!);
  });
  const errors = await openApp(page);
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
  for (const tab of ["Operating range", "Regression explorer"]) {
    await page.getByRole("tab", { name: tab }).click();
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

test("navigation groups plots and models in keyboard order @narrow", async ({ page }) => {
  await openApp(page);
  const navigation = page.getByRole("tablist", { name: "Experiment sections" });
  const tabs = navigation.getByRole("tab");
  await expect(tabs).toHaveText([
    "Regression explorer", "Operating range", "Compare decay", "Footprint",
    "Model validation", "Model training", "Execution cost model",
  ]);
  await expect(tabs.first()).toHaveAttribute("aria-selected", "true");
  await expect(tabs.first()).toHaveAccessibleDescription("Experiment plots");
  await expect(tabs.nth(3)).toHaveAccessibleDescription("AI models");
  const position = await navigation.boundingBox();
  await tabs.nth(1).click();
  await expect(page.getByRole("region", { name: "Operating range plot" })).toBeVisible();
  expect(await navigation.boundingBox()).toEqual(position);
  await tabs.nth(2).click();
  expect(await navigation.boundingBox()).toEqual(position);
  await tabs.nth(2).press("ArrowRight");
  await expect(tabs.nth(3)).toBeFocused();
  await expect(page).toHaveURL(/section=footprint/);
  await tabs.nth(3).press("End");
  await expect(tabs.last()).toBeFocused();
  await expect(page).toHaveURL(/section=cost/);
  await tabs.last().press("Home");
  await expect(tabs.first()).toBeFocused();
  await expect(tabs.first()).toHaveAttribute("aria-selected", "true");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
});

test("execution cost label stays on one line without moving on selection", async ({ page }) => {
  await openApp(page);
  const cost = page.getByRole("tab", { name: "Execution cost model" });
  const training = page.getByRole("tab", { name: "Model training" });
  for (const width of [1280, 1024, 901, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await training.click();
    const before = await cost.boundingBox();
    await cost.click();
    await expect(cost).toHaveAttribute("aria-selected", "true");
    expect(await cost.boundingBox()).toEqual(before);
    const fits = await cost.evaluate(button => {
      const range = document.createRange();
      range.selectNodeContents(button);
      const lines = range.getClientRects();
      const bounds = button.getBoundingClientRect();
      return lines.length === 1 && lines[0].left >= bounds.left && lines[0].right <= bounds.right &&
        bounds.left >= 0 && bounds.right <= innerWidth;
    });
    expect(fits, `Label fits at ${width}px`).toBe(true);
  }
});
