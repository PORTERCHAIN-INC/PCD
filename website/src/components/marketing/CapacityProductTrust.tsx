"use client";

import { useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Check, FileCheck2, MapPin, Navigation, Truck, Zap } from "lucide-react";
import Container from "@/components/ui/Container";
import { Link } from "@/i18n/navigation";
import { HUB_FROM } from "@/lib/marketing/config";
import { cn } from "@/lib/utils";

const PANEL_KEYS = ["quote", "track", "pod"] as const;
type PanelKey = (typeof PANEL_KEYS)[number];

type Props = {
  /** Visual surface — homepage uses light; platform/business can use ink. */
  tone?: "light" | "ink";
  /** Analytics / CTA from param */
  from?: string;
  className?: string;
};

function BrowserChrome({ url }: { url: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-primary/8 bg-[#0f172a] px-3 py-2.5 sm:px-4">
      <div className="flex gap-1.5" aria-hidden>
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
      </div>
      <div className="mx-auto flex h-7 max-w-md flex-1 items-center justify-center rounded-md bg-white/6 px-3 text-[11px] text-white/45 sm:text-xs">
        {url}
      </div>
    </div>
  );
}

function QuotePanel({ t }: { t: ReturnType<typeof useTranslations> }) {
  return (
    <div className="grid gap-4 p-4 sm:grid-cols-[1fr_0.95fr] sm:gap-5 sm:p-6">
      <div className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-secondary">
          {t("panels.quote.formLabel")}
        </p>
        {(
          [
            ["pickup", t("panels.quote.pickup")],
            ["drop", t("panels.quote.drop")],
            ["vehicle", t("panels.quote.vehicle")],
            ["window", t("panels.quote.window")],
          ] as const
        ).map(([key, value]) => (
          <div
            key={key}
            className="rounded-xl border border-primary/8 bg-white px-3.5 py-2.5 shadow-sm"
          >
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted">
              {t(`panels.quote.fields.${key}`)}
            </p>
            <p className="mt-0.5 text-sm font-semibold text-primary">{value}</p>
          </div>
        ))}
      </div>
      <div className="flex flex-col justify-between rounded-2xl border border-secondary/20 bg-gradient-to-br from-[#eff6ff] to-white p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-secondary">
            <Zap className="h-4 w-4" aria-hidden />
            <span className="text-xs font-semibold uppercase tracking-[0.14em]">
              {t("panels.quote.resultLabel")}
            </span>
          </div>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-primary sm:text-4xl">
            {t("panels.quote.price")}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted">{t("panels.quote.priceNote")}</p>
        </div>
        <ul className="mt-5 space-y-2">
          {(["driver", "tracking", "written"] as const).map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-primary/85">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
              <span>{t(`panels.quote.includes.${item}`)}</span>
            </li>
          ))}
        </ul>
        <div className="mt-5 rounded-xl bg-primary px-4 py-3 text-center text-sm font-semibold text-white">
          {t("panels.quote.cta")}
        </div>
      </div>
    </div>
  );
}

