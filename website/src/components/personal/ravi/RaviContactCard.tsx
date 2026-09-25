"use client";

import { UserPlus, ArrowUpRight } from "lucide-react";
import { raviContact, raviContactChannels } from "@/lib/ravi-contact";
import { RaviChannelIcon } from "./RaviChannelIcon";
import BlurFade from "@/components/magic/blur-fade";
import AnimatedGradientText from "@/components/magic/animated-gradient-text";
import BorderBeam from "@/components/magic/border-beam";
import MagicCard from "@/components/magic/magic-card";
import { QUOTE_CTA } from "@/lib/cta";
import { cn } from "@/lib/utils";

const MARQUEE_CHIPS = [
  "Porterchain",
  "Moving Commerce On-Chain",
  "GTA capacity",
  "B2B delivery",
  raviContact.role,
] as const;

export function RaviContactCard() {
  const initials = raviContact.name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const chips = [...MARQUEE_CHIPS, ...MARQUEE_CHIPS];

  return (
    <div className="ravi-page">
      <div className="ravi-page__glow ravi-page__glow--one" aria-hidden />
      <div className="ravi-page__glow ravi-page__glow--two" aria-hidden />
      <div className="ravi-page__glow ravi-page__glow--three" aria-hidden />
      <div className="ravi-page__grid" aria-hidden />

      <div className="ravi-page__marquee" aria-hidden>
        <div className="ravi-page__marquee-track">
          {chips.map((chip, i) => (
            <span key={`${chip}-${i}`} className="ravi-page__chip">
              {chip}
            </span>
          ))}
        </div>
      </div>

      <main className="ravi-card relative overflow-hidden">
        <BorderBeam
          size={180}
          duration={10}
          colorFrom="#2563eb"
          colorTo="#22c55e"
          className="rounded-[1.75rem]"
        />

        <BlurFade delay={0.02}>
          <header className="ravi-card__header">
            <p className="ravi-card__brand">{raviContact.company}</p>
            <p className="ravi-card__tagline">
              <AnimatedGradientText>{raviContact.tagline}</AnimatedGradientText>
            </p>
          </header>
        </BlurFade>

        <BlurFade delay={0.08}>
          <div className="ravi-card__profile">
            <div className="ravi-card__avatar" aria-hidden>
              <span className="ravi-card__avatar-ring" />
              {initials}
            </div>
            <h1 className="ravi-card__name">{raviContact.nameDisplay}</h1>
            <p className="ravi-card__role">{raviContact.role}</p>
            <p className="ravi-card__company">{raviContact.company}</p>

            <a
              href="/ravi/contact.vcf"
              download="Ravi-Chauhan-Porterchain.vcf"
              className={cn(
                "ravi-card__save shimmer-button relative overflow-hidden",
                "inline-flex w-full items-center justify-center gap-2"
              )}
            >
              <span className="relative z-10 inline-flex items-center gap-2">
                <UserPlus className="h-4 w-4 shrink-0" aria-hidden />
                Save to contacts
              </span>
              <span className="shimmer-button-glow absolute inset-0" aria-hidden />
            </a>
          </div>
        </BlurFade>

        <nav className="ravi-card__links" aria-label="Contact and social links">
          <ul>
            {raviContactChannels.map((channel, index) => (
              <li key={channel.id}>
                <BlurFade delay={0.12 + index * 0.04}>
                  <MagicCard className="ravi-card__magic !rounded-2xl !border-primary/10 !shadow-none hover:!shadow-premium">
                    <a
                      href={channel.href}
                      className="ravi-card__link"
                      {...(channel.external
                        ? { target: "_blank", rel: "noopener noreferrer" }
                        : {})}
                    >
                      <span className="ravi-card__link-icon" aria-hidden>
                        <RaviChannelIcon channel={channel.id} />
                      </span>
                      <span className="ravi-card__link-text">
                        <span className="ravi-card__link-label">{channel.label}</span>
                        {channel.detail ? (
                          <span className="ravi-card__link-detail">{channel.detail}</span>
                        ) : null}
                      </span>
                      <ArrowUpRight
                        className="ravi-card__link-arrow h-4 w-4 shrink-0"
                        aria-hidden
                      />
                    </a>
                  </MagicCard>
                </BlurFade>
              </li>
            ))}
          </ul>
        </nav>

        <BlurFade delay={0.48}>
          <footer className="ravi-card__footer">
            <a
              href={raviContact.links.merchantInquiry}
              className={cn(
                "ravi-card__footer-cta shimmer-button relative overflow-hidden",
                "inline-flex w-full items-center justify-center"
              )}
            >
              <span className="relative z-10">{QUOTE_CTA.en} · Merchant setup</span>
              <span className="shimmer-button-glow absolute inset-0" aria-hidden />
            </a>
            <a href={raviContact.links.website} className="ravi-card__footer-link">
              porterchain.com
            </a>
          </footer>
        </BlurFade>
      </main>
    </div>
  );
}
