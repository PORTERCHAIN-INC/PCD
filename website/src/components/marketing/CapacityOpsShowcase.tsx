"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Check, FileCheck2, MapPin, MessageSquare, Truck } from "lucide-react";
import Container from "@/components/ui/Container";
import { Link } from "@/i18n/navigation";
import { HUB_FROM } from "@/lib/marketing/config";
import { cn } from "@/lib/utils";

const FEATURE_KEYS = ["monitor", "dispatch", "notify", "closeout", "claims"] as const;
type FeatureKey = (typeof FEATURE_KEYS)[number];
type OpsT = ReturnType<typeof useTranslations<"capacityOps">>;

type Props = {
  from?: string;
  className?: string;
};

function FeedDemo({ t }: { t: OpsT }) {
  const events = ["dispatched", "pickup", "stall", "recovered", "delivered"] as const;
  return (
    <div className="overflow-hidden rounded-2xl border border-primary/10 bg-[#0b1220] shadow-xl shadow-primary/10">
      <div className="flex items-center justify-between border-b border-white/8 px-4 py-3">
        <p className="text-xs font-semibold text-white/80">{t("demos.feed.title")}</p>
        <span className="rounded-full bg-secondary/20 px-2 py-0.5 text-[10px] font-semibold text-[#93c5fd]">
          {t("demos.feed.live")}
        </span>
      </div>
      <div className="space-y-0 px-2 py-2">
        {events.map((key, i) => (
          <div
            key={key}
            className={cn(
              "flex gap-3 rounded-xl px-3 py-2.5",
              i === 2 || i === 3 ? "bg-amber-500/10" : "bg-transparent"
            )}
          >
            <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-secondary" />
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-sm font-semibold text-white">
                  {t(`demos.feed.events.${key}.title`)}
                </p>
                <span className="shrink-0 text-[11px] text-white/40">
                  {t(`demos.feed.events.${key}.time`)}
                </span>
              </div>
              <p className="mt-0.5 text-xs leading-relaxed text-white/55">
                {t(`demos.feed.events.${key}.body`)}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Marketing kanban — mirrors admin DispatchBoard card recipe (tracking, route, driver, SLA). */
const BOARD_COLS = [
  { key: "waiting", accent: "#64748b", cards: 2 as const },
  { key: "assigned", accent: "#0ea5e9", cards: 1 as const },
  { key: "atPickup", accent: "#a855f7", cards: 1 as const },
  { key: "inTransit", accent: "#2563eb", cards: 2 as const },
  { key: "delivered", accent: "#16a34a", cards: 1 as const },
] as const;

function BoardDemo({ t }: { t: OpsT }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-primary/10 bg-white shadow-xl shadow-primary/10">
      {/* Browser chrome */}
      <div className="flex items-center gap-2 border-b border-primary/8 bg-[#0f1b2d] px-3 py-2.5 sm:px-4">
        <div className="flex gap-1.5" aria-hidden>
          <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
        </div>
        <div className="mx-2 flex-1 sm:mx-4">
          <div className="mx-auto flex h-7 max-w-md items-center justify-center rounded-lg bg-white/5 text-[11px] text-white/45">
            {t("demos.board.url")}
          </div>
        </div>
      </div>

      {/* Merchant portal top bar */}
      <div className="flex items-center gap-3 border-b border-primary/8 bg-white px-3 py-2.5 sm:px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-secondary text-[11px] font-bold text-white">
          P
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-primary">{t("demos.board.appName")}</p>
          <p className="truncate text-[10px] text-muted">{t("demos.board.appSub")}</p>
        </div>
        <span className="hidden rounded-full bg-secondary/10 px-2.5 py-1 text-[10px] font-semibold text-secondary sm:inline">
          {t("demos.board.viewLabel")}
        </span>
        <span className="rounded-full bg-gray-bg px-2 py-1 text-[10px] font-medium text-muted">
          {t("demos.board.active")}
        </span>
      </div>

      {/* Kanban */}
      <div className="bg-[#f7f8fa] p-3 sm:p-4">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-primary">{t("demos.board.title")}</p>
            <p className="mt-0.5 text-[11px] text-muted">{t("demos.board.subtitle")}</p>
          </div>
          <div className="flex gap-1.5">
            <span className="rounded-lg border border-primary/8 bg-white px-2 py-1 text-[10px] font-medium text-muted">
              {t("demos.board.filterToday")}
            </span>
            <span className="hidden rounded-lg border border-primary/8 bg-white px-2 py-1 text-[10px] font-medium text-muted sm:inline">
              {t("demos.board.filterAll")}
            </span>
          </div>
        </div>

        <div className="-mx-1 flex gap-2.5 overflow-x-auto px-1 pb-1 [scrollbar-width:thin]">
          {BOARD_COLS.map((col) => (
            <div key={col.key} className="flex w-[148px] shrink-0 flex-col sm:w-[168px]">
              <div className="mb-2 flex items-center gap-1.5 px-0.5">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: col.accent }}
                  aria-hidden
                />
                <span className="truncate text-[11px] font-semibold text-primary">
                  {t(`demos.board.cols.${col.key}`)}
                </span>
                <span className="ml-auto rounded-full bg-white px-1.5 text-[10px] tabular-nums text-muted shadow-sm">
                  {col.cards}
                </span>
              </div>
              <div className="flex min-h-[200px] flex-col gap-2 rounded-2xl border border-dashed border-primary/10 bg-white/60 p-1.5">
                {Array.from({ length: col.cards }, (_, idx) => {
                  const sla = t(`demos.board.cards.${col.key}.${idx}.sla`);
                  const slaTone = t(`demos.board.cards.${col.key}.${idx}.slaTone`);
                  return (
                    <div
                      key={idx}
                      className="rounded-xl border border-primary/8 bg-white p-2.5 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-1">
                        <span className="font-mono text-[11px] font-semibold text-primary">
                          {t(`demos.board.cards.${col.key}.${idx}.id`)}
                        </span>
                        <span
                          className={cn(
                            "shrink-0 rounded-md px-1.5 py-0.5 text-[9px] font-semibold",
                            slaTone === "green" && "bg-emerald-50 text-emerald-700",
                            slaTone === "amber" && "bg-amber-50 text-amber-700",
                            slaTone === "slate" && "bg-slate-100 text-slate-600"
                          )}
                        >
                          {sla}
                        </span>
                      </div>
                      <p className="mt-1 truncate text-[10px] text-muted">
                        {t(`demos.board.cards.${col.key}.${idx}.merchant`)}
                      </p>
                      <p className="mt-0.5 truncate text-[10px] font-medium text-primary">
                        {t(`demos.board.cards.${col.key}.${idx}.route`)}
                      </p>
                      <div className="mt-1.5 flex gap-0.5" aria-hidden>
                        <span className="h-1 flex-1 rounded-full bg-emerald-500" />
                        <span
                          className={cn(
                            "h-1 flex-1 rounded-full",
                            col.key === "waiting" || col.key === "assigned"
                              ? "bg-primary/10"
                              : "bg-emerald-500"
                          )}
                        />
                        <span
                          className={cn(
                            "h-1 flex-1 rounded-full",
                            col.key === "delivered" ? "bg-emerald-500" : "bg-primary/10"
                          )}
                        />
                      </div>
                      <p className="mt-1.5 truncate text-[10px] text-muted">
                        {t(`demos.board.cards.${col.key}.${idx}.driver`)}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function NotifyDemo({ t }: { t: OpsT }) {
  const msgs = ["dispatch", "nearby", "delivered"] as const;
  return (
    <div className="overflow-hidden rounded-2xl border border-primary/10 bg-[#0b1220] shadow-xl shadow-primary/10">
      <div className="flex items-center gap-2 border-b border-white/8 px-4 py-3">
        <MessageSquare className="h-3.5 w-3.5 text-secondary" aria-hidden />
        <p className="text-xs font-semibold text-white/80">{t("demos.notify.title")}</p>
        <span className="ml-auto rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
          {t("demos.notify.active")}
        </span>
      </div>
      <div className="space-y-3 p-4">
        {msgs.map((key) => (
          <div key={key} className="rounded-xl border border-white/8 bg-white/[0.04] p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-secondary">
                {t(`demos.notify.msgs.${key}.channel`)}
              </span>
              <span className="text-[10px] text-white/40">
                {t(`demos.notify.msgs.${key}.when`)}
              </span>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-white/75">
              {t(`demos.notify.msgs.${key}.body`, {
                business: t("demos.notify.sampleBusiness"),
                link: t("demos.notify.sampleLink"),
              })}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CloseoutDemo({ t }: { t: OpsT }) {
  const checks = ["photo", "gps", "window", "notes"] as const;
  return (
    <div className="overflow-hidden rounded-2xl border border-primary/10 bg-white shadow-xl shadow-primary/8">
      <div className="border-b border-primary/8 bg-[#f8fafc] px-4 py-3">
        <p className="text-xs font-semibold text-primary">{t("demos.closeout.title")}</p>
      </div>
      <div className="grid gap-3 p-4 sm:grid-cols-[1fr_1.1fr]">
        <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-[#0b1220]">
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <FileCheck2 className="h-8 w-8 text-white/60" aria-hidden />
            <p className="mt-2 text-xs font-semibold text-white/80">{t("demos.closeout.photo")}</p>
          </div>
          <div className="absolute bottom-2 left-2 right-2 flex justify-between rounded-md bg-black/50 px-2 py-1.5 text-[10px] text-white/85">
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-3 w-3" aria-hidden />
              {t("demos.closeout.gps")}
            </span>
            <span>{t("demos.closeout.time")}</span>
          </div>
        </div>
        <ul className="space-y-2">
          {checks.map((key) => (
            <li
              key={key}
              className="flex items-start gap-2 rounded-lg border border-primary/6 bg-gray-bg/60 px-3 py-2.5"
            >
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden />
              <span className="text-sm text-primary/90">{t(`demos.closeout.checks.${key}`)}</span>
            </li>
          ))}
          <li className="rounded-lg border border-emerald-500/20 bg-emerald-50 px-3 py-2.5 text-sm font-semibold text-emerald-800">
            {t("demos.closeout.verified")}
          </li>
        </ul>
      </div>
    </div>
  );
}

function ClaimsDemo({ t }: { t: OpsT }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-primary/10 bg-white shadow-xl shadow-primary/8">
      <div className="flex items-center justify-between border-b border-primary/8 bg-[#f8fafc] px-4 py-3">
        <p className="text-xs font-semibold text-primary">{t("demos.claims.title")}</p>
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
          {t("demos.claims.status")}
        </span>
      </div>
      <div className="space-y-3 p-4">
        {(["issue", "evidence", "record"] as const).map((key) => (
          <div key={key} className="rounded-xl border border-primary/6 bg-gray-bg/50 px-3.5 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
              {t(`demos.claims.steps.${key}.label`)}
            </p>
            <p className="mt-1 text-sm font-medium text-primary">
              {t(`demos.claims.steps.${key}.body`)}
            </p>
          </div>
        ))}
        <div className="flex items-center gap-2 rounded-xl border border-secondary/20 bg-[#eff6ff] px-3.5 py-3">
          <Truck className="h-4 w-4 text-secondary" aria-hidden />
          <p className="text-sm font-semibold text-primary">{t("demos.claims.outcome")}</p>
        </div>
      </div>
    </div>
  );
}

const DEMO: Record<FeatureKey, (props: { t: OpsT }) => ReactNode> = {
  monitor: FeedDemo,
  dispatch: BoardDemo,
  notify: NotifyDemo,
  closeout: CloseoutDemo,
  claims: ClaimsDemo,
};

export default function CapacityOpsShowcase({ from = HUB_FROM.chooser, className }: Props) {
  const t = useTranslations("capacityOps");
  const tCta = useTranslations("common.cta");
  const reduce = useReducedMotion();
  const quoteHref = `/sign-up?intent=quote&from=${from}-ops-showcase`;

  return (
    <section
      className={cn("relative overflow-hidden bg-[#F4F6FA]", className)}
      aria-labelledby="capacity-ops-heading"
    >
      <Container className="py-16 sm:py-20 lg:py-24">
        <div className="mx-auto max-w-2xl text-center">
          <p className="pc-eyebrow text-secondary">{t("eyebrow")}</p>
          <h2
            id="capacity-ops-heading"
            className="mt-2 text-2xl font-semibold tracking-tight text-primary sm:text-3xl lg:text-4xl"
          >
            {t("title")}
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted sm:text-lg">{t("subtitle")}</p>
        </div>

        <div className="mt-14 space-y-16 lg:mt-20 lg:space-y-24">
          {FEATURE_KEYS.map((key, index) => {
            const Demo = DEMO[key];
            const reverse = index % 2 === 1;
            const fullWidth = key === "dispatch";
            return (
              <motion.div
                key={key}
                initial={reduce ? false : { opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.5 }}
                className={cn(
                  fullWidth
                    ? "space-y-8"
                    : cn(
                        "grid items-center gap-8 lg:grid-cols-2 lg:gap-14",
                        reverse && "lg:[&>*:first-child]:order-2"
                      )
                )}
              >
                <div className={cn(fullWidth && "mx-auto max-w-2xl text-center")}>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-secondary">
                    {t(`features.${key}.label`)}
                  </p>
                  <h3 className="mt-2 text-xl font-semibold tracking-tight text-primary sm:text-2xl">
                    {t(`features.${key}.title`)}
                  </h3>
                  <p className="mt-3 text-base leading-relaxed text-muted">
                    {t(`features.${key}.body`)}
                  </p>
                </div>
                <Demo t={t} />
              </motion.div>
            );
          })}
        </div>

        <div className="mt-16 text-center lg:mt-20">
          <Link
            href={quoteHref}
            className="inline-flex min-h-[var(--touch-min)] items-center justify-center rounded-xl bg-secondary px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
          >
            {tCta("quote")}
          </Link>
          <p className="mt-3 text-sm text-muted">{t("ctaHint")}</p>
        </div>
      </Container>
    </section>
  );
}
