"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import {
  LayoutDashboard,
  ShoppingCart,
  FileText,
  BarChart3,
  Route,
  MapPin,
  Upload,
  Code,
  CreditCard,
  TrendingUp,
  Package,
  Users,
} from "lucide-react";
import SectionHeader from "@/components/ui/SectionHeader";
import Button from "@/components/ui/Button";
import Container from "@/components/ui/Container";
import { merchantPortalUrl, portalDisplayHost } from "@/data/portal-links";

const FEATURE_KEYS = [
  "merchantPortal",
  "orderManagement",
  "invoices",
  "analytics",
  "routeOptimization",
  "driverTracking",
  "csvUpload",
  "api",
  "paymentTerms",
] as const;

const FEATURE_ICONS = [
  LayoutDashboard,
  ShoppingCart,
  FileText,
  BarChart3,
  Route,
  MapPin,
  Upload,
  Code,
  CreditCard,
];

const ORDER_KEYS = ["medical", "coffee", "parts"] as const;

export default function BusinessPlatform() {
  const t = useTranslations("businessPlatform");

  return (
    <section id="business" className="site-section bg-white">
      <Container>
        <div className="grid lg:grid-cols-2 gap-10 sm:gap-12 lg:gap-16 xl:gap-20 items-center">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="relative"
          >
            <div className="rounded-2xl border border-gray-200/80 bg-gray-bg shadow-premium overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 bg-primary border-b border-white/5">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-400/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-400/80" />
                  <div className="w-3 h-3 rounded-full bg-secondary/80" />
                </div>
                <div className="flex-1 mx-4">
                  <div className="bg-white/10 rounded-md px-3 py-1 text-xs text-white/50 text-center">
                    {portalDisplayHost(merchantPortalUrl)}
                  </div>
                </div>
              </div>

              <div className="p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-primary type-small">
                    {t("dashboardOverview")}
                  </h4>
                  <span className="type-caption text-secondary normal-case">{t("today")}</span>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: t("active"), value: "24", icon: Package, color: "text-secondary" },
                    {
                      label: t("delivered"),
                      value: "186",
                      icon: TrendingUp,
                      color: "text-secondary",
                    },
                    { label: t("drivers"), value: "12", icon: Users, color: "text-blue-600" },
                  ].map((stat) => {
                    const Icon = stat.icon;
                    return (
                      <div
                        key={stat.label}
                        className="bg-white rounded-xl p-3 border border-gray-100"
                      >
                        <Icon className={`w-4 h-4 ${stat.color} mb-1`} />
                        <p className="type-h3 text-primary">{stat.value}</p>
                        <p className="type-caption text-muted normal-case">{stat.label}</p>
                      </div>
                    );
                  })}
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100">
                  <p className="type-label text-primary mb-3">{t("weeklyDeliveries")}</p>
                  <div className="flex items-end gap-1.5 h-20">
                    {[40, 65, 45, 80, 55, 90, 70].map((h, i) => (
                      <div
                        key={i}
                        className="flex-1 rounded-sm bg-secondary/20 hover:bg-secondary/40 transition-colors"
                        style={{ height: `${h}%` }}
                      />
                    ))}
                  </div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100 space-y-2">
                  {ORDER_KEYS.map((key) => (
                    <div key={key} className="flex items-center justify-between text-xs">
                      <span className="text-primary/80">{t(`orderStatuses.${key}`)}</span>
                      <span className="text-secondary font-medium">
                        {t("orderStatuses.delivered")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="absolute -bottom-4 -right-4 bg-secondary text-white px-4 py-2 rounded-xl type-small font-semibold shadow-lg shadow-secondary/30">
              {t("onTime")}
            </div>
          </motion.div>

          <div>
            <SectionHeader
              label={t("label")}
              title={t("title")}
              subtitle={t("subtitle")}
              align="left"
              className="mb-8"
            />

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8">
              {FEATURE_KEYS.map((key, i) => {
                const Icon = FEATURE_ICONS[i];
                return (
                  <motion.div
                    key={key}
                    initial={{ opacity: 0, y: 10 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.3, delay: i * 0.05 }}
                    className="flex items-center gap-2.5 p-3 rounded-xl bg-gray-bg hover:bg-secondary/5 transition-colors"
                  >
                    <Icon className="w-4 h-4 text-secondary shrink-0" />
                    <span className="type-caption normal-case text-primary">
                      {t(`features.${key}`)}
                    </span>
                  </motion.div>
                );
              })}
            </div>

            <Button size="lg" className="rounded-xl">
              {t("cta")}
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}
