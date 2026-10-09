import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Camera, MapPinned, UserRoundX } from "lucide-react";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import TrackLookupForm from "@/components/track/TrackLookupForm";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "track",
    "Track your delivery | Porterchain",
    "Look up shipment status and proof of delivery with your Porterchain tracking number."
  );
}

const FACTS = [
  { id: "live", Icon: MapPinned },
  { id: "proof", Icon: Camera },
  { id: "noAccount", Icon: UserRoundX },
] as const;

/** Tracking entry: no hero image — the input is the hero (and the LCP is text). */
export default async function TrackPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("booking.track");

  return (
    <CorporateShell>
      <section className="bg-gray-bg" aria-labelledby="track-heading">
        <Container className="flex min-h-[60vh] max-w-2xl flex-col justify-center py-20 sm:py-28">
          <h1
            id="track-heading"
            className="text-4xl font-bold tracking-tight text-primary sm:text-5xl"
          >
            {t("title")}
          </h1>
          <p className="mt-3 text-lg text-muted">{t("entryLead")}</p>
          <div className="mt-8">
            <TrackLookupForm />
          </div>
          <ul className="mt-8 grid gap-3 text-sm text-primary sm:grid-cols-3">
            {FACTS.map(({ id, Icon }) => (
              <li key={id} className="flex items-center gap-2">
                <Icon className="h-4 w-4 shrink-0 text-secondary" aria-hidden />
                {t(`facts.${id}`)}
              </li>
            ))}
          </ul>
        </Container>
      </section>
    </CorporateShell>
  );
}
