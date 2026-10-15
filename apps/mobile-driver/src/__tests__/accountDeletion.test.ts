import { describe, expect, it, vi } from "vitest";
import { ACCOUNT_DELETION_NOTE, requestAccountDeletion } from "../accountDeletion";

describe("in-app account deletion", () => {
  it("files a deletion request with a clear note and reports the SLA", async () => {
    const req = vi.fn().mockResolvedValue({ status: "received", reference: "T-9", sla_days: 30 });
    const r = await requestAccountDeletion(req);
    expect(req).toHaveBeenCalledWith("deletion", ACCOUNT_DELETION_NOTE);
    expect(r.body).toContain("Reference T-9");
    expect(r.body).toContain("30 days");
  });

  it("propagates failure so the UI can show an error", async () => {
    const req = vi.fn().mockRejectedValue(new Error("network_unavailable"));
    await expect(requestAccountDeletion(req)).rejects.toThrow("network_unavailable");
  });
});
