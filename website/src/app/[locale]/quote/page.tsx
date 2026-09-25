import { redirect } from "next/navigation";
import { routing, type Locale } from "@/i18n/routing";

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

/** Legacy `/quote` — money-loop surface; capacity quote path is Clerk sign-up. */
export default async function QuoteRedirectPage({ params, searchParams }: Props) {
  const { locale } = await params;
  const query = await searchParams;
  const loc = (
    routing.locales.includes(locale as Locale) ? locale : routing.defaultLocale
  ) as string;
  const base = `/${loc}/sign-up`;
  const merged: Record<string, string | string[] | undefined> = {
    intent: "quote",
    from: "quote",
    ...query,
  };
  redirect(withQuery(base, merged));
}
