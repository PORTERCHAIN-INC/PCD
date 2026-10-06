import { cookies } from "next/headers";

const COOKIE = "pc_staff_sid";

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
    /\/$/,
    ""
  );
}

/** Same bearer the admin BFF attaches from the HttpOnly staff cookie. */
export async function staffAuthorization(): Promise<string | null> {
  const sid = (await cookies()).get(COOKIE)?.value?.trim();
  if (!sid) return null;
  return `Bearer staff_sess_${sid}`;
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
