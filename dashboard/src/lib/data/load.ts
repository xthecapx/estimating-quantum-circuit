import { createStore } from "zustand/vanilla";
import { readable, type Readable } from "svelte/store";
import { asReadable } from "../state/readable";
import { SCHEMA_VERSION, type CalibrationData, type IndexData } from "./types";
import type { CostSnapshot } from "../../views/cost/model";
import type { Snapshot as DecaySnapshot } from "../../views/decay/model";
import type { EstimationSnapshot } from "../../views/estimation/model";
import type { ProspectiveSnapshot } from "../../views/prospective/model";
import type { ComparisonSnapshot } from "../../views/findings/model";

type Result<T> = { data?: T; error?: Error };

function jsonExport<T extends { schemaVersion: number }>(
  valid: (data: T, scope: string) => boolean,
  version = 1,
) {
  function entry(name: string, scope: string) {
    const state = createStore<Result<T>>(() => ({}));
    let pending: Promise<T> | undefined;

    async function fetchData() {
      const response = await fetch(new URL(`data/${name}`, document.baseURI));
      if (!response.ok) throw new Error(`Could not load ${name} (HTTP ${response.status}).`);
      const data: T = await response.json();
      if (data?.schemaVersion !== version || !valid(data, scope)) {
        throw new Error(`Unexpected schema or scope for ${name}. Rebuild the dashboard.`);
      }
      return data;
    }

    function load(): Promise<T> {
      const { data } = state.getState();
      if (data) return Promise.resolve(data);
      if (!pending) {
        pending = fetchData().then(
          value => {
            pending = undefined;
            state.setState({ data: value }, true);
            return value;
          },
          reason => {
            pending = undefined;
            const error = reason instanceof Error ? reason : new Error(String(reason));
            state.setState({ error }, true);
            throw error;
          },
        );
        state.setState({}, true);
      }
      return pending;
    }

    const result = asReadable(state);
    return {
      load,
      subscribe(run: (value: Result<T>) => void) {
        // Subscribers receive failures through the store.
        void load().catch(() => {});
        return result.subscribe(run);
      },
    };
  }

  const entries = new Map<string, ReturnType<typeof entry>>();
  const empty = readable<Result<T>>({});
  function get(name: string, scope: string) {
    const key = JSON.stringify([name, scope]);
    let resource = entries.get(key);
    if (!resource) {
      resource = entry(name, scope);
      entries.set(key, resource);
    }
    return resource;
  }
  return {
    watch(name: string | undefined, scope = ""): Readable<Result<T>> {
      return name ? get(name, scope) : empty;
    },
    load(name: string) { return get(name, "").load(); },
  };
}

const index = jsonExport<IndexData>(data => Array.isArray(data.jobs) && !!data.refs, SCHEMA_VERSION);
const calibrations = jsonExport<CalibrationData>(data => !!data.calibrations && typeof data.calibrations === "object", SCHEMA_VERSION);
export const loadIndex = () => index.load("index.json");
export const loadCalibrations = () => calibrations.load("calibrations.json");

export const decayData = jsonExport<DecaySnapshot>((data, chip) => data.backend === chip && !!data.panels);
export const estimationData = jsonExport<EstimationSnapshot>((data, scope) => data.backend === scope && !!data.targets, 2);
export const comparisonData = jsonExport<ComparisonSnapshot>(data => Array.isArray(data.rows) && Array.isArray(data.points));
export const validationData = jsonExport<ProspectiveSnapshot>(data => !!data.scores && !!data.chips);
export const costData = jsonExport<CostSnapshot>(data => !!data.points && !!data.physicalTerms);
