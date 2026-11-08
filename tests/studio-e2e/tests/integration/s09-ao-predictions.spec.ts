import { expect, test } from "@playwright/test";
import { ao, aoAsk, aoNodes, blockedUnlessAo } from "./ao";

// S9 — KumoRFM predictions. Opt-in: data leaves the network.

const kumoReason = () =>
  process.env.RUN_KUMO === "1" ? null : "RUN_KUMO != 1 (KumoRFM uploads data to a third party; opt-in only)";

test.describe("S9 predictions (KumoRFM)", () => {
  test("9.1 predictive question routes to kumo_predict", async () => {
    await blockedUnlessAo(kumoReason());
    const ev = await aoAsk(await ao(), "Which customers are most likely to place an invoice in the next 30 days?");
    expect(ev.find((x) => x.type === "error")).toBeUndefined();
    const nodes = aoNodes(ev);
    expect(nodes).toContain("prepare_prediction_graph");
    expect(nodes).toContain("kumo_predict");
  });

  test("9.2 descriptive question does not route to Kumo", async () => {
    await blockedUnlessAo(kumoReason());
    const ev = await aoAsk(await ao(), "What was revenue for Probe Widget PG in Pennsylvania in June 2015?");
    expect(aoNodes(ev)).not.toContain("kumo_predict");
  });

  test("9.4 persisted analyses are listed", async () => {
    await blockedUnlessAo(kumoReason());
    const r = await (await ao()).get("/api/pql-analyses");
    expect(r.status()).toBe(200);
  });
});
