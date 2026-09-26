"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { AlertTriangle, ClipboardList, Timer, Zap } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { AnimatedRing, NumberTicker } from "@/components/dashboard/magic";

type Tone = "ok" | "warn" | "danger";

type Channel = {
  id: string;
  label: string;
  value: number;
  /** Soft ceiling for bar fill (visual scale, not a hard SLA). */
  scale: number;
  tone: Tone;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
};

const TONE: Record<Tone, { bar: string; text: string; track: string }> = {
  ok: { bar: "bg-emerald-500", text: "text-emerald-700", track: "bg-emerald-100" },
  warn: { bar: "bg-amber-500", text: "text-amber-800", track: "bg-amber-100" },
  danger: { bar: "bg-red-500", text: "text-red-700", track: "bg-red-100" },
};

function toneWaiting(n: number): Tone {
  return n >= 15 ? "danger" : n >= 5 ? "warn" : "ok";
}
function toneDelayed(n: number): Tone {
  return n >= 5 ? "danger" : n > 0 ? "warn" : "ok";
}
function toneSla(breached: number, atRisk: number): Tone {
  return breached > 0 ? "danger" : atRisk > 0 ? "warn" : "ok";
}
function toneExceptions(n: number): Tone {
  return n >= 5 ? "danger" : n > 0 ? "warn" : "ok";
}

/** 0–100 network pressure index (higher = more heat). Matches Control Tower thresholds. */
export function computeOpsPressureScore(ops: {
  waiting: number;
  delayed: number;
  slaBreached: number;
  slaAtRisk: number;
  exceptions: number;
}): number {
  const score =
    Math.min(35, ops.waiting * 2.2) +
    Math.min(25, ops.delayed * 5) +
    Math.min(20, ops.slaBreached * 10) +
    Math.min(10, ops.slaAtRisk * 2) +
    Math.min(15, ops.exceptions * 3);
  return Math.round(Math.min(100, score));
}

function pressureLabel(score: number): { text: string; tone: Tone } {
  if (score >= 55) return { text: "Critical", tone: "danger" };
  if (score >= 25) return { text: "Elevated", tone: "warn" };
  return { text: "Calm", tone: "ok" };
}

/**
 * Ops pressure card — composite score + channel meters.
 * Replaces the polar radial chart (hard to read at zero / uneven scales).
 */
export function OpsPressureCard({ operations }: { operations: Record<string, unknown> }) {
  const waiting = Number(operations.waiting_dispatch ?? 0);
  const delayed = Number(operations.delayed_orders ?? 0);
  const slaBreached = Number(operations.sla_breached ?? 0);
  const slaAtRisk = Number(operations.sla_at_risk ?? 0);
  const exceptions = Number(operations.open_exceptions ?? 0);
  const slaTotal = slaBreached + slaAtRisk;

  const score = computeOpsPressureScore({
    waiting,
    delayed,
    slaBreached,
    slaAtRisk,
    exceptions,
  });
  const label = pressureLabel(score);

  const channels: Channel[] = [
    {
      id: "waiting",
      label: "Waiting dispatch",
      value: waiting,
      scale: 20,
      tone: toneWaiting(waiting),
      href: "/operations?view=desk",
      icon: ClipboardList,
    },
    {
      id: "delayed",
      label: "Delayed",
      value: delayed,
      scale: 8,
      tone: toneDelayed(delayed),
      href: "/operations?view=orders",
      icon: Zap,
    },
    {
      id: "sla",
      label: slaBreached > 0 ? `SLA (${slaBreached} breached)` : "SLA at risk",
      value: slaTotal,
      scale: 8,
      tone: toneSla(slaBreached, slaAtRisk),
      href: "/operations?view=attention",
      icon: Timer,
    },
    {
      id: "exceptions",
      label: "Exceptions",
      value: exceptions,
      scale: 8,
      tone: toneExceptions(exceptions),
      href: "/operations?view=attention",
      icon: AlertTriangle,
    },
  ];

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex items-center gap-3">
        <AnimatedRing value={score} max={100} label="Pressure" size={100} mode="pressure" />
        <div className="min-w-0">
          <p className={cn("text-sm font-semibold", TONE[label.tone].text)}>{label.text}</p>
          <p className="text-xs text-muted">
            Index <NumberTicker value={score} className="font-semibold text-primary" /> / 100
          </p>
          <Link
            href="/operations?view=attention"
            className="mt-1 inline-block text-xs font-medium text-secondary hover:underline"
          >
            Open Attention →
          </Link>
        </div>
      </div>

      <ul className="space-y-2.5">
        {channels.map((ch) => {
          const pct = Math.min(100, (ch.value / Math.max(ch.scale, 1)) * 100);
          const Icon = ch.icon;
          const t = TONE[ch.tone];
          return (
            <li key={ch.id}>
              <Link href={ch.href} className="group block">
                <div className="mb-0.5 flex items-center justify-between gap-2 text-xs">
                  <span className="flex items-center gap-1.5 text-muted group-hover:text-primary">
                    <Icon className={cn("h-3.5 w-3.5", t.text)} />
                    {ch.label}
                  </span>
                  <span className={cn("font-semibold tabular-nums", t.text)}>{ch.value}</span>
                </div>
                <div className={cn("h-1.5 overflow-hidden rounded-full", t.track)}>
                  <motion.div
                    className={cn("h-full rounded-full", t.bar)}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                  />
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
