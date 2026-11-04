import { auth } from "@porterchain/auth/oidc/next";

/** Server-side: prefer the in-cluster API address (the public URL may not be reachable from the container). */
function apiBase(): string {
  return (
    process.env.PORTERCHAIN_API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ||
    "http://localhost:8001"
  ).replace(/\/$/, "");
}

/** Same bearer the admin BFF attaches: the Keycloak `pc-admin` access token. */
export async function staffAuthorization(): Promise<string | null> {
  const token = await (await auth()).getToken();
  return token ? `Bearer ${token}` : null;
}

export async function adminServerFetch<T>(path: string): Promise<T | null> {
  const authorization = await staffAuthorization();
  if (!authorization) return null;
  const target = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  try {
    const res = await fetch(target, {
      headers: { Authorization: authorization, Accept: "application/json" },
      cache: "no-store",
      // Layout prefetch is best-effort: never hold the page for it.
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
