import { afterEach, expect, it, vi } from "vitest";
import { decayData } from "../../src/lib/data/load";

afterEach(() => vi.unstubAllGlobals());

function chipResponse(backend: string) {
  return Response.json({ schemaVersion: 1, backend, panels: {} });
}

it("shares in-flight reports and keeps a late response scoped to its original chip", async () => {
  vi.stubGlobal("document", { baseURI: "https://example.org/dashboard/" });
  let finish!: (response: Response) => void;
  const fetch = vi.fn()
    .mockReturnValueOnce(new Promise<Response>(resolve => { finish = resolve; }))
    .mockResolvedValueOnce(chipResponse("B"));
  vi.stubGlobal("fetch", fetch);

  const reportA = decayData.watch("first.json", "A");
  const oldView = vi.fn();
  const remaining = vi.fn();
  const leave = reportA.subscribe(oldView);
  const leaveOther = reportA.subscribe(remaining);
  expect(fetch).toHaveBeenCalledTimes(1);
  leave();

  const active = vi.fn();
  const leaveB = decayData.watch("second.json", "B").subscribe(active);
  await vi.waitFor(() => expect(active.mock.lastCall?.[0].data?.backend).toBe("B"));
  finish(chipResponse("A"));
  await vi.waitFor(() => expect(remaining.mock.lastCall?.[0].data?.backend).toBe("A"));
  expect(active.mock.lastCall?.[0].data.backend).toBe("B");
  expect(oldView).toHaveBeenCalledTimes(1);
  leaveB();
  leaveOther();

  const revisit = vi.fn();
  const done = reportA.subscribe(revisit);
  expect(revisit.mock.lastCall?.[0].data.backend).toBe("A");
  expect(fetch).toHaveBeenCalledTimes(2);
  done();
});

it("skips missing reports and retries a failed validation on the next visit", async () => {
  vi.stubGlobal("document", { baseURI: "https://example.org/" });
  const fetch = vi.fn().mockResolvedValueOnce(chipResponse("wrong chip")).mockResolvedValueOnce(chipResponse("C"));
  vi.stubGlobal("fetch", fetch);
  decayData.watch(undefined, "C").subscribe(() => {})();
  expect(fetch).not.toHaveBeenCalled();

  const report = decayData.watch("retry.json", "C");
  const values = vi.fn();
  const leave = report.subscribe(values);
  await vi.waitFor(() => expect(values.mock.lastCall?.[0].error).toBeInstanceOf(Error));
  leave();
  const done = report.subscribe(values);
  await vi.waitFor(() => expect(values.mock.lastCall?.[0].data?.backend).toBe("C"));
  expect(fetch).toHaveBeenCalledTimes(2);
  done();
});
