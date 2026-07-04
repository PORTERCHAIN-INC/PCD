"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Download, RefreshCw, Search, Settings2, Upload } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Button, Spinner } from "@/components/crm/primitives";
import {
  CONFIG_SECTION_IDS,
  INTEGRATION_SECTION_IDS,
  MODULE_SECTION_LINKS,
  exportSettingsJson,
  settingsApi,
} from "@/lib/settings";
import { SECTION_DESCRIPTIONS, SECTION_ICONS } from "@/lib/settings-metadata";
import SettingsSidebar from "./SettingsSidebar";
import { MasterruleCallout } from "./ui/SettingsPrimitives";
import DashboardPanel from "./panels/DashboardPanel";
import ConfigFormPanel from "./panels/ConfigFormPanel";
import IntegrationPanel from "./panels/IntegrationPanel";
import VehiclesPanel from "./panels/VehiclesPanel";
import { RolesPanel, UsersPanel } from "./panels/AccessPanels";
import {
  AuditPanel,
  EnvManagedPanel,
  ModuleLinkPanel,
  PlatformPanel,
} from "./panels/PlatformPanels";

export default function SettingsCenter() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  const initialTab = searchParams.get("section") ?? "dashboard";
  const [tab, setTab] = useState(initialTab);
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);

  const {
    data: center,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["settings-center"],
    enabled,
    queryFn: async () => settingsApi.center(await getApiToken()),
    retry: 1,
  });

  const { data: searchHits = [] } = useQuery({
    queryKey: ["settings-search", search],
    enabled: enabled && search.length >= 2,
    queryFn: async () => settingsApi.search(await getApiToken(), search),
  });

  const selectTab = useCallback(
    (id: string) => {
      setTab(id);
      const params = new URLSearchParams(searchParams.toString());
      params.set("section", id);
      router.replace(`/settings?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<string>).detail;
      if (detail) selectTab(detail);
    };
    window.addEventListener("settings-navigate", handler);
    return () => window.removeEventListener("settings-navigate", handler);
  }, [selectTab]);

  useEffect(() => {
    const s = searchParams.get("section");
    if (s && s !== tab) setTab(s);
  }, [searchParams, tab]);

  const activeSection = useMemo(
    () => center?.sections.find((s) => s.id === tab),
    [center?.sections, tab]
  );

  const saveConfig = useCallback(
    async (key: string, value: unknown, reason: string) => {
      setSaving(true);
      try {
        const token = await getApiToken();
        await settingsApi.updateConfig(token, key, value, reason);
        await qc.invalidateQueries({ queryKey: ["settings-center"] });
      } finally {
        setSaving(false);
      }
    },
    [getApiToken, qc]
  );

  async function handleExport() {
    const data = await settingsApi.exportConfig(await getApiToken());
    exportSettingsJson(data);
  }

  async function handleImport() {
    const raw = prompt("Paste configuration JSON export");
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      const config = (parsed.config as Record<string, unknown>) ?? parsed;
      await settingsApi.importConfig(await getApiToken(), config, "Admin UI import");
      void refetch();
    } catch {
      window.alert("Invalid JSON");
    }
  }

  if (!enabled) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-8">
        <p className="font-semibold text-red-800">Failed to load settings center</p>
        <p className="mt-1 text-sm text-red-700">
          {error instanceof Error ? error.message : "Unknown error"}
        </p>
        <Button variant="outline" className="mt-4" onClick={() => void refetch()}>
          <RefreshCw className="h-4 w-4" /> Retry
        </Button>
      </div>
    );
  }

  if (isLoading && !center) {
    return (
      <div className="flex justify-center py-20">
        <Spinner label="Loading settings center…" />
      </div>
    );
  }

  const dash = center?.dashboard;
  const config = center?.config ?? {};
  const validation = center?.validation;
  const ActiveIcon = SECTION_ICONS[tab] ?? Settings2;

  return (
    <div className="space-y-6">
      {/* Hero header */}
      <div className="relative overflow-hidden rounded-2xl border border-primary/10 bg-gradient-to-br from-white via-white to-secondary/5 px-6 py-6 shadow-sm">
        <div className="relative z-10 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary/10">
                <Settings2 className="h-6 w-6 text-secondary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-primary">Settings Center</h1>
                <p className="text-sm text-muted">
                  Enterprise configuration for the entire Porterchain platform
                </p>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void refetch()}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
            <Button variant="outline" onClick={() => void handleExport()}>
              <Download className="h-4 w-4" /> Export
            </Button>
            <Button variant="outline" onClick={() => void handleImport()}>
              <Upload className="h-4 w-4" /> Import
            </Button>
          </div>
        </div>
      </div>

      <MasterruleCallout />

      {validation && (!validation.valid || validation.warnings.length > 0) && (
        <div
          className={cn(
            "rounded-xl border px-4 py-3 text-sm",
            validation.valid ? "border-amber-200 bg-amber-50" : "border-red-200 bg-red-50"
          )}
        >
          <p className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="h-4 w-4" />
            Configuration validation
          </p>
          {validation.issues.map((i) => (
            <p key={i} className="mt-1 text-red-700">
              {i}
            </p>
          ))}
          {validation.warnings.map((w) => (
            <p key={w} className="mt-1 text-amber-800">
              {w}
            </p>
          ))}
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search settings — users, fleetbase, booking, security…"
          className="w-full rounded-xl border border-primary/10 bg-white py-2.5 pl-10 pr-3 text-sm shadow-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20"
        />
        {searchHits.length > 0 && (
          <ul className="absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-primary/10 bg-white shadow-xl">
            {searchHits.map((h) => (
              <li key={`${h.type}-${h.id}`}>
                <button
                  type="button"
                  className="w-full px-4 py-2.5 text-left text-sm hover:bg-secondary/5"
                  onClick={() => {
                    selectTab(h.id);
                    setSearch("");
                  }}
                >
                  <span className="font-medium text-primary">{h.label}</span>
                  <span className="ml-2 text-xs text-muted">{h.type}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <aside className="hidden w-60 shrink-0 lg:block">
          <div className="sticky top-4 rounded-2xl border border-primary/10 bg-white p-3 shadow-sm">
            {center?.sections && (
              <SettingsSidebar sections={center.sections} activeId={tab} onSelect={selectTab} />
            )}
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <select
            value={tab}
            onChange={(e) => selectTab(e.target.value)}
            className="mb-4 w-full rounded-xl border border-primary/10 bg-white px-3 py-2.5 text-sm lg:hidden"
          >
            {center?.sections.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>

          <div className="mb-4 flex items-center gap-2 text-xs text-muted lg:hidden">
            <ActiveIcon className="h-4 w-4 text-secondary" />
            {activeSection?.label ?? tab}
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2 }}
              className="rounded-2xl border border-primary/10 bg-white p-5 shadow-sm md:p-6 lg:p-8"
            >
              <SectionRouter
                tab={tab}
                center={center}
                dash={dash}
                config={config}
                saving={saving}
                onSaveConfig={saveConfig}
                onRefetch={() => void refetch()}
                onExport={() => void handleExport()}
                onImport={() => void handleImport()}
              />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

function SectionRouter({
  tab,
  center,
  dash,
  config,
  saving,
  onSaveConfig,
  onRefetch,
  onExport,
  onImport,
}: {
  tab: string;
  center: Awaited<ReturnType<typeof settingsApi.center>> | undefined;
  dash: Awaited<ReturnType<typeof settingsApi.dashboard>> | undefined;
  config: Record<string, unknown>;
  saving: boolean;
  onSaveConfig: (key: string, value: unknown, reason: string) => Promise<void>;
  onRefetch: () => void;
  onExport: () => void;
  onImport: () => void;
}) {
  if (tab === "dashboard" && dash) return <DashboardPanel dash={dash} />;
  if (tab === "users" && center) return <UsersPanel onRefetch={onRefetch} />;
  if (tab === "roles" && center)
    return <RolesPanel permissions={center.permissions} roles={center.roles} />;
  if (tab === "audit") return <AuditPanel />;
  if (tab === "backup")
    return <PlatformPanel variant="backup" onExport={onExport} onImport={onImport} />;
  if (tab === "logs")
    return <PlatformPanel variant="logs" onExport={onExport} onImport={onImport} />;
  if (tab === "developer")
    return <PlatformPanel variant="developer" onExport={onExport} onImport={onImport} />;
  if (tab === "maintenance")
    return (
      <PlatformPanel variant="maintenance" dash={dash} onExport={onExport} onImport={onImport} />
    );

  if (tab === "api_keys" || tab === "integrations") return <EnvManagedPanel sectionId={tab} />;

  if ((INTEGRATION_SECTION_IDS as readonly string[]).includes(tab) && dash) {
    const health = dash.health as Record<string, unknown>;
    return <IntegrationPanel sectionId={tab} data={health[tab]} />;
  }

  if (tab === "vehicles") {
    const booking =
      typeof config.booking === "object" && config.booking !== null
        ? (config.booking as Record<string, unknown>)
        : undefined;
    return (
      <VehiclesPanel
        data={config.vehicles}
        defaultClass={
          typeof booking?.default_vehicle_class === "string"
            ? booking.default_vehicle_class
            : undefined
        }
        saving={saving}
        onSave={(value, reason) => onSaveConfig("vehicles", value, reason)}
      />
    );
  }

  if ((CONFIG_SECTION_IDS as readonly string[]).includes(tab)) {
    return (
      <ConfigFormPanel
        sectionId={tab}
        data={config[tab]}
        saving={saving}
        onSave={(value, reason) => onSaveConfig(tab, value, reason)}
      />
    );
  }

  if (tab in MODULE_SECTION_LINKS) {
    return <ModuleLinkPanel sectionId={tab} moduleConfig={center?.module_config} />;
  }

  return (
    <p className="text-sm text-muted">
      {SECTION_DESCRIPTIONS[tab] ?? "Select a section from the navigation."}
    </p>
  );
}
