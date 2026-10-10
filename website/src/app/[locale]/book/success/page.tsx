import { Suspense } from "react";
import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import BookSuccess from "@/components/book/BookSuccess";
import { routing } from "@/i18n/routing";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export const metadata: Metadata = {
  title: "Booked | PorterChain",
  robots: { index: false, follow: false },
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

async function SuccessBody({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const q = await searchParams;
  const quoteId = Array.isArray(q.quote_id) ? q.quote_id[0] : q.quote_id;
  return (
    <SiteShell>
      <Container className="py-10 md:py-16">
        <BookSuccess quoteId={String(quoteId ?? "").slice(0, 64)} />
      </Container>
    </SiteShell>
  );
}

/** Stripe success return for guest (retail) checkout. */
export default function BookSuccessPage(props: Props) {
  return (
    <Suspense fallback={null}>
      <SuccessBody {...props} />
    </Suspense>
  );
}
