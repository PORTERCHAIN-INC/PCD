"use client";

import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { healthTone } from "@/lib/settings";

export function StatusPill({ status }: { status: string }) {
  const tone = healthTone(status);
  const Icon =
    tone === "green"
      ? CheckCircle2
      : tone === "red"
        ? XCircle
        : tone === "amber"
          ? AlertTriangle
          : Info;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ring-1 ring-inset",
        tone === "green" && "bg-green-50 text-green-800 ring-green-600/20",
        tone === "amber" && "bg-amber-50 text-amber-900 ring-amber-600/20",
        tone === "red" && "bg-red-50 text-red-800 ring-red-600/20",
        tone === "gray" && "bg-slate-100 text-slate-700 ring-slate-500/20"
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {status}
    </span>
  );
}

export function SettingsPageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-primary/10 pb-5">
      <div className="min-w-0">
        <h2 className="text-xl font-bold tracking-tight text-primary">{title}</h2>
        {description && (
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function SettingsCard({
  title,
  description,
  action,
  children,
  className,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-2xl border border-primary/10 bg-white shadow-sm", className)}>
      {(title || action) && (
        <div className="flex items-start justify-between gap-3 border-b border-primary/10 px-5 py-4">
          <div>
            {title && <h3 className="text-sm font-semibold text-primary">{title}</h3>}
            {description && <p className="mt-0.5 text-xs text-muted">{description}</p>}
          </div>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function Toggle({
  checked,
  onChange,
  label,
  hint,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  hint?: string;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-xl border border-primary/10 bg-gray-bg/40 px-4 py-3">
      <div>
        <p className="text-sm font-medium text-primary">{label}</p>
        {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative h-6 w-11 shrink-0 rounded-full transition-colors",
          checked ? "bg-secondary" : "bg-primary/20"
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
            checked ? "translate-x-5" : "translate-x-0.5"
          )}
        />
      </button>
    </label>
  );
}

export function StatTile({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  sub?: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border px-4 py-3",
        tone === "default" && "border-primary/10 bg-white",
        tone === "success" && "border-green-200 bg-green-50/80",
        tone === "warning" && "border-amber-200 bg-amber-50/80",
        tone === "danger" && "border-red-200 bg-red-50/80"
      )}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-lg font-bold text-primary">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </div>
  );
}

export function MasterruleCallout() {
  return (
    <div className="flex gap-3 rounded-xl border border-secondary/20 bg-secondary/5 px-4 py-3 text-xs text-primary/80">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
      <p>
        <span className="font-semibold text-primary">Architecture policy:</span> Runtime settings
        are stored in Porterchain <code className="rounded bg-white px-1">SystemConfig</code>.
        Secrets and API keys remain in environment variables — this UI shows status only, never
        credentials. Business logic stays in Application Services per masterrule §3.
      </p>
    </div>
  );
}
