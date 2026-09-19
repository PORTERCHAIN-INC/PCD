/**
 * IndexNow helper — ping participating engines when URLs change.
 * No-op without INDEXNOW_KEY. Used by scripts / optional API route.
 */

import { publicEnv } from "@/lib/env";

export function getIndexNowKey(): string {
  return (process.env.INDEXNOW_KEY ?? "").trim();
}

export function indexNowKeyFileName(): string | null {
  const key = getIndexNowKey();
  return key ? `${key}.txt` : null;
}

export async function pingIndexNow(
  urls: string[]
): Promise<{ ok: boolean; status?: number; skipped?: string }> {
  const key = getIndexNowKey();
  if (!key) return { ok: false, skipped: "INDEXNOW_KEY unset" };
  if (urls.length === 0) return { ok: false, skipped: "no_urls" };

  const host = new URL(publicEnv.siteUrl).host;
  const body = {
    host,
    key,
    keyLocation: `${publicEnv.siteUrl}/api/marketing/indexnow-key`,
    urlList: urls.slice(0, 10_000),
  };

  const res = await fetch("https://api.indexnow.org/indexnow", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify(body),
  });
  return { ok: res.ok || res.status === 202, status: res.status };
}
