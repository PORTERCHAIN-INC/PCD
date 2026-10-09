import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { ArrowRight } from "lucide-react";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import { Link } from "@/i18n/navigation";
import CoreFaqList from "@/components/marketing/faq/CoreFaqList";
import ContactBar from "@/components/marketing/delivery/ContactBar";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

const COPY = {
  en: {
    meta: "FAQ: price, coverage, cut-off, Shopify, insurance | Porterchain",
    desc: "Ten straight answers: what a delivery costs, where and when we deliver, vehicles, Shopify, proof of delivery, insurance, payment and claims.",
    h1: "Questions, answered.",
    lead: "Ten things buyers ask before their first delivery. Short answers, each with the page that proves it.",
    guides: "Longer reads are in the guides",
  },
  fr: {
    meta: "FAQ : prix, couverture, heure limite, Shopify, assurance | Porterchain",
    desc: "Dix réponses directes : prix, zones et horaires, véhicules, Shopify, preuve de livraison, assurance, paiement et réclamations.",
    h1: "Vos questions, nos réponses.",
    lead: "Les dix questions posées avant une première livraison. Des réponses courtes, chacune avec la page qui le prouve.",
    guides: "Les guides vont plus loin",
  },
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const c = COPY[locale === "fr" ? "fr" : "en"];
  return buildPageMetadata(locale, "faq", c.meta, c.desc);
}

/** The single FAQ (Oct 2026). Former /faq/{cluster} pages 301 here or to their topic page. */
export default async function FaqPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const c = COPY[locale === "fr" ? "fr" : "en"];
  return (
    <CorporateShell>
      <section className="bg-white">
        <Container size="narrow" className="pb-12 pt-[calc(var(--nav-height)+3rem)] sm:pb-16">
          <h1 className="text-4xl font-bold tracking-tight text-primary sm:text-5xl">{c.h1}</h1>
          <p className="mt-3 max-w-2xl text-lg text-muted">{c.lead}</p>
          <div className="mt-10">
            <CoreFaqList locale={locale} grouped filter />
          </div>
          <Link
            href="/guides"
            className="mt-10 inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-secondary underline-offset-4 hover:underline"
          >
            {c.guides}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </Container>
      </section>
      <ContactBar />
    </CorporateShell>
  );
}
