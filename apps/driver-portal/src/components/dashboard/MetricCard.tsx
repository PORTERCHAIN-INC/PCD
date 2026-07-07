import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = false,
  className,
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: LucideIcon;
  accent?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border bg-white p-4 shadow-sm transition-shadow hover:shadow-md",
        accent
          ? "border-[var(--secondary)]/30 ring-1 ring-[var(--secondary)]/10"
          : "border-transparent",
        className
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">{label}</p>
        {Icon && (
          <span
            className={cn(
              "rounded-lg p-1.5",
              accent
                ? "bg-[var(--secondary)]/10 text-[var(--secondary)]"
                : "bg-[var(--gray-bg)] text-[var(--primary)]/60"
            )}
          >
            <Icon className="h-4 w-4" />
          </span>
        )}
      </div>
      <p className="mt-2 text-2xl font-bold tracking-tight text-[var(--primary)]">{value}</p>
      {hint && <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p>}
    </div>
  );
}
