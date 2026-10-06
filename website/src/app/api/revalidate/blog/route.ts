import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse } from "next/server";
import { pingIndexNow } from "@/lib/marketing/indexnow";
import { publicEnv } from "@/lib/env";

function authorize(req: Request): boolean {
  const secret = (process.env.WEBSITE_REVALIDATE_SECRET ?? "").trim();
  if (!secret) return false;
  const header = (req.headers.get("authorization") ?? "").trim();
  if (header === `Bearer ${secret}`) return true;
  const alt = (req.headers.get("x-revalidate-secret") ?? "").trim();
  return alt === secret;
}

type Body = {
  locale?: string;
  slug?: string;
  tags?: string[];
  paths?: string[];
};

/**
 * On-demand blog revalidation — called by the API after admin publish/update/delete.
 * Auth: Bearer WEBSITE_REVALIDATE_SECRET (or X-Revalidate-Secret).
 */
export async function POST(req: Request) {
  if (!authorize(req)) {
    const configured = Boolean((process.env.WEBSITE_REVALIDATE_SECRET ?? "").trim());
    return NextResponse.json(
      { ok: false, error: configured ? "unauthorized" : "revalidate_secret_unset" },
      { status: configured ? 401 : 501 }
    );
  }

  let body: Body = {};
  try {
    body = (await req.json()) as Body;
  } catch {
    body = {};
  }

  const locale = typeof body.locale === "string" ? body.locale.trim().toLowerCase() : "";
  const slug = typeof body.slug === "string" ? body.slug.trim().toLowerCase() : "";

  const tags = new Set<string>(["blog"]);
  if (locale) tags.add(`blog:${locale}`);
  if (Array.isArray(body.tags)) {
    for (const t of body.tags) {
      if (typeof t === "string" && t.trim()) tags.add(t.trim());
    }
  }
  for (const tag of tags) {
    revalidateTag(tag, { expire: 0 });
  }

  const paths = new Set<string>();
  if (locale) {
    paths.add(`/${locale}/blog`);
    if (slug) paths.add(`/${locale}/blog/${slug}`);
  } else {
    paths.add("/en/blog");
    paths.add("/fr/blog");
  }
  if (Array.isArray(body.paths)) {
    for (const p of body.paths) {
      if (typeof p === "string" && p.startsWith("/")) paths.add(p);
    }
  }
  for (const path of paths) {
    revalidatePath(path);
  }

  const site = publicEnv.siteUrl.replace(/\/$/, "");
  const indexUrls = [...paths].map((p) => `${site}${p}`);
  const indexNow = await pingIndexNow(indexUrls);

  return NextResponse.json({
    ok: true,
    tags: [...tags],
    paths: [...paths],
    indexNow,
  });
}
