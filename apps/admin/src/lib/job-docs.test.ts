import { describe, expect, it, vi } from "vitest";
import { jobDocsClient, missingDocs, normaliseInstruction } from "./job-docs";

describe("job docs client", () => {
  it("calls the right paths", async () => {
    const f = vi.fn().mockResolvedValue({});
    const c = jobDocsClient(f as never, "/v1/admin/jobs");
    await c.docs("batches", "b1");
    await c.edit("i1", { delete: true });
    expect(f.mock.calls[0][0]).toBe("/v1/admin/jobs/batches/b1/pickup-docs");
    expect(f.mock.calls[1]).toEqual([
      "/v1/admin/jobs/instructions/i1",
      { method: "PATCH", body: '{"delete":true}' },
    ]);
  });
  it("hides business notes from drivers and forces must_read visible", () => {
    expect(
      normaliseInstruction({ text: " rate $5 ", business: true, visibility: ["driver", "admin"] })
        .visibility
    ).toEqual(["admin"]);
    expect(
      normaliseInstruction({ text: "gate 4", priority: "must_read", visibility: ["admin"] })
        .visibility
    ).toContain("driver");
    expect(
      missingDocs([
        { id: "1", doc_type: "bol", status: "missing" },
        { id: "2", doc_type: "x", status: "captured" },
      ])
    ).toEqual(["bol"]);
  });
});
