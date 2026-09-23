import { allowDevAuth } from "./config";

export type SessionSnapshot = {
  ready: boolean;
  signedIn: boolean;
  getToken: () => Promise<string | null>;
  signOut: () => Promise<void>;
};

const idleSignOut = async () => undefined;

let snapshot: SessionSnapshot = {
  ready: true,
  signedIn: false,
  getToken: async () => null,
  signOut: idleSignOut,
};

const listeners = new Set<() => void>();

export function setSessionSnapshot(next: SessionSnapshot): void {
  snapshot = next;
  listeners.forEach((listen) => listen());
}

export function getSessionSnapshot(): SessionSnapshot {
  return snapshot;
}

export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export async function requireBearer(): Promise<string> {
  const token = await snapshot.getToken();
  if (token) return token;
  if (allowDevAuth()) return "dev";
  throw new Error("signed_out");
}

/** Wait for ClerkBridge to publish a live session after hosted / token-cache restore. */
export async function waitForSignedSession(timeoutMs = 5_000): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const current = getSessionSnapshot();
    if (current.signedIn) {
      const token = await current.getToken();
      if (token) return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  const last = getSessionSnapshot();
  if (!last.signedIn) return false;
  return Boolean(await last.getToken());
}

/** Clears local session view after Clerk/dev sign-out. */
export async function clearSession(): Promise<void> {
  // Dynamic import avoids session ↔ push ↔ api cycle.
  try {
    const { unregisterRememberedPush } = await import("./push");
    await unregisterRememberedPush();
  } catch {
    /* ignore */
  }
  await snapshot.signOut();
  setSessionSnapshot({
    ready: true,
    signedIn: false,
    getToken: async () => null,
    signOut: idleSignOut,
  });
}
