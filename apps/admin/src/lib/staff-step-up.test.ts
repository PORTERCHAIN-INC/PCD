import { describe, expect, it } from "vitest";
import { isStaffStepUpRequired, stepUpUrl } from "@/lib/staff-step-up";
import { staffAccountNotice } from "@/lib/settings";

describe("staff step-up (Keycloak re-login)", () => {
  it("detects the API error code", () => {
    expect(isStaffStepUpRequired(new Error("staff_step_up_required"))).toBe(true);
    expect(isStaffStepUpRequired(new Error("forbidden"))).toBe(false);
  });
  it("forces prompt=login and returns to the page", () => {
    expect(stepUpUrl("/settings?section=users")).toBe(
      "/auth/login?prompt=login&return_to=%2Fsettings%3Fsection%3Dusers"
    );
  });
});

describe("staffAccountNotice", () => {
  const base = { admin_user_id: "a", email: "s@x.io", role: "admin" };
  it("reports each outcome", () => {
    expect(staffAccountNotice({ ...base, keycloak_provisioned: true, email_sent: true })).toBe(
      "Setup email sent to s@x.io."
    );
    expect(staffAccountNotice({ ...base, keycloak_provisioned: true, email_sent: false })).toMatch(
      /SMTP/
    );
    expect(staffAccountNotice({ ...base, keycloak_provisioned: false, email_sent: false })).toMatch(
      /not configured/
    );
  });
});
