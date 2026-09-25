"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Activity, HeartPulse, Sparkles } from "lucide-react";
import { DiagnosticsAiUsageView } from "@/components/diagnostics/DiagnosticsAiUsageView";
import { DiagnosticsHealthView } from "@/components/diagnostics/DiagnosticsHealthView";
import { DiagnosticsTestCenter } from "@/components/diagnostics/DiagnosticsTestCenter";
import { SettingsPageHeader } from "@/components/settings/ui/SettingsPrimitives";
import { cn } from "@porterchain/ui/utils";
import AdminPage from "@/components/layout/AdminPage";

type SystemTab = "health" | "tests" | "ai";

const TABS: { id: SystemTab; label: string; description: string; icon: typeof HeartPulse }[] = [
  {
    id: "health",
    label: "Health",
    description: "Live status of portals, engines, and infrastructure",
    icon: HeartPulse,
  },
  {
    id: "tests",
    label: "Tests",
    description: "Integration, E2E, architecture, and chaos suites",
    icon: Activity,
  },
  {
    id: "ai",
    label: "AI usage",
    description: "NVIDIA NIM metering and phase2 flags",
    icon: Sparkles,
  },
];

function tabFromQuery(raw: string | null): SystemTab {
  if (raw === "tests") return "tests";
  if (raw === "ai") return "ai";
  return "health";
}

export function SystemCenter() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<SystemTab>(() => tabFromQuery(searchParams.get("tab")));

  useEffect(() => {
    setTab(tabFromQuery(searchParams.get("tab")));
  }, [searchParams]);

  function selectTab(next: SystemTab) {
    setTab(next);
    const params = new URLSearchParams(searchParams.toString());
    if (next === "health") params.delete("tab");
    else params.set("tab", next);
    const q = params.toString();
    router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
  }

  return (
    <AdminPage>
      <SettingsPageHeader
        title="System"
        description="Platform health, validation, and AI usage — live probes and metering in one place."
      />

      <div className="flex flex-wrap gap-2">
        {TABS.map(({ id, label, description, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => selectTab(id)}
            className={cn(
              "flex min-w-[12rem] flex-1 flex-col items-start gap-1 rounded-2xl border px-4 py-3 text-left transition sm:flex-none",
              tab === id
                ? "border-secondary/40 bg-secondary text-white shadow-sm"
                : "border-primary/10 bg-white text-primary hover:bg-gray-bg"
            )}
          >
            <span className="inline-flex items-center gap-2 text-sm font-semibold">
              <Icon className="h-4 w-4" />
              {label}
            </span>
            <span className={cn("text-xs", tab === id ? "text-white/80" : "text-muted")}>
              {description}
            </span>
          </button>
        ))}
      </div>

      {tab === "health" ? (
        <DiagnosticsHealthView embedded onOpenTests={() => selectTab("tests")} />
      ) : tab === "tests" ? (
        <DiagnosticsTestCenter embedded onOpenHealth={() => selectTab("health")} />
      ) : (
        <DiagnosticsAiUsageView embedded />
      )}
    </AdminPage>
  );
}
