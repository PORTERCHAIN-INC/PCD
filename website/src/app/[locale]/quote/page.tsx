import { Suspense } from "react";
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

async function QuoteRedirect({
  locale,
  searchParams,
}: {
  locale: string;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const loc = (
    routing.locales.includes(locale as Locale) ? locale : routing.defaultLocale
  ) as string;
  // Retail quotes are instant and need no account: go straight to guest booking.
  redirect(withQuery(`/${loc}/book`, query));
  return null;
}

/** Legacy `/quote` → guest express booking (`/book`), query preserved. */
export default async function QuoteRedirectPage({ params, searchParams }: Props) {
  const { locale } = await params;
  return (
    <Suspense fallback={null}>
      <QuoteRedirect locale={locale} searchParams={searchParams} />
    </Suspense>
  );
}
