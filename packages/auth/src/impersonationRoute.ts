/**
 * Shared `/api/auth/impersonation` route handlers (customer, driver and merchant portals).
 * Establishes / clears the HttpOnly impersonation cookie used by the portal BFFs.
 * Uses the Web Response API so this package does not depend on `next`.
 */
import { PC_IMP_COOKIE } from "./impersonation";

const API_BASE = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
  /\/$/,
  ""
);

function setCookie(token: string, maxAge: number): string {
  const parts = [
    `${PC_IMP_COOKIE}=${token}`,
    "Path=/",
    `Max-Age=${maxAge}`,
    "HttpOnly",
    "SameSite=Lax",
  ];
  if (process.env.NODE_ENV === "production") parts.push("Secure");
  return parts.join("; ");
}

const CLEAR_COOKIE = `${PC_IMP_COOKIE}=; Path=/; Max-Age=0; HttpOnly`;

function json(body: unknown, status = 200, setCookie?: string): Response {
  const headers = new Headers({ "content-type": "application/json" });
  if (setCookie) headers.append("set-cookie", setCookie);
  return new Response(JSON.stringify(body), { status, headers });
}

export async function POST(request: Request): Promise<Response> {
  const body = (await request.json().catch(() => ({}))) as { token?: string };
  const token = (body.token || "").trim();
  if (!token.startsWith("pc_imp_")) {
    return json({ detail: "invalid_impersonation_token" }, 400);
  }
  const peek = await fetch(`${API_BASE}/v1/auth/impersonation/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!peek.ok) {
    return json({ detail: "impersonation_expired" }, 401);
  }
  const data = (await peek.json()) as Record<string, unknown>;
  const maxAge = Math.max(60, Number(data.seconds_remaining) || 900);
  return json({ ok: true, ...data }, 200, setCookie(token, maxAge));
}

export async function GET(): Promise<Response> {
  return json({ ok: true });
}

export async function DELETE(): Promise<Response> {
  return json({ ok: true }, 200, CLEAR_COOKIE);
}
