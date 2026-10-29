import { describe, expect, it, vi } from "vitest";
import {
  appleAuthorizeUrl,
  appleSignInEnabled,
  keycloakConfig,
  passwordSignIn,
  reviewerLoginEnabled,
  validateCredentials,
} from "./auth/reviewerLogin";

describe("G21 reviewer login", () => {
  it("is off unless flagged", () => {
    expect(reviewerLoginEnabled({})).toBe(false);
    expect(reviewerLoginEnabled({ EXPO_PUBLIC_REVIEWER_LOGIN_ENABLED: "true" })).toBe(true);
  });

  it("A-APR-01: password-only success sets the session, no code step", async () => {
    const create = vi.fn().mockResolvedValue({ status: "complete", createdSessionId: "sess_1" });
    const setActive = vi.fn().mockResolvedValue(undefined);
    await passwordSignIn({ create }, setActive, " review@x.com ", "pw123456");
    expect(create).toHaveBeenCalledWith({ identifier: "review@x.com", password: "pw123456" });
    expect(setActive).toHaveBeenCalledWith({ session: "sess_1" });
  });

  it("A-APR-07: a code/2FA requirement errors instead of showing an OTP screen", async () => {
    const create = vi
      .fn()
      .mockResolvedValue({ status: "needs_second_factor", createdSessionId: null });
    await expect(passwordSignIn({ create }, vi.fn(), "r@x.com", "pw123456")).rejects.toThrow(
      "reviewer_needs_code"
    );
  });

  it("validates inputs", () => {
    expect(validateCredentials("bad", "pw123456")).toBeTruthy();
    expect(validateCredentials("r@x.com", "short")).toBeTruthy();
    expect(validateCredentials("r@x.com", "pw123456")).toBeNull();
  });

  it("A-APR-04: Apple stays hidden until flag + Keycloak are both set", () => {
    expect(appleSignInEnabled({ EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED: "true" })).toBe(false);
    const env = {
      EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED: "true",
      EXPO_PUBLIC_KEYCLOAK_URL: "https://id.porterchain.com/",
      EXPO_PUBLIC_KEYCLOAK_CLIENT_ID: "mobile",
    };
    expect(appleSignInEnabled(env)).toBe(true);
    const url = appleAuthorizeUrl(keycloakConfig(env)!, "porterchain://auth", "s");
    expect(url).toContain(
      "https://id.porterchain.com/realms/porterchain/protocol/openid-connect/auth?"
    );
    expect(url).toContain("kc_idp_hint=apple");
  });
});
