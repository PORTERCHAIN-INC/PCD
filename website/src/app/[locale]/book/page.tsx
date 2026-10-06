import { Suspense } from "react";
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

async function BookRedirect({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  redirect(withQuery(customerPortalBookUrl, query));
  return null;
}

/** Legacy `/book` — retail booking is customer portal only; forward quote_id handoff (C-13). */
export default async function BookRedirectPage({ params, searchParams }: Props) {
  await params;
  return (
    <Suspense fallback={null}>
      <BookRedirect searchParams={searchParams} />
    </Suspense>
  );
}
