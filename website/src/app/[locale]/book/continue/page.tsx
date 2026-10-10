import { Suspense } from "react";
import { redirect } from "next/navigation";
import { routing } from "@/i18n/routing";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

async function ContinueRedirect({ params, searchParams }: Props) {
  const { locale } = await params;
  const q = await searchParams;
  const quoteId = Array.isArray(q.quote_id) ? q.quote_id[0] : q.quote_id;
  const qs = quoteId ? `?quote_id=${encodeURIComponent(String(quoteId).slice(0, 64))}` : "";
  redirect(`/${locale}/book${qs}`);
  return null;
}

/** Stripe cancel return: back to the same price on the guest booking page. */
export default function BookContinuePage(props: Props) {
  return (
    <Suspense fallback={null}>
      <ContinueRedirect {...props} />
    </Suspense>
  );
}
