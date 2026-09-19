"use client";

import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import LinkButton from "@/components/corporate/ui/LinkButton";
import FadeIn from "@/components/corporate/motion/FadeIn";
import { ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { Check } from "lucide-react";

interface PlatformBridgeSectionProps {
  /** Attribution source for `from=` query params (e.g. industry/construction-materials). */
  from: string;
}

export default function PlatformBridgeSection({ from }: PlatformBridgeSectionProps) {
  const t = useTranslations("corporate.platformBridge");
  const vehiclesHref = `/vehicles`;
  const quoteHref = `/sign-up?intent=quote&from=${encodeURIComponent(from)}`;
  const bullets = [t("bullets.0"), t("bullets.1"), t("bullets.2")];

  return (
    <section className="site-section bg-gray-bg border-y border-primary/[0.06]">
      <Container>
        <FadeIn>
          <div className="grid lg:grid-cols-2 gap-8 lg:gap-12 items-center">
            <div>
              <SectionHeader label={t("label")} title={t("title")} align="left" className="mb-0" />
              <ul className="mt-6 space-y-3">
                {bullets.map((bullet) => (
                  <li key={bullet} className="flex items-start gap-3 text-sm text-muted">
                    <Check className="w-4 h-4 text-secondary shrink-0 mt-0.5" aria-hidden />
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-col sm:flex-row lg:flex-col gap-3 lg:items-stretch">
              <LinkButton
                href={vehiclesHref}
                size="lg"
                className="w-full justify-center"
                trackEvent={ANALYTICS_EVENTS.SEO_BRIDGE_CLICK}
                trackLabel={t("platformCta")}
                trackSource={`bridge:${from}`}
              >
                {t("platformCta")}
              </LinkButton>
              <LinkButton
                href={quoteHref}
                variant="outline"
                size="lg"
                className="w-full justify-center"
                trackEvent={ANALYTICS_EVENTS.SEO_BRIDGE_CLICK}
                trackLabel={t("quoteCta")}
                trackSource={`bridge:${from}`}
              >
                {t("quoteCta")}
              </LinkButton>
            </div>
          </div>
        </FadeIn>
      </Container>
    </section>
  );
}
