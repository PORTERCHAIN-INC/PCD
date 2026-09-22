"use client";

import Link from "next/link";
import {
  CheckCircle2,
  Circle,
  Clock,
  FileText,
  LogOut,
  RefreshCw,
  Shield,
  UserCheck,
  XCircle,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { driverApi } from "@/lib/api";
import type { DriverOnboardingStatus } from "@/lib/onboarding";
import { cn } from "@/lib/utils";

function stepIcon(step: DriverOnboardingStatus["steps"][number]) {
  if (step.complete) return <CheckCircle2 className="h-5 w-5 text-emerald-600" />;
  if (step.status === "rejected" || step.status === "suspended") {
    return <XCircle className="h-5 w-5 text-red-600" />;
  }
  if (step.status === "pending_review") {
    return <Clock className="h-5 w-5 text-amber-600" />;
  }
  return <Circle className="h-5 w-5 text-[var(--muted)]" />;
}

function statusLabel(step: DriverOnboardingStatus["steps"][number]) {
  if (step.complete) return "Complete";
  if (step.status === "pending_review") return "Awaiting admin review";
  if (step.status === "rejected") return "Rejected";
  if (step.status === "suspended") return "Suspended";
  if (step.id === "documents_uploaded" && step.missing?.length) {
    return `Missing: ${step.missing.join(", ").replaceAll("_", " ")}`;
  }
  return "Pending";
}

export default function DriverOnboardingView({
  data,
  refreshing,
  onRefresh,
}: {
  data: DriverOnboardingStatus;
  refreshing?: boolean;
  onRefresh: () => void;
}) {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  const logout = async () => {
    setSigningOut(true);
    try {
      await driverApi.logout();
      router.replace("/login");
    } finally {
      setSigningOut(false);
    }
  };

  const completed = data.steps.filter((s) => s.complete).length;
  const total = data.steps.length;
  const progress = total ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="min-h-dvh bg-[var(--gray-bg)]">
      <header className="border-b border-[var(--primary)]/10 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--secondary)] text-sm font-bold text-white">
              P
            </span>
            <div>
              <p className="text-sm font-bold text-[var(--primary)]">Porterchain Driver</p>
              <p className="text-xs text-[var(--muted)]">Account activation</p>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            disabled={signingOut}
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm text-[var(--muted)]"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-50">
              <Shield className="h-6 w-6 text-amber-700" />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-bold text-[var(--primary)]">Activation in progress</h1>
              <p className="mt-2 text-sm text-[var(--muted)]">
                Your driver account is not fully authorized yet. Complete each step below. The
                dashboard stays locked until operations approves everything.
              </p>
            </div>
            <button
              type="button"
              onClick={onRefresh}
              disabled={refreshing}
              className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
            >
              <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
              Refresh
            </button>
          </div>

          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-medium text-[var(--primary)]">Progress</span>
              <span className="text-[var(--muted)]">
                {completed}/{total} steps
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-[var(--gray-bg)]">
              <div
                className="h-full rounded-full bg-[var(--secondary)] transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>

        <ol className="mt-6 space-y-3">
          {data.steps.map((step) => (
            <li
              key={step.id}
              className={cn(
                "rounded-2xl border bg-white p-5 shadow-sm",
                step.complete
                  ? "border-emerald-100"
                  : step.status === "pending_review"
                    ? "border-amber-100"
                    : "border-[var(--primary)]/8"
              )}
            >
              <div className="flex items-start gap-3">
                {stepIcon(step)}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-semibold text-[var(--primary)]">{step.label}</h2>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        step.complete
                          ? "bg-emerald-50 text-emerald-700"
                          : step.status === "pending_review"
                            ? "bg-amber-50 text-amber-800"
                            : "bg-[var(--gray-bg)] text-[var(--muted)]"
                      )}
                    >
                      {statusLabel(step)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-[var(--muted)]">{step.description}</p>
                  {step.reason ? <p className="mt-2 text-sm text-red-700">{step.reason}</p> : null}
                </div>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <Link
            href="/profile"
            className="flex items-center gap-3 rounded-2xl border border-[var(--primary)]/10 bg-white p-4 shadow-sm hover:border-[var(--secondary)]/30"
          >
            <FileText className="h-5 w-5 text-[var(--secondary)]" />
            <div>
              <p className="font-semibold text-[var(--primary)]">Upload documents</p>
              <p className="text-xs text-[var(--muted)]">Profile & compliance</p>
            </div>
          </Link>
          <div className="flex items-center gap-3 rounded-2xl border border-dashed border-[var(--primary)]/15 bg-white/60 p-4">
            <UserCheck className="h-5 w-5 text-[var(--muted)]" />
            <div>
              <p className="font-semibold text-[var(--primary)]">Need help?</p>
              <p className="text-xs text-[var(--muted)]">
                Contact operations after you submit docs
              </p>
            </div>
          </div>
        </div>

        {data.ready ? (
          <div className="mt-6 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            All requirements met — opening your dashboard…
          </div>
        ) : (
          <p className="mt-6 text-center text-xs text-[var(--muted)]">
            Status refreshes automatically every 30 seconds.
          </p>
        )}
      </main>
    </div>
  );
}
