/** Minimal WebAuthn helpers for staff IdP passkeys (no npm WebAuthn SDK). */

function b64urlToBuffer(b64url: string): ArrayBuffer {
  const pad = "=".repeat((4 - (b64url.length % 4)) % 4);
  const b64 = (b64url + pad).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

function bufferToB64url(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 1) bin += String.fromCharCode(bytes[i]!);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function publicKeyFromOptions(
  options: Record<string, unknown>
): PublicKeyCredentialCreationOptions | PublicKeyCredentialRequestOptions {
  const challenge = b64urlToBuffer(String(options.challenge));
  const next = { ...options, challenge } as Record<string, unknown>;
  if (Array.isArray(options.excludeCredentials)) {
    next.excludeCredentials = options.excludeCredentials.map((c: { id: string; type: string }) => ({
      ...c,
      id: b64urlToBuffer(c.id),
    }));
  }
  if (Array.isArray(options.allowCredentials)) {
    next.allowCredentials = options.allowCredentials.map((c: { id: string; type: string }) => ({
      ...c,
      id: b64urlToBuffer(c.id),
    }));
  }
  if (options.user && typeof options.user === "object") {
    const user = options.user as { id: string; name: string; displayName: string };
    next.user = { ...user, id: b64urlToBuffer(user.id) };
  }
  return next as unknown as PublicKeyCredentialCreationOptions;
}

export function credentialToJson(cred: PublicKeyCredential): Record<string, unknown> {
  const response = cred.response as
    AuthenticatorAttestationResponse | AuthenticatorAssertionResponse;
  const base: Record<string, unknown> = {
    id: cred.id,
    rawId: bufferToB64url(cred.rawId),
    type: cred.type,
    clientExtensionResults: cred.getClientExtensionResults?.() ?? {},
  };
  if ("attestationObject" in response) {
    base.response = {
      clientDataJSON: bufferToB64url(response.clientDataJSON),
      attestationObject: bufferToB64url(response.attestationObject),
      transports: response.getTransports?.() ?? [],
    };
  } else {
    base.response = {
      clientDataJSON: bufferToB64url(response.clientDataJSON),
      authenticatorData: bufferToB64url(response.authenticatorData),
      signature: bufferToB64url(response.signature),
      userHandle: response.userHandle ? bufferToB64url(response.userHandle) : null,
    };
  }
  return base;
}

export async function createPasskey(
  options: Record<string, unknown>
): Promise<PublicKeyCredential> {
  if (!window.PublicKeyCredential) {
    throw new Error("passkeys_unsupported");
  }
  const cred = await navigator.credentials.create({
    publicKey: publicKeyFromOptions(options) as PublicKeyCredentialCreationOptions,
  });
  if (!cred || !(cred instanceof PublicKeyCredential)) {
    throw new Error("passkey_create_cancelled");
  }
  return cred;
}

export async function getPasskey(options: Record<string, unknown>): Promise<PublicKeyCredential> {
  if (!window.PublicKeyCredential) {
    throw new Error("passkeys_unsupported");
  }
  const cred = await navigator.credentials.get({
    publicKey: publicKeyFromOptions(options) as PublicKeyCredentialRequestOptions,
  });
  if (!cred || !(cred instanceof PublicKeyCredential)) {
    throw new Error("passkey_get_cancelled");
  }
  return cred;
}

export function passkeysSupported(): boolean {
  return typeof window !== "undefined" && Boolean(window.PublicKeyCredential);
}
