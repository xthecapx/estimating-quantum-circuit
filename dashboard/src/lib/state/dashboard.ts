import type { TabGroup } from "../ui/Tabs.svelte";
import { createStore } from "zustand/vanilla";
import { loadIndex } from "../data/load";
import type { IndexData } from "../data/types";
import { Explorer } from "./explorer.svelte";
import { asReadable } from "./readable";
import { formatHash, parseHash, type UrlState } from "./url";

export const sectionGroups: TabGroup[] = [
  {
    label: "Summary", icon: "experiment",
    tabs: [{ id: "findings", label: "Findings", icon: "experiment" }],
  },
  {
    label: "Experiment plots", icon: "compare",
    tabs: [
      { id: "range", label: "Operating range", icon: "compare" },
      { id: "decay", label: "Compare decay", icon: "decay" },
    ],
  },
  {
    label: "Prediction models", icon: "qubits",
    tabs: [
      { id: "footprint", label: "Footprint", icon: "qubits" },
      { id: "validation", label: "Model validation", icon: "validation" },
      { id: "estimation", label: "Model training", icon: "sliders" },
      { id: "cost", label: "Execution cost model", icon: "cost" },
    ],
  },
];
const tabs = sectionGroups.flatMap(group => group.tabs);

function choicesFromUrl(url: UrlState) {
  return {
    // A bare address opens the summary. A link without a recognised section but with
    // explorer settings (older shared links) still opens the operating range.
    section: tabs.find(tab => tab.id === url.section)?.id
      ?? (Object.keys(url).some(key => key !== "section") ? "range" : "findings"),
    decay: {
      matrix: url.matrix === "direction" ? "direction" : "similarity",
      pair: url.pair || "", resource: url.resource || "", outcome: url.outcome || "",
      scope: url.backend || "",
    },
    estimation: {
      scope: url.estScope || "pooled", target: url.estTarget || "",
      split: url.estSplit === "cv" ? "cv" : "holdout", view: url.estView || "h1",
    },
    prospective: {
      target: url.valTarget || "success", chip: url.valChip || "",
      regime: url.valRegime === "mixed_submit" ? "mixed_submit" : "circuit_only",
    },
    cost: {
      split: url.costSplit === "unseen_circuit" ? "unseen_circuit" : "new_run",
      circuit: url.costCircuit || "", shots: url.costShots || "1024", price: url.costPrice || "",
    },
  };
}

export type DashboardChoices = ReturnType<typeof choicesFromUrl>;
export type DecayChoices = DashboardChoices["decay"];
export type EstimationChoices = DashboardChoices["estimation"];
export type ProspectiveChoices = DashboardChoices["prospective"];
export type CostChoices = DashboardChoices["cost"];

interface DashboardState extends DashboardChoices {
  index?: IndexData;
  explorer?: Explorer;
  error?: string;
}

function activeRoute(state: DashboardState, current: Explorer): UrlState {
  const { section, decay, estimation, prospective, cost } = state;
  switch (section) {
    case "range":
      return { ...current.toUrl(), section };
    case "decay":
      return {
        section,
        backend: decay.resource ? (decay.scope || "all") : undefined,
        matrix: decay.matrix,
        pair: decay.pair,
        resource: decay.resource,
        outcome: decay.outcome,
      };
    case "estimation":
    case "footprint":
      return { section, estScope: estimation.scope, estTarget: estimation.target, estSplit: estimation.split, estView: estimation.view };
    case "validation":
      return { section, valTarget: prospective.target, valRegime: prospective.regime, valChip: prospective.chip };
    case "cost":
      return { section, costSplit: cost.split, costCircuit: cost.circuit, costShots: cost.shots, costPrice: cost.price };
    default:
      return { section };
  }
}

export function createDashboard() {
  const state = createStore<DashboardState>(() => choicesFromUrl({}));
  let sectionUrls: Record<string, string> = {};

  function restoreRoute(index = state.getState().index) {
    const url = parseHash(location.hash);
    state.setState({
      ...choicesFromUrl(url), index,
      explorer: index && new Explorer(index, url),
    });
  }

  function mount() {
    let mounted = true;
    sectionUrls = { ...history.state?.dashboardSections };
    const onHashChange = () => restoreRoute();
    onHashChange();
    window.addEventListener("hashchange", onHashChange);
    loadIndex().then(index => {
      if (mounted) restoreRoute(index);
    }).catch(reason => {
      if (!mounted) return;
      console.error(reason);
      state.setState({ error: "The experiment data could not be loaded. Build the dashboard (npm run build) and serve its dist/ directory over HTTP." });
    });
    return () => {
      mounted = false;
      window.removeEventListener("hashchange", onHashChange);
    };
  }

  function saveRoute(current: DashboardState) {
    if (!current.explorer) return;
    const hash = formatHash(activeRoute(current, current.explorer));
    sectionUrls[current.section] = hash;
    const saved = history.state?.dashboardSections;
    if (location.hash !== hash || Object.entries(sectionUrls).some(([key, value]) => saved?.[key] !== value)) {
      history.replaceState({ ...history.state, dashboardSections: sectionUrls }, "", hash);
    }
  }

  function selectSection(next: string) {
    const current = state.getState();
    if (next === current.section) return;
    saveRoute(current);
    const hash = sectionUrls[next] ?? formatHash({ section: next, mode: next === "range" ? "overview" : undefined });
    history.pushState({ ...history.state, dashboardSections: sectionUrls }, "", hash);
    restoreRoute();
  }

  return {
    ...asReadable(state), mount, saveRoute, selectSection,
    setChoices(choices: Partial<Omit<DashboardChoices, "section">>) {
      state.setState(choices);
    },
  };
}
