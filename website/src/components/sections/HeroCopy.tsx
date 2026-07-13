"use client";

import BlurFade from "@/components/magic/blur-fade";
import AnimatedGradientText from "@/components/magic/animated-gradient-text";
import ShimmerButton from "@/components/magic/shimmer-button";
import LinkButton from "@/components/corporate/ui/LinkButton";
import SlaResponseCountdown from "@/components/seo/SlaResponseCountdown";
import { MapPin, ShieldCheck, Timer } from "lucide-react";

interface HeroCopyProps {
  locale: string;
  badge: string;
  title: string;
  titleHighlight: string;
  subtitle: string;
  primaryCta: string;
  secondaryCta: string;
  trustLine: string;
  trustProof: string;
  trustAreas: string;
  slaLabel: string;
  slaExpired: string;
}

export default function HeroCopy({
  locale,
  badge,
  title,
  titleHighlight,
  subtitle,
  primaryCta,
  secondaryCta,
  trustLine,
  trustProof,
  trustAreas,
  slaLabel,
  slaExpired,
}: HeroCopyProps) {
  return (
    <div className="hero-copy">
      <BlurFade delay={0.05}>
        <p className="hero-copy__eyebrow">{badge}</p>
      </BlurFade>

      <BlurFade delay={0.1}>
        <h1 className="hero-copy__title text-primary text-balance">
          {title}{" "}
          <AnimatedGradientText className="hero-copy__highlight">
            {titleHighlight}
          </AnimatedGradientText>
        </h1>
      </BlurFade>

      <BlurFade delay={0.15}>
        <p className="hero-copy__subtitle">{subtitle}</p>
      </BlurFade>

      <BlurFade delay={0.2}>
        <div className="hero-copy__actions">
          <ShimmerButton
            href="/contact?intent=quote&from=home-hero"
            trackSource="home-hero"
            className="hero-copy__cta"
          >
            {primaryCta}
          </ShimmerButton>
          <LinkButton
            href="/business#fleet"
            variant="outline"
            size="md"
            trackSource="home-hero"
            className="hero-copy__cta"
          >
            {secondaryCta}
          </LinkButton>
        </div>
      </BlurFade>

      <BlurFade delay={0.28} inView>
        <ul className="hero-copy__trust">
          <li>
            <Timer className="hero-copy__trust-icon" aria-hidden />
            <span>{trustLine}</span>
          </li>
          <li>
            <ShieldCheck className="hero-copy__trust-icon" aria-hidden />
            <span>{trustProof}</span>
          </li>
          <li>
            <MapPin className="hero-copy__trust-icon" aria-hidden />
            <span>{trustAreas}</span>
          </li>
        </ul>
      </BlurFade>

      <BlurFade delay={0.34} inView>
        <div className="hero-copy__sla">
          <SlaResponseCountdown locale={locale} label={slaLabel} expiredLabel={slaExpired} />
        </div>
      </BlurFade>
    </div>
  );
}