function TrackPanel({ t }: { t: ReturnType<typeof useTranslations> }) {
  const steps = ["dispatched", "pickup", "enRoute", "eta"] as const;
  return (
    <div className="grid gap-4 p-4 sm:grid-cols-[1.1fr_0.9fr] sm:gap-5 sm:p-6">
      <div className="relative overflow-hidden rounded-2xl border border-primary/8 bg-[#e8eef8] min-h-[220px]">
        <div
          className="absolute inset-0 opacity-60"
          style={{
            backgroundImage:
              "linear-gradient(rgba(37,99,235,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(37,99,235,0.08) 1px, transparent 1px)",
            backgroundSize: "28px 28px",
          }}
          aria-hidden
        />
        <svg viewBox="0 0 320 220" className="absolute inset-0 h-full w-full" aria-hidden>
          <path
            d="M36 170 C90 150, 110 90, 160 100 S240 150, 286 70"
            fill="none"
            stroke="#2563eb"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray="8 6"
          />
          <circle cx="36" cy="170" r="7" fill="#0b1220" />
          <circle cx="160" cy="100" r="6" fill="#2563eb" />
          <circle cx="286" cy="70" r="8" fill="#2563eb" />
          <circle cx="286" cy="70" r="14" fill="#2563eb" opacity="0.2" />
        </svg>
        <div className="absolute left-3 top-3 rounded-lg border border-white/70 bg-white/95 px-2.5 py-1.5 shadow-sm backdrop-blur-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
            {t("panels.track.mapBadge")}
          </p>
          <p className="text-xs font-semibold text-primary">{t("panels.track.corridor")}</p>
        </div>
        <div className="absolute bottom-3 right-3 flex items-center gap-2 rounded-xl border border-secondary/25 bg-white px-3 py-2 shadow-md">
          <Truck className="h-4 w-4 text-secondary" aria-hidden />
          <div>
            <p className="text-[10px] font-medium text-muted">{t("panels.track.vehicle")}</p>
            <p className="text-xs font-semibold text-primary">{t("panels.track.eta")}</p>
          </div>
        </div>
      </div>
      <div className="rounded-2xl border border-primary/8 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-secondary">
              {t("panels.track.shipment")}
            </p>
            <p className="mt-1 text-base font-semibold text-primary">{t("panels.track.ref")}</p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-secondary/10 px-2.5 py-1 text-[11px] font-semibold text-secondary">
            <Navigation className="h-3 w-3" aria-hidden />
            {t("panels.track.status")}
          </span>
        </div>
        <ol className="mt-5 space-y-3">
          {steps.map((step, i) => (
            <li key={step} className="flex items-start gap-3">
              <span
                className={cn(
                  "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold",
                  i < 3 ? "bg-secondary text-white" : "bg-secondary/15 text-secondary"
                )}
              >
                {i < 3 ? <Check className="h-3.5 w-3.5" aria-hidden /> : i + 1}
              </span>
              <div>
                <p className="text-sm font-semibold text-primary">
                  {t(`panels.track.steps.${step}.title`)}
                </p>
                <p className="text-xs text-muted">{t(`panels.track.steps.${step}.meta`)}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function PodPanel({ t }: { t: ReturnType<typeof useTranslations> }) {
  return (
    <div className="grid gap-4 p-4 sm:grid-cols-[0.95fr_1.05fr] sm:gap-5 sm:p-6">
      <div className="overflow-hidden rounded-2xl border border-primary/8 bg-[#0b1220] shadow-sm">
        <div className="relative aspect-[4/3] bg-gradient-to-br from-[#1e293b] via-[#0f172a] to-[#020617]">
          <div
            className="absolute inset-6 rounded-xl border-2 border-dashed border-white/20"
            aria-hidden
          />
          <div className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center">
            <FileCheck2 className="h-10 w-10 text-white/70" aria-hidden />
            <p className="mt-3 text-sm font-semibold text-white">{t("panels.pod.photoLabel")}</p>
            <p className="mt-1 text-xs text-white/50">{t("panels.pod.photoMeta")}</p>
          </div>
          <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between rounded-lg bg-black/45 px-3 py-2 text-[11px] text-white/85 backdrop-blur-sm">
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-3 w-3" aria-hidden />
              {t("panels.pod.gps")}
            </span>
            <span>{t("panels.pod.timestamp")}</span>
          </div>
        </div>
      </div>
      <div className="flex flex-col rounded-2xl border border-primary/8 bg-white p-4 shadow-sm sm:p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-secondary">
          {t("panels.pod.closeoutLabel")}
        </p>
        <h3 className="mt-2 text-lg font-semibold text-primary">{t("panels.pod.title")}</h3>
        <p className="mt-2 text-sm leading-relaxed text-muted">{t("panels.pod.body")}</p>
        <dl className="mt-5 grid gap-3 sm:grid-cols-2">
          {(
            [
              ["receiver", t("panels.pod.receiver")],
              ["method", t("panels.pod.method")],
              ["site", t("panels.pod.site")],
              ["ref", t("panels.pod.ref")],
            ] as const
          ).map(([key, value]) => (
            <div key={key} className="rounded-xl bg-gray-bg px-3 py-2.5">
              <dt className="text-[10px] font-medium uppercase tracking-wide text-muted">
                {t(`panels.pod.fields.${key}`)}
              </dt>
              <dd className="mt-0.5 text-sm font-semibold text-primary">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-auto pt-5">
          <div className="flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-50 px-3 py-2.5 text-sm font-semibold text-emerald-800">
            <Check className="h-4 w-4" aria-hidden />
            {t("panels.pod.verified")}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CapacityProductTrust({
  tone = "light",
  from = HUB_FROM.chooser,
  className,
}: Props) {
  const t = useTranslations("productTrust");
  const reduce = useReducedMotion();
  const [active, setActive] = useState<PanelKey>("quote");
  const quoteHref = `/sign-up?intent=quote&from=${from}-product-trust`;

  return (
    <section
      className={cn(
        "relative overflow-hidden",
        tone === "ink" ? "bg-primary text-white" : "bg-white",
        className
      )}
      aria-labelledby="product-trust-heading"
    >
      <Container className="py-16 sm:py-20">
        <div className="mx-auto max-w-2xl text-center">
          <p className={cn("pc-eyebrow", tone === "ink" ? "text-accent" : "text-secondary")}>
            {t("eyebrow")}
          </p>
          <h2
            id="product-trust-heading"
            className={cn(
              "mt-2 text-2xl font-semibold tracking-tight sm:text-3xl lg:text-4xl",
              tone === "ink" ? "text-white" : "text-primary"
            )}
          >
            {t("title")}
          </h2>
          <p
            className={cn(
              "mt-4 text-base leading-relaxed sm:text-lg",
              tone === "ink" ? "text-white/65" : "text-muted"
            )}
          >
            {t("subtitle")}
          </p>
        </div>

        <div
          className="mx-auto mt-8 flex max-w-xl flex-wrap justify-center gap-2"
          role="tablist"
          aria-label={t("tabsAria")}
        >
          {PANEL_KEYS.map((key) => {
            const selected = active === key;
            return (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => setActive(key)}
                className={cn(
                  "rounded-full px-4 py-2 text-sm font-semibold transition-colors",
                  selected
                    ? tone === "ink"
                      ? "bg-white text-primary"
                      : "bg-primary text-white"
                    : tone === "ink"
                      ? "bg-white/10 text-white/75 hover:bg-white/15"
                      : "bg-gray-bg text-primary/70 hover:bg-primary/5 hover:text-primary"
                )}
              >
                {t(`tabs.${key}`)}
              </button>
            );
          })}
        </div>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.55 }}
          className="relative mx-auto mt-10 max-w-5xl"
        >
          {tone === "light" ? (
            <div
              className="pointer-events-none absolute -inset-6 rounded-[2rem] bg-secondary/10 blur-3xl"
              aria-hidden
            />
          ) : (
            <div
              className="pointer-events-none absolute -inset-6 rounded-[2rem] bg-secondary/25 blur-3xl"
              aria-hidden
            />
          )}
          <div className="relative overflow-hidden rounded-2xl border border-primary/10 bg-[#f7f8fa] shadow-[0_24px_80px_-28px_rgba(11,18,32,0.45)]">
            <BrowserChrome url={t(`panels.${active}.url`)} />
            <div
              role="tabpanel"
              aria-label={t(`tabs.${active}`)}
              className="min-h-[320px] sm:min-h-[360px]"
            >
              <AnimatePresence mode="wait">
                <motion.div
                  key={active}
                  initial={reduce ? false : { opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduce ? undefined : { opacity: 0, y: -8 }}
                  transition={{ duration: 0.28 }}
                >
                  {active === "quote" ? <QuotePanel t={t} /> : null}
                  {active === "track" ? <TrackPanel t={t} /> : null}
                  {active === "pod" ? <PodPanel t={t} /> : null}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </motion.div>

        <div className="mt-10 text-center">
          <Link
            href={quoteHref}
            className={cn(
              "inline-flex min-h-[var(--touch-min)] items-center justify-center rounded-xl px-6 py-3 text-sm font-semibold transition-colors",
              tone === "ink"
                ? "bg-white text-primary hover:bg-white/90"
                : "bg-secondary text-white hover:bg-[#1d4ed8]"
            )}
          >
            {t("cta")}
          </Link>
          <p className={cn("mt-3 text-sm", tone === "ink" ? "text-white/55" : "text-muted")}>
            {t("ctaHint")}
          </p>
        </div>
      </Container>
    </section>
  );
}
