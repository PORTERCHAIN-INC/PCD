"use client";

import { PRETRIP_ITEMS, type PretripChecks } from "@/lib/pretrip";
import { cn } from "@/lib/utils";

export function PretripGate({
  checks,
  onChange,
}: {
  checks: PretripChecks;
  onChange: (next: PretripChecks) => void;
}) {
  return (
    <div
      className="rounded-2xl border border-[var(--primary)]/10 bg-white p-5 shadow-sm"
      data-testid="pretrip-check"
    >
      <h2 className="text-lg font-bold">30-second pre-trip</h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Lights, tires, plates, leaks, winter kit — then start shift.
      </p>
      <ul className="mt-4 space-y-2">
        {PRETRIP_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onChange({ ...checks, [item.id]: !checks[item.id] })}
              className={cn(
                "flex w-full items-center justify-between rounded-xl px-4 py-3 text-sm font-medium",
                checks[item.id]
                  ? "bg-emerald-50 text-emerald-800"
                  : "bg-[var(--gray-bg)] text-[var(--primary)]"
              )}
            >
              <span>{item.label}</span>
              <span aria-hidden>{checks[item.id] ? "✓" : ""}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
