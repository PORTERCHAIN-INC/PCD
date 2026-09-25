import type { Metadata } from "next";
import { getMessages, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { integrationsEducationSlug, guideSlug, capabilitySlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

type ChannelBlock = { title?: string; description?: string };

type IntegrationsMessages = {
  meta?: { title?: string; description?: string };
  hero?: { title?: string; subtitle?: string };
  intro?: { description?: string };
  readinessSectionTitle?: string;
  csv?: ChannelBlock;
  api?: ChannelBlock;
  edi?: ChannelBlock;
  manual?: ChannelBlock;
  email?: ChannelBlock;
  sms?: ChannelBlock;
  whatsapp?: ChannelBlock;
  webhooks?: ChannelBlock;
  cta?: { title?: string; description?: string; primary?: string; secondary?: string };
};

const CHANNEL_KEYS = [
  "csv",
  "api",
  "edi",
  "manual",
  "email",
  "sms",
  "whatsapp",
  "webhooks",
] as const;

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const messages = await getMessages({ locale });
  const m = (messages as { integrations?: IntegrationsMessages }).integrations?.meta;
  return buildPageMetadata(
    locale,
    "integrations",
    m?.title ?? "Integrations",
    m?.description ?? ""
  );
}

export default async function IntegrationsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;
  const messages = await getMessages({ locale });
  const page = (messages as { integrations?: IntegrationsMessages }).integrations;

  const sections = CHANNEL_KEYS.flatMap((key) => {
    const block = page?.[key];
    if (!block?.title || !block.description) return [];
    return [{ heading: block.title, body: block.description }];
  });

  const relatedLinks = [
    {
      href: integrationsEducationSlug(loc, "csv-delivery-uploads"),
      label: loc === "fr" ? "Guide CSV" : "CSV upload guide",
    },
    {
      href: integrationsEducationSlug(loc, "api-order-ingestion"),
      label: loc === "fr" ? "Guide API" : "API ingestion guide",
    },
    {
      href: integrationsEducationSlug(loc, "sms-status-notifications"),
      label: loc === "fr" ? "Notifications SMS" : "SMS status notifications",
    },
    {
      href: integrationsEducationSlug(loc, "email-status-notifications"),
      label: loc === "fr" ? "Notifications courriel" : "Email status notifications",
    },
    {
      href: integrationsEducationSlug(loc, "whatsapp-status-notifications"),
      label: loc === "fr" ? "Notifications WhatsApp" : "WhatsApp status notifications",
    },
    {
      href: integrationsEducationSlug(loc, "webhooks-delivery-events"),
      label: loc === "fr" ? "Webhooks et événements" : "Webhooks & delivery events",
    },
    {
      href: `/${loc}/developers`,
      label: loc === "fr" ? "Documentation développeurs" : "Developer docs",
    },
    {
      href: capabilitySlug(loc, "branded-tracking"),
      label: loc === "fr" ? "Suivi client" : "Customer tracking",
    },
    {
      href: guideSlug(loc, "what-is-a-transportation-capacity-network"),
      label: loc === "fr" ? "Réseau de capacité" : "Capacity network guide",
    },
  ];

  return (
    <CorporateShell>
      <ContentClusterView
        locale={loc}
        ctaSource="integrations"
        data={{
          title: page?.hero?.title ?? "Integrations",
          description: page?.meta?.description ?? page?.intro?.description ?? "",
          intro: page?.intro?.description ?? page?.hero?.subtitle ?? "",
          sections,
          relatedLinks,
        }}
      />
    </CorporateShell>
  );
}
