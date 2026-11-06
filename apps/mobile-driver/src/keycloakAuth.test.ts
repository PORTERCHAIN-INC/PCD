import { describe, expect, it, vi } from "vitest";
import {
  AUTH_TOKEN_STORE_KEY,
  authErrorCopy,
  authResetDeletes,
  authorizeUrl,
  endSessionUrl,
  endpoints,
  exchangeCode,
  exchangeIdpToken,
  googleNativeConfig,
  identityFromToken,
  idpEnabled,
  keycloakConfig,
  browserSignInFresh,
  nativeExchangeFallsBack,
  needsRefresh,
  parseRedirect,
  PRESERVED_ON_AUTH_RESET,
  REDIRECT_URI,
  refreshTokens,
} from "./auth/keycloak";

const kc = {
  url: "https://auth.porterchain.com",
  realm: "porterchain",
  clientId: "pc-driver-app",
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
    expect(REDIRECT_URI).toBe("porterchain-driver://auth");
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
    const fresh = new URL(
      authorizeUrl(kc, {
        redirectUri: REDIRECT_URI,
        codeChallenge: "c",
        state: "s",
        nonce: "n",
        fresh: true,
      })
    );
    expect(fresh.searchParams.get("prompt")).toBe("login");
    expect(fresh.searchParams.get("response_type")).toBe("code");
    const inviteFresh = new URL(
      authorizeUrl(kc, {
        redirectUri: REDIRECT_URI,
        codeChallenge: "c",
        state: "s",
        nonce: "n",
        fresh: true,
        register: true,
      })
    );
    expect(inviteFresh.searchParams.get("prompt")).toBe("create");
  });

  it("reset logout URL is the public client end-session, and reset does not name business data", () => {
    const logout = new URL(endSessionUrl(kc, REDIRECT_URI));
    expect(logout.pathname).toBe("/realms/porterchain/protocol/openid-connect/logout");
    expect(logout.searchParams.get("client_id")).toBe("pc-driver-app");
    expect(logout.searchParams.get("post_logout_redirect_uri")).toBe(REDIRECT_URI);
    expect(logout.searchParams.has("id_token_hint")).toBe(false);
    expect(logout.searchParams.has("client_secret")).toBe(false);
    const hinted = new URL(endSessionUrl(kc, REDIRECT_URI, "fixture-id-token"));
    expect(hinted.searchParams.get("id_token_hint")).toBe("fixture-id-token");
    expect(authResetDeletes(AUTH_TOKEN_STORE_KEY)).toBe(true);
    for (const key of PRESERVED_ON_AUTH_RESET) {
      expect(authResetDeletes(key)).toBe(false);
    }
    expect(PRESERVED_ON_AUTH_RESET).toEqual(
      expect.arrayContaining([
        "porterchain_driver_offline_queue",
        "porterchain_driver_offline_rejected",
        "porterchain_driver_gps_buffer",
        "porterchain_driver_pod_key",
        "pcd.driver.rq.v1",
      ])
    );
  });

  it("redirect parsing checks state", () => {
    expect(parseRedirect("porterchain-driver://auth?code=abc&state=s1", "s1")).toEqual({
      code: "abc",
    });
    expect(parseRedirect("porterchain-driver://auth?code=abc&state=x", "s1")).toEqual({
      error: "state_mismatch",
    });
    expect(parseRedirect("porterchain-driver://auth?error=access_denied", "s1")).toEqual({
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

  it("standard token exchange rejection is invalid_request and falls back to the browser", async () => {
    const bad = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        error: "invalid_request",
        error_description:
          "Parameter 'subject_issuer' is not supported for standard token exchange",
      }),
    });
    await expect(
      exchangeIdpToken(bad, kc, { subjectToken: "not-a-real-token", subjectIssuer: "apple" })
    ).rejects.toThrow("invalid_request");
    expect(nativeExchangeFallsBack("invalid_request")).toBe(true);
    expect(nativeExchangeFallsBack("unsupported_grant_type")).toBe(true);
    expect(nativeExchangeFallsBack("cancel")).toBe(false);
    expect(nativeExchangeFallsBack("dismiss")).toBe(false);
    expect(nativeExchangeFallsBack("access_denied")).toBe(false);
    expect(browserSignInFresh(true, false)).toBe(true);
    expect(browserSignInFresh(false, true)).toBe(true);
    expect(browserSignInFresh(false, false)).toBe(false);
    expect(authErrorCopy("invalid_request")).not.toMatch(/connection/i);
    expect(authErrorCopy("cancel")).toMatch(/cancelled/i);
  });

  it("native Apple/Google id token is exchanged for Keycloak tokens", async () => {
    const f = ok({ access_token: "a", refresh_token: "r", expires_in: 60 });
    await exchangeIdpToken(f, kc, { subjectToken: "apple.jwt", subjectIssuer: "apple" });
    const body = new URLSearchParams(f.mock.calls[0][1].body);
    expect(body.get("grant_type")).toBe("urn:ietf:params:oauth:grant-type:token-exchange");
    expect(body.get("subject_issuer")).toBe("apple");
    expect(body.get("subject_token_type")).toBe("urn:ietf:params:oauth:token-type:id_token");
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
