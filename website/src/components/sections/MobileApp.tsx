"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Smartphone, Truck } from "lucide-react";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";

const APP_KEYS = ["customer", "driver"] as const;
const APP_ICONS = [Smartphone, Truck];
const APP_GRADIENTS = [
  "from-secondary to-blue-700",
  "from-primary to-[#152238]",
];

function PhoneMockup({ children, gradient }: { children: React.ReactNode; gradient: string }) {
  return (
    <div className="relative mx-auto w-[220px]">
      <div className="rounded-[2.5rem] border-[6px] border-gray-800 bg-gray-800 shadow-2xl overflow-hidden">
        <div className="h-6 bg-gray-800 flex items-center justify-center">
          <div className="w-16 h-4 bg-gray-900 rounded-full" />
        </div>
        <div className={`h-[380px] bg-gradient-to-b ${gradient} p-4`}>{children}</div>
        <div className="h-4 bg-gray-800" />
      </div>
    </div>
  );
}

export default function MobileApp() {
  const t = useTranslations("mobileApp");

  return (
    <section className="site-section bg-gray-bg">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />

        <div className="grid sm:grid-cols-2 gap-8 lg:gap-12 max-w-3xl mx-auto">
          {APP_KEYS.map((key, i) => {
            const Icon = APP_ICONS[i];
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.15 }}
                className="text-center"
              >
                <PhoneMockup gradient={APP_GRADIENTS[i]}>
                  <div className="flex flex-col items-center justify-center h-full text-white">
                    <Icon className="w-10 h-10 mb-3 opacity-80" />
                    <p className="font-semibold type-small">{t(`apps.${key}.name`)}</p>
                    <div className="mt-4 w-full space-y-2">
                      <div className="h-8 bg-white/10 rounded-lg" />
                      <div className="h-8 bg-white/10 rounded-lg" />
                      <div className="h-12 bg-white/20 rounded-lg" />
                    </div>
                  </div>
                </PhoneMockup>

                <h3 className="mt-6 type-h3 text-primary">{t(`apps.${key}.name`)}</h3>
                <p className="text-muted type-small mt-1 max-w-xs mx-auto">
                  {t(`apps.${key}.description`)}
                </p>

                <div className="mt-4 flex justify-center gap-2">
                  <a
                    href="#"
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-primary text-white type-caption normal-case tracking-normal hover:bg-primary/90 transition-colors"
                  >
                    {t("appStore")}
                  </a>
                  <a
                    href="#"
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-gray-300 text-primary type-caption normal-case tracking-normal hover:bg-white transition-colors"
                  >
                    {t("googlePlay")}
                  </a>
                </div>
              </motion.div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
