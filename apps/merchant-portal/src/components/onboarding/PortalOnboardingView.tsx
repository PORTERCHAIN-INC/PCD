"use client";

import { CheckCircle2, Circle, Clock, LogOut, RefreshCw, Shield, XCircle } from "lucide-react";
import { SignOutButton } from "@clerk/nextjs";
import type { PortalOnboardingStatus } from "@/lib/onboarding";
import { cn } from "@/lib/utils";
import { useState } from "react";

function stepIcon(step: PortalOnboardingStatus["steps"][number]) {
  if (step.complete) return <CheckCircle2 className="h-5 w-5 text-emerald-600" />;
  if (step.status === "suspended" || step.status === "inactive") {
    return <XCircle className="h-5 w-5 text-red-600" />;
  }
  if (
    step.status === "pending_review" ||
    step.status === "onboarding" ||
    step.status === "pending"
  ) {
    return <Clock className="h-5 w-5 text-amber-600" />;
  }
  return <Circle className="h-5 w-5 text-muted" />;
}

function statusLabel(step: PortalOnboardingStatus["steps"][number]) {
  if (step.complete) return "Complete";
  if (step.status === "onboarding") return "Onboarding in progress";
  if (step.status === "suspended") return "Suspended";
  if (step.status === "inactive") return "Access revoked";
  if (step.status === "pending") return "Pending";
  return "Awaiting review";
}

export default function PortalOnboardingView({
  data,
  refreshing,
  onRefresh,
  onSaveVertical,
}: {
  data: PortalOnboardingStatus;
  refreshing?: boolean;
  onRefresh: () => void;
  onSaveVertical?: (vertical: string) => Promise<void>;
}) {
  const [savingVertical, setSavingVertical] = useState(false);
  const [verticalError, setVerticalError] = useState<string | null>(null);
  const verticalStep = data.steps.find((s) => s.id === "business_vertical");
  const showVerticalPicker =
    verticalStep && !verticalStep.complete && (data.vertical_options?.length ?? 0) > 0;

  const completed = data.steps.filter((s) => s.complete).length;
  const total = data.steps.length;
  const progress = total ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="min-h-dvh bg-gray-bg">
      <header className="border-b border-primary/10 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary text-sm font-bold text-white">
              P
            </span>
            <div>
              <p className="text-sm font-bold text-primary">Porterchain Merchant</p>
              <p className="text-xs text-muted">Account activation</p>
            </div>
          </div>
          <SignOutButton redirectUrl="/sign-in">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-xl border border-primary/10 px-3 py-2 text-sm text-muted"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </SignOutButton>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-50">
              <Shield className="h-6 w-6 text-amber-700" />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-bold text-primary">Activation in progress</h1>
              <p className="mt-2 text-sm text-muted">
                Merchant access is invitation-only. Complete each step below — your dashboard stays
                locked until Porterchain activates your business account.
              </p>
              {data.company_name ? (
                <p className="mt-2 text-sm font-medium text-primary">{data.company_name}</p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={onRefresh}
              disabled={refreshing}
              className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-primary/10 px-3 py-2 text-sm"
            >
              <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
              Refresh
            </button>
          </div>

          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-medium text-primary">Progress</span>
              <span className="text-muted">
                {completed}/{total} steps
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-bg">
              <div
                className="h-full rounded-full bg-secondary transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>

        {showVerticalPicker && onSaveVertical ? (
          <div className="mt-6 rounded-2xl border border-secondary/20 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-primary">Select your business vertical</h2>
            <p className="mt-1 text-sm text-muted">
              Porterchain tailors booking fields, pricing, and ops workflows to your industry.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {data.vertical_options!.map((option) => (
                <button
                  key={option.slug}
                  type="button"
                  disabled={savingVertical}
                  onClick={async () => {
                    setVerticalError(null);
                    setSavingVertical(true);
                    try {
                      await onSaveVertical(option.slug);
                    } catch (err) {
                      setVerticalError(err instanceof Error ? err.message : "vertical_save_failed");
                    } finally {
                      setSavingVertical(false);
                    }
                  }}
                  className={cn(
                    "rounded-xl border px-4 py-3 text-left text-sm transition-colors",
                    data.vertical === option.slug
                      ? "border-secondary bg-secondary/5 font-semibold text-primary"
                      : "border-primary/10 hover:border-secondary/40"
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
            {verticalError ? (
              <p className="mt-3 text-sm text-red-600" role="alert">
                {verticalError}
              </p>
            ) : null}
          </div>
        ) : null}

        <ol className="mt-6 space-y-3">
          {data.steps.map((step) => (
            <li
              key={step.id}
              className={cn(
                "rounded-2xl border bg-white p-5 shadow-sm",
                step.complete
                  ? "border-emerald-100"
                  : step.status === "onboarding" || step.status === "pending"
                    ? "border-amber-100"
                    : "border-primary/8"
              )}
            >
              <div className="flex items-start gap-3">
                {stepIcon(step)}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-semibold text-primary">{step.label}</h2>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        step.complete ? "bg-emerald-50 text-emerald-700" : "bg-gray-bg text-muted"
                      )}
                    >
                      {statusLabel(step)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-muted">{step.description}</p>
                </div>
              </div>
            </li>
          ))}
        </ol>

        {data.ready ? (
          <div className="mt-6 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            All requirements met — opening your merchant portal…
          </div>
        ) : (
          <p className="mt-6 text-center text-xs text-muted">
            Need an invite? Contact your Porterchain account manager. Status refreshes every 30
            seconds.
          </p>
        )}
      </main>
    </div>
  );
}
