"use client";

import { ExternalLink, Loader2, Truck } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { useOptionalSessionContext } from "@porterchain/auth";
import { useFleetbaseSso } from "@/hooks/useFleetbaseSso";
import { canOpenFleetbaseConsole } from "@/lib/fleetbase-access";

type Variant = "header" | "menu" | "toolbar" | "inline";

type Props = {
  variant?: Variant;
  className?: string;
  /** When false, always render (caller already gated). Default: hide if role ineligible. */
  respectRole?: boolean;
};

function resolveRole(
  profileRole: string | null | undefined,
  sessionRoles: string[] | undefined
): string | null {
  if (profileRole && profileRole.toLowerCase() !== "staff") return profileRole;
  return sessionRoles?.[0] ?? null;
}

export default function OpenFleetbaseButton({
  variant = "toolbar",
  className,
  respectRole = true,
}: Props) {
  const { profile } = useAdminProfile();
  const session = useOptionalSessionContext()?.session;
  const { openConsole, loading, error, clearError } = useFleetbaseSso();
  const role = resolveRole(profile?.role, session?.roles);

  if (respectRole && !canOpenFleetbaseConsole(role)) {
    return null;
  }

  if (variant === "header") {
    return (
      <div className={cn("relative", className)}>
        <button
          type="button"
          disabled={loading}
          onClick={() => {
            clearError();
            void openConsole();
          }}
          title="Open Fleetbase execution console (same staff session)"
          aria-label="Open Fleetbase execution console"
          className={cn(
            "inline-flex h-10 items-center gap-2 rounded-full border border-primary/10 bg-white px-3 text-sm font-semibold text-primary shadow-sm transition",
            "hover:border-secondary/30 hover:bg-secondary/5",
            "disabled:cursor-wait disabled:opacity-60"
          )}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin text-secondary" />
          ) : (
            <Truck className="h-4 w-4 text-secondary" />
          )}
          <span className="hidden sm:inline">{loading ? "Opening…" : "Execution"}</span>
        </button>
        {error && (
          <p className="absolute right-0 top-full z-50 mt-1 w-56 rounded-lg border border-red-200 bg-white px-2.5 py-1.5 text-[11px] text-red-700 shadow-sm">
            {error}
          </p>
        )}
      </div>
    );
  }

  if (variant === "menu") {
    return (
      <div className={className}>
        <button
          type="button"
          disabled={loading}
          onClick={() => {
            clearError();
            void openConsole();
          }}
          className="flex w-full items-start gap-3 rounded-xl border border-secondary/15 bg-secondary/5 px-3 py-3 text-left transition hover:bg-secondary/10 disabled:opacity-60"
        >
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary text-white">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Truck className="h-4 w-4" />}
          </span>
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-1.5 text-sm font-semibold text-primary">
              {loading ? "Opening Fleetbase…" : "Open Fleetbase console"}
              <ExternalLink className="h-3.5 w-3.5 text-secondary" />
            </span>
            <span className="mt-0.5 block text-xs leading-snug text-muted">
              Same staff session · dispatch, GPS, routes · no second login
            </span>
          </span>
        </button>
        {error && <p className="mt-1.5 px-1 text-xs text-red-600">{error}</p>}
      </div>
    );
  }

  if (variant === "inline") {
    return (
      <span className={className}>
        <button
          type="button"
          disabled={loading}
          onClick={() => {
            clearError();
            void openConsole();
          }}
          className="font-medium text-secondary underline decoration-secondary/30 underline-offset-2 hover:decoration-secondary disabled:opacity-60"
        >
          {loading ? "Opening…" : "Fleetbase console"}
        </button>
        {error && <span className="ml-2 text-xs text-red-600">{error}</span>}
      </span>
    );
  }

  // toolbar
  return (
    <div className={cn("inline-flex flex-col items-end gap-1", className)}>
      <button
        type="button"
        disabled={loading}
        onClick={() => {
          clearError();
          void openConsole();
        }}
        className={cn(
          "inline-flex items-center gap-2 rounded-xl bg-secondary px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition",
          "hover:bg-secondary/90 disabled:cursor-wait disabled:opacity-60"
        )}
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Truck className="h-4 w-4" />}
        {loading ? "Opening…" : "Open Fleetbase"}
        {!loading && <ExternalLink className="h-3.5 w-3.5 opacity-80" />}
      </button>
      {error && <p className="max-w-xs text-right text-xs text-red-600">{error}</p>}
    </div>
  );
}
