"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import {
  Package,
  MapPin,
  FileText,
  Users,
  BarChart3,
  Repeat,
  Upload,
  PieChart,
  CreditCard,
  Settings,
} from "lucide-react";

const DASHBOARD_ITEMS = [
  { key: "orders", icon: Package },
  { key: "tracking", icon: MapPin },
  { key: "invoices", icon: FileText },
  { key: "drivers", icon: Users },
  { key: "analytics", icon: BarChart3 },
  { key: "recurring", icon: Repeat },
  { key: "csv", icon: Upload },
  { key: "reports", icon: PieChart },
  { key: "payments", icon: CreditCard },
  { key: "settings", icon: Settings },
] as const;

export default function DashboardPreview() {
  const t = useTranslations("businessPage.dashboard");

  return (
    <section className="biz-section bg-[#091b1c] overflow-hidden">
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center max-w-2xl mx-auto mb-12"
        >
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#ff7a00]">
            {t("label")}
          </span>
          <h2 className="mt-3 biz-heading text-white tracking-tight">{t("title")}</h2>
          <p className="mt-4 text-white/60 leading-relaxed">{t("subtitle")}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 32 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="relative max-w-5xl mx-auto"
        >
          <div className="absolute -inset-8 bg-[#ff7a00]/8 rounded-3xl blur-3xl" />
          <div className="relative rounded-2xl overflow-hidden biz-shadow-lg border border-white/10">
            {/* Browser chrome */}
            <div className="flex items-center gap-2 px-4 py-3 bg-[#0d2526] border-b border-white/8">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
              </div>
              <div className="flex-1 mx-4">
                <div className="max-w-md mx-auto h-7 rounded-lg bg-white/5 flex items-center justify-center text-xs text-white/40">
                  dashboard.porterchain.com
                </div>
              </div>
            </div>

            <div className="flex min-h-[420px]">
              {/* Sidebar */}
              <div className="hidden sm:block w-52 bg-[#0a1e1f] border-r border-white/8 p-4">
                <div className="flex items-center gap-2 mb-6">
                  <div className="w-8 h-8 rounded-lg bg-[#ff7a00] flex items-center justify-center text-white text-sm font-bold">
                    P
                  </div>
                  <span className="text-white text-sm font-semibold">Porterchain</span>
                </div>
                <nav className="space-y-1">
                  {DASHBOARD_ITEMS.map(({ key, icon: Icon }, i) => (
                    <div
                      key={key}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs ${
                        i === 0 ? "bg-[#ff7a00]/15 text-[#ff7a00] font-medium" : "text-white/50"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {t(`items.${key}`)}
                    </div>
                  ))}
                </nav>
              </div>

              {/* Main content */}
              <div className="flex-1 bg-[#f7f8fa] p-5 sm:p-6">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="font-semibold text-[#091b1c]">{t("overview")}</h3>
                  <span className="text-xs text-[#5c6b6c]">{t("today")}</span>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
                  {(["deliveries", "onTime", "revenue", "active"] as const).map((stat) => (
                    <div key={stat} className="p-4 rounded-xl bg-white border border-[#091b1c]/6">
                      <p className="text-2xl font-bold text-[#091b1c]">
                        {t(`stats.${stat}.value`)}
                      </p>
                      <p className="text-xs text-[#5c6b6c] mt-1">{t(`stats.${stat}.label`)}</p>
                    </div>
                  ))}
                </div>
                <div className="rounded-xl bg-white border border-[#091b1c]/6 p-4 h-40 flex items-end gap-2">
                  {[40, 65, 45, 80, 55, 90, 70].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 rounded-t-md bg-gradient-to-t from-[#ff7a00] to-[#ff7a00]/40"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </Container>
    </section>
  );
}
