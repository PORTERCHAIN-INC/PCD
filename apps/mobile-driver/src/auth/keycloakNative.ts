/** Native glue for Keycloak PKCE: random/sha256 via expo-crypto, browser via expo-web-browser,
 * tokens in the Keychain/Keystore via expo-secure-store. */
import { Platform } from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";
import * as Crypto from "expo-crypto";
import * as SecureStore from "expo-secure-store";
import * as WebBrowser from "expo-web-browser";
import {
  AUTH_TOKEN_STORE_KEY,
  authorizeUrl,
  base64UrlFromBase64,
  endSessionUrl,
  exchangeCode,
  exchangeIdpToken,
  googleNativeConfig,
  type IdpHint,
  type KeycloakConfig,
  nativeExchangeFallsBack,
  parseRedirect,
  REDIRECT_URI,
  type Tokens,
} from "./keycloak";

const STORE_KEY = AUTH_TOKEN_STORE_KEY;

function randomString(bytes = 32): string {
  const raw = Crypto.getRandomBytes(bytes);
  let bin = "";
  raw.forEach((b) => (bin += String.fromCharCode(b)));
  return base64UrlFromBase64(btoa(bin));
}

async function challengeFor(verifier: string): Promise<string> {
  const digest = await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, verifier, {
    encoding: Crypto.CryptoEncoding.BASE64,
  });
  return base64UrlFromBase64(digest);
}

export async function signInWithKeycloak(
  kc: KeycloakConfig,
  opts: { idpHint?: IdpHint; register?: boolean; fresh?: boolean } = {}
): Promise<Tokens> {
  const codeVerifier = randomString(48);
  const state = randomString(16);
  const url = authorizeUrl(kc, {
    redirectUri: REDIRECT_URI,
    codeChallenge: await challengeFor(codeVerifier),
    state,
    nonce: randomString(16),
    ...opts,
  });
  const result = await WebBrowser.openAuthSessionAsync(url, REDIRECT_URI, {
    preferEphemeralSession: false,
  });
  if (result.type !== "success") throw new Error(result.type);
  const parsed = parseRedirect(result.url, state);
  if ("error" in parsed) throw new Error(parsed.error);
  return exchangeCode(fetch as never, kc, {
    code: parsed.code,
    codeVerifier,
    redirectUri: REDIRECT_URI,
  });
}

export async function loadTokens(): Promise<Tokens | null> {
  const raw = await SecureStore.getItemAsync(STORE_KEY).catch(() => null);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Tokens;
  } catch {
    return null;
  }
}

export async function saveTokens(t: Tokens | null): Promise<void> {
  if (!t) await SecureStore.deleteItemAsync(STORE_KEY).catch(() => undefined);
  else await SecureStore.setItemAsync(STORE_KEY, JSON.stringify(t));
}

async function appleIdToken(): Promise<string | null> {
  if (Platform.OS !== "ios" || !(await AppleAuthentication.isAvailableAsync())) return null;
  const rawNonce = randomString(16);
  const cred = await AppleAuthentication.signInAsync({
    requestedScopes: [
      AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
      AppleAuthentication.AppleAuthenticationScope.EMAIL,
    ],
    nonce: await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, rawNonce),
  });
  return cred.identityToken ?? null;
}

async function googleIdToken(): Promise<string | null> {
  const cfg = googleNativeConfig();
  if (!cfg) return null;
  // Lazy: the native module is absent in Expo Go / web; fall back to the browser flow then.
  const mod = await import("@react-native-google-signin/google-signin").catch(() => null);
  if (!mod) return null;
  const { GoogleSignin } = mod;
  GoogleSignin.configure({
    webClientId: cfg.webClientId,
    iosClientId: cfg.iosClientId,
    offlineAccess: false,
  });
  if (Platform.OS === "android") await GoogleSignin.hasPlayServices();
  const res = await GoogleSignin.signIn();
  if (res.type !== "success") throw new Error("cancel");
  return res.data.idToken ?? null;
}

/**
 * Native Sign in with Apple (iOS) / Google, exchanged for Keycloak tokens. Returns null when the
 * native path is unavailable or the token endpoint rejects the exchange, so the caller opens the
 * authorization-code + PKCE browser flow instead. Cancel does not fall through.
 */
export async function nativeSignIn(kc: KeycloakConfig, hint: IdpHint): Promise<Tokens | null> {
  let idToken: string | null;
  try {
    idToken = hint === "apple" ? await appleIdToken() : await googleIdToken();
  } catch (err) {
    const code = (err as { code?: string })?.code;
    if (code === "ERR_REQUEST_CANCELED" || (err instanceof Error && err.message === "cancel")) {
      throw new Error("cancel");
    }
    return null;
  }
  if (!idToken) return null;
  try {
    return await exchangeIdpToken(fetch as never, kc, {
      subjectToken: idToken,
      subjectIssuer: hint,
    });
  } catch (err) {
    const code = err instanceof Error ? err.message : "";
    if (!nativeExchangeFallsBack(code)) throw err;
    return null;
  }
}

/**
 * Open Keycloak logout in the same (non-ephemeral) system browser session sign-in uses,
 * so a stuck cookie is cleared. Local jobs and proof photos are not touched here.
 */
export async function endBrowserSession(kc: KeycloakConfig, idToken: string | null): Promise<void> {
  const url = endSessionUrl(kc, REDIRECT_URI, idToken);
  await WebBrowser.openAuthSessionAsync(url, REDIRECT_URI, {
    preferEphemeralSession: false,
  }).catch(() => undefined);
}
