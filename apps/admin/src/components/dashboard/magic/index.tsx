"use client";

import { useEffect, useRef } from "react";
import { motion, useInView, useMotionValue, useSpring } from "framer-motion";
import { cn } from "@porterchain/ui/utils";

/** Magic UI–style counting number (framer-motion spring). */
export function NumberTicker({
  value,
  className,
  decimalPlaces = 0,
  prefix = "",
  suffix = "",
}: {
  value: number;
  className?: string;
  decimalPlaces?: number;
  prefix?: string;
  suffix?: string;
}) {
  const safe = Number.isFinite(value) ? value : 0;
  const ref = useRef<HTMLSpanElement>(null);
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { damping: 40, stiffness: 120 });
  const inView = useInView(ref, { once: true, margin: "-40px" });

  useEffect(() => {
    if (inView) motionValue.set(safe);
  }, [inView, motionValue, safe]);

  useEffect(() => {
    const unsub = spring.on("change", (latest) => {
      if (!ref.current) return;
      ref.current.textContent = `${prefix}${latest.toLocaleString("en-CA", {
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces,
      })}${suffix}`;
    });
    return unsub;
  }, [spring, decimalPlaces, prefix, suffix]);

  return (
    <span ref={ref} className={cn("tabular-nums", className)}>
      {prefix}
      {safe.toLocaleString("en-CA", {
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces,
      })}
      {suffix}
    </span>
  );
}

/** Soft cursor spotlight card — PorterChain blue (#2563eb), not Magic UI purple. */
export function SpotlightCard({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--spot-x", `${e.clientX - rect.left}px`);
    el.style.setProperty("--spot-y", `${e.clientY - rect.top}px`);
  }

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-primary/10 bg-white",
        "before:pointer-events-none before:absolute before:inset-0 before:opacity-0 before:transition-opacity",
        "before:bg-[radial-gradient(420px_circle_at_var(--spot-x,50%)_var(--spot-y,50%),rgba(37,99,235,0.12),transparent_55%)]",
        "hover:before:opacity-100",
        className
      )}
    >
      <div className="relative z-10 h-full">{children}</div>
    </div>
  );
}

export function BentoGrid({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid auto-rows-auto grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4",
        className
      )}
    >
      {children}
    </div>
  );
}

export function BentoCell({
  children,
  className,
  span = 1,
}: {
  children: React.ReactNode;
  className?: string;
  span?: 1 | 2;
}) {
  return (
    <SpotlightCard className={cn(span === 2 && "md:col-span-2", "p-4", className)}>
      {children}
    </SpotlightCard>
  );
}

/** SVG circular progress — Magic UI vibe without extra deps. */
export function AnimatedRing({
  value,
  max = 100,
  label,
  size = 120,
  /** health = high is good (green); pressure = high is bad (red). */
  mode = "health",
}: {
  value: number;
  max?: number;
  label: string;
  size?: number;
  mode?: "health" | "pressure";
}) {
  const pct = Math.max(0, Math.min(100, (value / Math.max(max, 1)) * 100));
  const r = 40;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const stroke = size >= 150 ? 11 : size >= 130 ? 10 : 9;
  const valueClass =
    size >= 150
      ? "text-3xl font-bold text-primary"
      : size >= 130
        ? "text-2xl font-bold text-primary"
        : "text-lg font-bold text-primary";
  const labelClass =
    size >= 150
      ? "max-w-[7rem] text-center text-xs leading-tight text-muted"
      : "max-w-[5.5rem] text-center text-[10px] leading-tight text-muted";
  const tone =
    mode === "pressure"
      ? pct >= 55
        ? "#ef4444"
        : pct >= 25
          ? "#f59e0b"
          : "#10b981"
      : pct >= 85
        ? "#10b981"
        : pct >= 60
          ? "#2563eb"
          : "#f59e0b";

  return (
    <div className="relative inline-flex" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 100 100" className="-rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        <motion.circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke={tone}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.9, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-0.5">
        <NumberTicker value={Math.round(pct)} suffix="%" className={valueClass} />
        <span className={labelClass}>{label}</span>
      </div>
    </div>
  );
}
