import { Suspense } from "react";
import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import ExpressBook from "@/components/book/ExpressBook";
import { routing } from "@/i18n/routing";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export const metadata: Metadata = {
  title: "Book a same-day delivery | PorterChain",
  description: "Price in seconds, pay with card, Apple Pay or Google Pay. No account needed.",
  robots: { index: false, follow: true },
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

function one(value: string | string[] | undefined): string | undefined {
  const v = Array.isArray(value) ? value[0] : value;
  return v ? String(v).slice(0, 600) : undefined;
}

async function BookBody({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const q = await searchParams;
  return (
    <SiteShell>
      <Container className="py-10 md:py-16">
        <ExpressBook
          initialPickup={one(q.pickup) ?? ""}
          initialDropoff={one(q.dropoff) ?? ""}
          initialVehicle={one(q.vehicle)}
          quoteId={one(q.quote_id)}
          againToken={one(q.again)}
        />
      </Container>
    </SiteShell>
  );
}

/** Guest express booking: no account, price first, Stripe Checkout (cards, Apple Pay, Google Pay). */
export default function BookPage(props: Props) {
  return (
    <Suspense
      fallback={
        <RouteLoading label="Loading booking">
          <PageSkeleton rows={4} />
        </RouteLoading>
      }
    >
      <BookBody {...props} />
    </Suspense>
  );
}
