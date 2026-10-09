import { redirect } from "next/navigation";

const HANDOFF_KEYS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_term",
  "utm_content",
  "from",
  "pc_vid",
];

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  // Keep the website hand-off (UTM / visitor id) so signup attribution survives the redirect.
  const params = await searchParams;
  const qs = new URLSearchParams();
  for (const key of HANDOFF_KEYS) {
    const value = params[key];
    if (typeof value === "string" && value) qs.set(key, value);
  }
  redirect(qs.size ? `/dashboard?${qs.toString()}` : "/dashboard");
}
