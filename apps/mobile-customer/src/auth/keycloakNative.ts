/** Native glue for Keycloak PKCE: random/sha256 via expo-crypto, browser via expo-web-browser,
 * tokens in the Keychain/Keystore via expo-secure-store. */
import * as Crypto from "expo-crypto";
import * as SecureStore from "expo-secure-store";
import * as WebBrowser from "expo-web-browser";
import {
  authorizeUrl,
  base64UrlFromBase64,
  exchangeCode,
  type IdpHint,
  type KeycloakConfig,
  parseRedirect,
  REDIRECT_URI,
  type Tokens,
} from "./keycloak";

const STORE_KEY = "pc_keycloak_tokens";

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
