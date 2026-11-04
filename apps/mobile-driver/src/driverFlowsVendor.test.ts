import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { flowView } from "@porterchain/driver-flows";

const src = path.resolve(__dirname, "../../../packages/driver-flows/src");
const vend = path.resolve(__dirname, "../vendor/driver-flows/src");

describe("vendored @porterchain/driver-flows", () => {
  it.runIf(existsSync(src))(
    "matches packages/driver-flows (run scripts/sync-driver-flows.sh)",
    () => {
      for (const f of readdirSync(src).filter((n) => !n.endsWith(".test.ts"))) {
        expect(readFileSync(path.join(vend, f), "utf8")).toBe(
          readFileSync(path.join(src, f), "utf8")
        );
      }
    }
  );
  it("renders cards", () => {
    const v = flowView(
      {
        flow_id: "d",
        version: 1,
        steps: [{ id: "a", card: "signature", capture: ["signature"], block_if: ["no_signature"] }],
      },
      {},
      "en"
    );
    expect(v[0].blockers).toEqual(["Signature needed"]);
  });
});
