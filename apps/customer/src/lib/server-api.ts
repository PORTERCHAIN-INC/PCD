import { auth } from "@clerk/nextjs/server";
import { cookies } from "next/headers";
import { clerkDevBypassEnabled } from "@porterchain/auth/devBypass";
import { PC_IMP_FLAG } from "@porterchain/auth/impersonation";

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
    /\/$/,
    ""
  );
}

async function customerBearer(): Promise<string | null> {
  const jar = await cookies();
  if (jar.get(PC_IMP_FLAG)?.value === "1") return null;
  if (clerkDevBypassEnabled()) return "dev";
  const { getToken, userId } = await auth();
  if (!userId) return null;
  return (await getToken()) ?? null;
}

export async function customerServerFetch<T>(path: string): Promise<T | null> {
  const token = await customerBearer();
  if (!token) return null;
  try {
    const res = await fetch(`${apiBase()}${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
        "X-Porterchain-Portal": "customer",
      },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
