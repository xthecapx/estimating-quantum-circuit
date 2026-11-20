import type { StoreApi } from "zustand/vanilla";
import type { Readable } from "svelte/store";

/** Svelte subscribers receive the current value immediately, then future updates. */
export function asReadable<T>(store: StoreApi<T>): Readable<T> {
  return {
    subscribe(run) {
      const unsubscribe = store.subscribe(run);
      run(store.getState());
      return unsubscribe;
    },
  };
}
