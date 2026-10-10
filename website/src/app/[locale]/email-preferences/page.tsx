import { Suspense } from "react";
import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import { routing } from "@/i18n/routing";
import EmailPreferencesView from "./preferences-view";

type Props = { params: Promise<{ locale: string }> };

export const metadata: Metadata = {
  title: "Email preferences | PorterChain",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

async function Body({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SiteShell>
      <Container className="py-10 md:py-16">
        <Suspense fallback={null}>
          <EmailPreferencesView />
        </Suspense>
      </Container>
    </SiteShell>
  );
}

/** Signed-link email preferences: CASL unsubscribe + consent, PIPEDA/GDPR deletion request. */
export default function EmailPreferencesPage(props: Props) {
  return (
    <Suspense fallback={null}>
      <Body {...props} />
    </Suspense>
  );
}
