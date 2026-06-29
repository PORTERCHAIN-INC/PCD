"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { MapPin, Clock, User, Truck, Circle, Package } from "lucide-react";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";

export default function LiveMap() {
  const t = useTranslations("liveMap");

  return (
    <section className="site-section bg-primary overflow-hidden">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} dark />

        <div className="rounded-2xl sm:rounded-3xl overflow-hidden border border-white/10 shadow-2xl">
          <div className="relative h-[min(65vw,280px)] sm:h-[min(55vw,400px)] lg:h-[min(50vw,500px)] min-h-[240px] sm:min-h-[320px] bg-[#0f2744]">
            <svg className="absolute inset-0 w-full h-full opacity-10">
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>

            <svg
              className="absolute inset-0 w-full h-full"
              viewBox="0 0 800 500"
              preserveAspectRatio="xMidYMid slice"
            >
              <path
                d="M 50 250 Q 200 200, 350 280 T 650 220 T 750 300"
                stroke="var(--secondary)"
                strokeWidth="3"
                fill="none"
                strokeDasharray="8 4"
                opacity="0.6"
                className="animate-[route-dash_2s_linear_infinite]"
              />
              <path
                d="M 100 350 L 400 150 L 700 350"
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="2"
                fill="none"
              />
              <path
                d="M 200 100 L 200 400 M 400 80 L 400 420 M 600 120 L 600 380"
                stroke="rgba(255,255,255,0.06)"
                strokeWidth="1.5"
                fill="none"
              />
            </svg>

            <svg
              className="absolute bottom-0 left-0 w-full h-16 sm:h-28 opacity-25 pointer-events-none"
              viewBox="0 0 800 80"
              preserveAspectRatio="xMidYMax slice"
              fill="none"
              aria-hidden
            >
              <rect x="0" y="40" width="40" height="40" fill="#1e3354" />
              <rect x="50" y="25" width="35" height="55" fill="#152238" />
              <rect x="100" y="35" width="30" height="45" fill="#1e3354" />
              <rect x="350" y="15" width="8" height="65" fill="#2563eb" opacity="0.5" />
              <ellipse cx="354" cy="35" rx="12" ry="5" fill="#38bdf8" opacity="0.3" />
              <rect x="380" y="30" width="35" height="50" fill="#1e3354" />
              <rect x="500" y="35" width="40" height="45" fill="#1e3354" />
              <rect x="700" y="40" width="100" height="40" fill="#1e3354" />
            </svg>

            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="absolute top-[45%] left-[15%]"
            >
              <div className="w-3.5 h-3.5 sm:w-4 sm:h-4 rounded-full bg-secondary shadow-lg shadow-secondary/50" />
              <div className="absolute -inset-2 rounded-full border-2 border-secondary/30 animate-ping" />
            </motion.div>

            <motion.div
              animate={{ x: [0, 200, 400, 550], y: [0, -30, 20, 50] }}
              transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
              className="absolute top-[40%] left-[20%]"
            >
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-secondary flex items-center justify-center shadow-lg shadow-secondary/40">
                <Truck className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
              </div>
            </motion.div>

            <div className="absolute top-[55%] right-[18%]">
              <MapPin className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
            </div>

            {/* Desktop overlays */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="hidden lg:block absolute top-6 right-6 w-72 glass-dark rounded-2xl p-5 space-y-4"
            >
              <TrackingCard t={t} showProgress />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              className="hidden lg:block absolute bottom-6 left-6 w-64 glass-dark rounded-2xl p-4"
            >
              <OrderCard t={t} />
            </motion.div>
          </div>

          {/* Mobile / tablet cards below map */}
          <div className="lg:hidden grid sm:grid-cols-2 gap-3 p-3 sm:p-4 bg-[#0a1628] border-t border-white/10">
            <div className="glass-dark rounded-2xl p-4 space-y-4">
              <TrackingCard t={t} showProgress />
            </div>
            <div className="glass-dark rounded-2xl p-4">
              <OrderCard t={t} />
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}

function TrackingCard({
  t,
  showProgress = false,
}: {
  t: (key: string) => string;
  showProgress?: boolean;
}) {
  return (
    <>
      <div className="flex items-center justify-between gap-3">
        <span className="text-white/60 type-caption font-bold">{t("liveTracking")}</span>
        <span className="flex items-center gap-1.5 type-caption font-bold normal-case text-green-400 shrink-0">
          <Circle className="w-2 h-2 fill-green-400" />
          {t("inTransit")}
        </span>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Clock className="w-4 h-4 text-secondary shrink-0" />
          <div className="min-w-0">
            <p className="text-white/50 type-caption normal-case">{t("eta")}</p>
            <p className="text-white font-semibold type-small">{t("etaValue")}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <User className="w-4 h-4 text-secondary shrink-0" />
          <div className="min-w-0">
            <p className="text-white/50 type-caption normal-case">{t("driver")}</p>
            <p className="text-white font-semibold type-small">{t("driverName")}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Truck className="w-4 h-4 text-secondary shrink-0" />
          <div className="min-w-0">
            <p className="text-white/50 type-caption normal-case">{t("vehicle")}</p>
            <p className="text-white font-semibold type-small">{t("vehicleType")}</p>
          </div>
        </div>
      </div>

      {showProgress && (
        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
          <motion.div
            animate={{ width: ["30%", "75%"] }}
            transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
            className="h-full bg-secondary rounded-full"
          />
        </div>
      )}
    </>
  );
}

function OrderCard({ t }: { t: (key: string) => string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-10 h-10 rounded-xl bg-secondary/20 flex items-center justify-center shrink-0">
        <Package className="w-5 h-5 text-secondary" />
      </div>
      <div className="min-w-0">
        <p className="text-white font-semibold type-small">{t("orderLabel")}</p>
        <p className="text-white/50 type-caption normal-case truncate">{t("orderRoute")}</p>
      </div>
    </div>
  );
}
