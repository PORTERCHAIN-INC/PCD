"use client";

import { useTranslations } from "next-intl";
import { FileCode2, Lock, Plug, ScrollText, Shield } from "lucide-react";
import { Link } from "@/i18n/navigation";
import MagicCard from "@/components/magic/magic-card";
import BlurFade from "@/components/magic/blur-fade";
import StorySection from "./StorySection";

const ITEMS = [
  { key: "api", icon: FileCode2, href: "/developers/docs" },
  { key: "security", icon: Shield, href: "/trust" },
  { key: "compliance", icon: Lock, href: "/trust" },
  { key: "integrations", icon: Plug, href: "/integrations" },
  { key: "docs", icon: ScrollText, href: "/developers/docs" },
] as const;

export default function StoryEnterprise() {
  const t = useTranslations("corporate.home.story.enterprise");

  return (
    <StorySection
      id="enterprise"
      label={t("label")}
      title={t("title")}
      subtitle={t("subtitle")}
      dark
    >
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {ITEMS.map((item, i) => {
          const Icon = item.icon;
          return (
            <BlurFade key={item.key} delay={i * 0.05} inView>
              <Link href={item.href} className="block h-full">
                <MagicCard className="flex h-full flex-col items-center border-white/10 bg-white/[0.04] p-5 text-center hover:border-white/20 hover:bg-white/[0.08]">
                  <Icon
                    className="h-6 w-6 text-accent group-hover:text-white transition-colors"
                    aria-hidden
                  />
                  <span className="mt-3 text-sm font-semibold text-white">
                    {t(`items.${item.key}`)}
                  </span>
                </MagicCard>
              </Link>
            </BlurFade>
          );
        })}
      </div>
    </StorySection>
  );
}
