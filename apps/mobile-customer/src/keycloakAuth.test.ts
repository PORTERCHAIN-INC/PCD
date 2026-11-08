import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import {
  authorizeUrl,
  endpoints,
  authErrorCopy,
  exchangeCode,
  googleNativeConfig,
  hostedSignIn,
  identityFromToken,
  idpEnabled,
  keycloakConfig,
  needsRefresh,
  parseRedirect,
  REDIRECT_URI,
  refreshTokens,
} from "./auth/keycloak";

const kc = {
  url: "https://auth.porterchain.com",
  realm: "porterchain",
  clientId: "pc-customer-app",
};
const ok = (body: unknown) =>
  vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => body });

describe("L36 Keycloak mobile auth", () => {
  it("defaults to the production realm and app client; dev without URL means dev auth", () => {
    expect(keycloakConfig({})).toEqual(kc);
    expect(keycloakConfig({}, true)).toBeNull();
    expect(keycloakConfig({ EXPO_PUBLIC_KEYCLOAK_URL: "http://10.0.2.2:18180/" }, true)?.url).toBe(
      "http://10.0.2.2:18180"
    );
    expect(REDIRECT_URI).toBe("porterchain-customer://auth");
  });

  it("authorize URL uses PKCE S256, no implicit flow, idp hint for Apple/Google", () => {
    const u = new URL(
      authorizeUrl(kc, {
        redirectUri: REDIRECT_URI,
        codeChallenge: "ch",
        state: "st",
        nonce: "n",
        idpHint: "apple",
      })
    );
    expect(u.origin + u.pathname).toBe(endpoints(kc).authorize);
    expect(u.searchParams.get("response_type")).toBe("code");
    expect(u.searchParams.get("code_challenge_method")).toBe("S256");
    expect(u.searchParams.get("kc_idp_hint")).toBe("apple");
    const reg = new URL(
      authorizeUrl(kc, {
        redirectUri: REDIRECT_URI,
        codeChallenge: "c",
        state: "s",
        nonce: "n",
        register: true,
      })
    );
    expect(reg.searchParams.get("prompt")).toBe("create");
  });

  it("the login the app starts is website-style PKCE, not token exchange or an Apple hint", async () => {
    const plan = hostedSignIn(false);
    expect(plan).toEqual({ fresh: true });
    const u = new URL(
      authorizeUrl(kc, {
        redirectUri: REDIRECT_URI,
        codeChallenge: "c",
        state: "s",
        nonce: "n",
        ...plan,
      })
    );
    expect(u.searchParams.get("response_type")).toBe("code");
    expect(u.searchParams.get("code_challenge_method")).toBe("S256");
    expect(u.searchParams.get("prompt")).toBe("login");
    expect(u.searchParams.get("kc_idp_hint")).toBeNull();
    expect(u.searchParams.get("client_id")).toBe("pc-customer-app");
    const created = new URL(
      authorizeUrl(kc, {
        redirectUri: REDIRECT_URI,
        codeChallenge: "c",
        state: "s",
        nonce: "n",
        ...hostedSignIn(true),
      })
    );
    expect(created.searchParams.get("prompt")).toBe("create");
    expect(created.searchParams.get("kc_idp_hint")).toBeNull();
    expect(authErrorCopy("invalid_request")).not.toMatch(/connection/i);
    const nativeSrc = readFileSync(new URL("./auth/keycloakNative.ts", import.meta.url), "utf8");
    expect(nativeSrc).not.toContain("subject_issuer");
    expect(nativeSrc).not.toContain("nativeSignIn");
    expect(nativeSrc).not.toContain("token-exchange");
  });

  it("redirect parsing checks state", () => {
    expect(parseRedirect("porterchain-customer://auth?code=abc&state=s1", "s1")).toEqual({
      code: "abc",
    });
    expect(parseRedirect("porterchain-customer://auth?code=abc&state=x", "s1")).toEqual({
      error: "state_mismatch",
    });
    expect(parseRedirect("porterchain-customer://auth?error=access_denied", "s1")).toEqual({
      error: "access_denied",
    });
  });

  it("A-APR-01: code exchange sends verifier, stores tokens (reviewer = same Keycloak password login)", async () => {
    const f = ok({ access_token: "a", refresh_token: "r", id_token: "i", expires_in: 300 });
    const t = await exchangeCode(
      f,
      kc,
      { code: "c", codeVerifier: "v", redirectUri: REDIRECT_URI },
      1000
    );
    expect(t).toEqual({ accessToken: "a", refreshToken: "r", idToken: "i", expiresAt: 301000 });
    const body = new URLSearchParams(f.mock.calls[0][1].body);
    expect(body.get("grant_type")).toBe("authorization_code");
    expect(body.get("code_verifier")).toBe("v");
    expect(f.mock.calls[0][0]).toBe(endpoints(kc).token);
  });

  it("refresh keeps the old refresh token when none is returned; errors surface", async () => {
    const t = await refreshTokens(ok({ access_token: "b", expires_in: 60 }), kc, {
      accessToken: "a",
      refreshToken: "r",
      idToken: null,
      expiresAt: 0,
    });
    expect(t.refreshToken).toBe("r");
    const bad = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: "invalid_grant" }),
    });
    await expect(refreshTokens(bad, kc, { ...t })).rejects.toThrow("invalid_grant");
    expect(needsRefresh({ ...t, expiresAt: Date.now() + 10_000 })).toBe(true);
    expect(needsRefresh({ ...t, expiresAt: Date.now() + 120_000 })).toBe(false);
  });

  it("Apple and Google both on by default (same size, 4.8); native Google needs web client id", () => {
    expect(idpEnabled("apple", {})).toBe(true);
    expect(idpEnabled("google", { EXPO_PUBLIC_GOOGLE_SIGN_IN_ENABLED: "false" })).toBe(false);
    expect(googleNativeConfig({})).toBeNull();
    expect(googleNativeConfig({ EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID: "w" })).toEqual({
      webClientId: "w",
    });
  });

  it("reads sub/email from the access token for display", () => {
    const payload = btoa(JSON.stringify({ sub: "kc-1", email: "a@b.c" })).replace(/=+$/, "");
    expect(identityFromToken(`h.${payload}.s`)).toEqual({ userId: "kc-1", email: "a@b.c" });
    expect(identityFromToken("garbage")).toEqual({ userId: null, email: null });
  });
});
