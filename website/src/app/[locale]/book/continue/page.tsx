import { redirect } from "next/navigation";
import { routing } from "@/i18n/routing";
import { customerPortalBookUrl } from "@/data/portal-links";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

function withQuery(base: string, searchParams: Record<string, string | string[] | undefined>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    if (value == null) continue;
    if (Array.isArray(value)) {
      for (const v of value) params.append(key, v);
    } else {
      params.set(key, value);
    }
  }
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

/** Legacy `/book/continue` — forward quote_id / session handoff to portal (C-13). */
export default async function BookContinueRedirectPage({ params, searchParams }: Props) {
  await params;
  const query = await searchParams;
  redirect(withQuery(customerPortalBookUrl, query));
}
