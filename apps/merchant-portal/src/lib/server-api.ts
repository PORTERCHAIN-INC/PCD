import { auth } from "@clerk/nextjs/server";
import { cookies } from "next/headers";
import { clerkDevBypassEnabled } from "@porterchain/auth/devBypass";
import { PC_IMP_FLAG } from "@porterchain/auth/impersonation";
import { MERCHANT_ID_COOKIE } from "@/lib/merchant-cookie";

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
    /\/$/,
    ""
  );
}

export async function merchantOrgId(): Promise<string | null> {
  const raw = (await cookies()).get(MERCHANT_ID_COOKIE)?.value?.trim();
  if (!raw) return null;
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

async function merchantBearer(): Promise<string | null> {
  const jar = await cookies();
  if (jar.get(PC_IMP_FLAG)?.value === "1") return null;
  if (clerkDevBypassEnabled()) return "dev";
  const { getToken, userId } = await auth();
  if (!userId) return null;
  return (await getToken()) ?? null;
}

export async function merchantServerFetch<T>(
  path: string,
  orgId?: string | null
): Promise<T | null> {
  const token = await merchantBearer();
  if (!token) return null;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    Accept: "application/json",
    "X-Porterchain-Portal": "merchant",
  };
  if (orgId) headers["X-Merchant-Id"] = orgId;
  try {
    const res = await fetch(`${apiBase()}${path}`, { headers, cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
