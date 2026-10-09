"use client";

import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_CHALLENGE_KEYS } from "@/data/business";
import MagicCard from "@/components/magic/magic-card";
import BlurFade from "@/components/magic/blur-fade";
import {
  DollarSign,
  Clock,
  CalendarX,
  EyeOff,
  Users,
  MapPinOff,
  FileText,
  TrendingDown,
} from "lucide-react";

const ICONS = [DollarSign, Clock, CalendarX, EyeOff, Users, MapPinOff, FileText, TrendingDown];

export default function BusinessChallenges() {
  const t = useTranslations("businessPage.challenges");

  return (
    <section className="biz-section bg-[#f7f8fa]">
      <Container>
        <BlurFade inView className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="biz-heading text-[#0b1220] tracking-tight">{t("title")}</h2>
          <p className="mt-4 text-[#5b6779] leading-relaxed">{t("subtitle")}</p>
        </BlurFade>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
          {BUSINESS_CHALLENGE_KEYS.map((key, i) => {
            const Icon = ICONS[i];
            return (
              <BlurFade key={key} delay={i * 0.05} inView>
                <MagicCard className="h-full p-6">
                  <div className="w-10 h-10 rounded-xl bg-[#2563eb]/10 flex items-center justify-center text-[#2563eb] mb-4">
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="font-semibold text-[#0b1220] mb-2">{t(`items.${key}.title`)}</h3>
                  <p className="text-sm text-[#5b6779] leading-relaxed">
                    {t(`items.${key}.description`)}
                  </p>
                </MagicCard>
              </BlurFade>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
