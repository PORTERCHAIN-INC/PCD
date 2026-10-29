import { auth } from "@porterchain/auth/oidc/next";

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
    /\/$/,
    ""
  );
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
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
