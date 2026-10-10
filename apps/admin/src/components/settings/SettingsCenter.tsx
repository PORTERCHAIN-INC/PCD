"use client";

import CarriageTermsPanel from "@/components/settings/CarriageTermsPanel";
import RoutePricingPanel from "@/components/settings/RoutePricingPanel";
import { startTransition, useCallback, useEffect, useMemo, useOptimistic, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Download, RefreshCw, Search, Settings2, Upload } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import AdminPage from "@/components/layout/AdminPage";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Button } from "@/components/crm/primitives";
import {
  CONFIG_SECTION_IDS,
  ENV_OWNED_SECTION_IDS,
  INTEGRATION_SECTION_IDS,
  exportSettingsJson,
  settingsApi,
  type SettingsCenter as SettingsCenterData,
} from "@/lib/settings";
import { SECTION_ALIASES, SECTION_DESCRIPTIONS, SECTION_ICONS } from "@/lib/settings-metadata";
import { withStaffStepUp } from "@/lib/staff-step-up";
import SettingsSidebar from "./SettingsSidebar";
import { MasterruleCallout } from "./ui/SettingsPrimitives";
import { PageSkeleton } from "@porterchain/ui/loading";
import dynamic from "next/dynamic";

const panelFallback = () => (
  <div className="py-6">
    <PageSkeleton rows={4} />
  </div>
);

const DashboardPanel = dynamic(() => import("./panels/DashboardPanel"), {
  loading: panelFallback,
});
const ConfigFormPanel = dynamic(() => import("./panels/ConfigFormPanel"), {
  loading: panelFallback,
});
const IntegrationPanel = dynamic(() => import("./panels/IntegrationPanel"), {
  loading: panelFallback,
});
const VehiclesPanel = dynamic(() => import("./panels/VehiclesPanel"), {
  loading: panelFallback,
});
const PricingPanel = dynamic(() => import("./panels/PricingPanel"), {
  loading: panelFallback,
});
const CoveragePanel = dynamic(() => import("./panels/CoveragePanel"), {
  loading: panelFallback,
});
const EnvOwnedPanel = dynamic(() => import("./panels/EnvOwnedPanel"), {
  loading: panelFallback,
});
const LeadIngestPanel = dynamic(() => import("./panels/LeadIngestPanel"), {
  loading: panelFallback,
});
const RolesPanel = dynamic(
  () => import("./panels/RolesPanel").then((m) => ({ default: m.RolesPanel })),
  { loading: panelFallback }
);
const UsersPanel = dynamic(
  () => import("./panels/users/UsersPanel").then((m) => ({ default: m.UsersPanel })),
  { loading: panelFallback }
);
const AuditPanel = dynamic(
  () => import("./panels/PlatformPanels").then((m) => ({ default: m.AuditPanel })),
  { loading: panelFallback }
);
const PlatformPanel = dynamic(
  () => import("./panels/PlatformPanels").then((m) => ({ default: m.PlatformPanel })),
  { loading: panelFallback }
);
const ImportConfigModal = dynamic(
  () => import("./panels/ImportConfigModal").then((m) => ({ default: m.ImportConfigModal })),
  { ssr: false }
);

function resolveSection(raw: string | null): string {
  const id = raw ?? "dashboard";
  return SECTION_ALIASES[id] ?? id;
}

export default function SettingsCenter() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  const [tab, setTab] = useState(() => resolveSection(searchParams.get("section")));
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [searchActive, setSearchActive] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

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

  const [optimisticCenter, applyOptimisticConfig] = useOptimistic(
    center,
    (current, update: { key: string; value: unknown }) => {
      if (!current) return current;
      return {
        ...current,
        config: { ...current.config, [update.key]: update.value },
      };
    }
  );
  const paintCenter = optimisticCenter ?? center;

  const { data: searchHits = [] } = useQuery({
    queryKey: ["settings-search", search],
    enabled: enabled && search.length >= 2,
    queryFn: async () => settingsApi.search(await getApiToken(), search),
  });

  const selectTab = useCallback(
    (id: string) => {
      const next = resolveSection(id);
      if (dirty && next !== tab) {
        if (!window.confirm("Discard unsaved changes in this section?")) return;
        setDirty(false);
      }
      setTab(next);
      const params = new URLSearchParams(searchParams.toString());
      params.set("section", next);
      router.replace(`/settings?${params.toString()}`, { scroll: false });
    },
    [router, searchParams, dirty, tab]
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
    const s = resolveSection(searchParams.get("section"));
    if (s && s !== tab) setTab(s);
  }, [searchParams, tab]);

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  const activeSection = useMemo(
    () => paintCenter?.sections.find((s) => s.id === tab),
    [paintCenter?.sections, tab]
  );

  const bindingEffect = useMemo(() => {
    const b = paintCenter?.bindings?.bindings.find((x) => x.id === tab);
    return b?.effect ?? "status";
  }, [paintCenter?.bindings, tab]);

  const saveConfig = useCallback(
    async (key: string, value: unknown, reason: string) => {
      setSaving(true);
      setToast(null);
      const previous = qc.getQueryData<SettingsCenterData>(["settings-center"]);
      startTransition(() => {
        applyOptimisticConfig({ key, value });
      });
      if (previous) {
        qc.setQueryData<SettingsCenterData>(["settings-center"], {
          ...previous,
          config: { ...previous.config, [key]: value },
        });
      }
      try {
        const token = await getApiToken();
        await withStaffStepUp(token, () => settingsApi.updateConfig(token, key, value, reason));
        await qc.invalidateQueries({ queryKey: ["settings-center"] });
        setDirty(false);
        setToast("Saved");
      } catch (e) {
        if (previous) qc.setQueryData(["settings-center"], previous);
        setToast(e instanceof Error ? e.message : "Save failed");
        throw e;
      } finally {
        setSaving(false);
      }
    },
    [applyOptimisticConfig, getApiToken, qc]
  );

  async function handleExport() {
    const data = await settingsApi.exportConfig(await getApiToken());
    exportSettingsJson(data);
  }

  if (!center && !enabled) {
    return (
      <div className="py-6">
        <PageSkeleton rows={4} />
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
      <div className="py-6">
        <PageSkeleton rows={6} />
      </div>
    );
  }

  const dash = paintCenter?.dashboard;
  const config = paintCenter?.config ?? {};
  const validation = paintCenter?.validation;
  const ActiveIcon = SECTION_ICONS[tab] ?? Settings2;

  return (
    <AdminPage>
      <div className="relative overflow-hidden rounded-2xl border border-primary/10 bg-gradient-to-br from-white via-white to-secondary/5 px-4 py-5 shadow-sm sm:px-6 sm:py-6">
        <div className="relative z-10 flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary/10">
              <Settings2 className="h-6 w-6 text-secondary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-primary">Settings</h1>
              <p className="text-sm text-muted">
                Commercial catalog, access, and connection status
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void refetch()}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
            <Button variant="outline" onClick={() => void handleExport()}>
              <Download className="h-4 w-4" /> Export
            </Button>
            <Button variant="outline" onClick={() => setImportOpen(true)}>
              <Upload className="h-4 w-4" /> Import
            </Button>
          </div>
        </div>
      </div>

      <MasterruleCallout />

      {toast && (
        <p className="rounded-xl border border-secondary/20 bg-secondary/5 px-3 py-2 text-sm text-primary">
          {toast}
        </p>
      )}

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

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          type="search"
          role="combobox"
          aria-expanded={searchActive && search.length >= 2}
          aria-controls="settings-search-listbox"
          aria-autocomplete="list"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setSearchActive(true);
          }}
          onFocus={() => setSearchActive(true)}
          onBlur={() => window.setTimeout(() => setSearchActive(false), 150)}
          placeholder="Search settings — SLA, downtown, vehicles, dispatch…"
          className="w-full rounded-xl border border-primary/10 bg-white py-2.5 pl-10 pr-3 text-sm shadow-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20"
        />
        {searchActive && search.length >= 2 && (
          <ul
            id="settings-search-listbox"
            role="listbox"
            className="absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-primary/10 bg-white shadow-xl"
          >
            {searchHits.length === 0 && (
              <li className="px-4 py-3 text-sm text-muted">No matching settings</li>
            )}
            {searchHits.map((h) => (
              <li key={`${h.type}-${h.id}`} role="option">
                <button
                  type="button"
                  className="w-full px-4 py-2.5 text-left text-sm hover:bg-secondary/5"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    selectTab(h.id);
                    setSearch("");
                    setSearchActive(false);
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

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        <aside className="hidden w-60 shrink-0 lg:block">
          <div className="sticky top-4 max-h-[calc(100vh-6rem)] overflow-y-auto rounded-2xl border border-primary/10 bg-white p-3 shadow-sm">
            {paintCenter?.sections && (
              <SettingsSidebar
                sections={paintCenter.sections}
                activeId={tab}
                onSelect={selectTab}
              />
            )}
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <select
            value={tab}
            onChange={(e) => selectTab(e.target.value)}
            className="mb-4 min-h-11 w-full rounded-xl border border-primary/10 bg-white px-3 py-2.5 text-sm lg:hidden"
          >
            {paintCenter?.sections.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>

          <div className="mb-4 flex items-center gap-2 text-xs text-muted lg:hidden">
            <ActiveIcon className="h-4 w-4 text-secondary" />
            {activeSection?.label ?? tab}
          </div>

          <div
            key={tab}
            className="min-w-0 overflow-x-auto rounded-2xl border border-primary/10 bg-white p-4 shadow-sm sm:p-5 md:p-6 lg:p-8"
          >
            <SectionRouter
              tab={tab}
              center={paintCenter}
              dash={dash}
              config={config}
              saving={saving}
              bindingEffect={bindingEffect}
              onDirty={() => setDirty(true)}
              onSaveConfig={saveConfig}
              onRefetch={() => void refetch()}
              onExport={() => void handleExport()}
              onImport={() => setImportOpen(true)}
            />
          </div>
        </main>
      </div>

      <ImportConfigModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={() => {
          setToast("Configuration imported");
          void refetch();
        }}
      />
    </AdminPage>
  );
}

function SectionRouter({
  tab,
  center,
  dash,
  config,
  saving,
  bindingEffect,
  onSaveConfig,
  onRefetch,
  onExport,
  onImport,
}: {
  tab: string;
  center: SettingsCenterData | undefined;
  dash: SettingsCenterData["dashboard"] | undefined;
  config: Record<string, unknown>;
  saving: boolean;
  bindingEffect: string;
  onDirty: () => void;
  onSaveConfig: (key: string, value: unknown, reason: string) => Promise<void>;
  onRefetch: () => void;
  onExport: () => void;
  onImport: () => void;
}) {
  if (tab === "dashboard" && dash)
    return <DashboardPanel dash={dash} validation={center?.validation} />;
  if (tab === "users") return <UsersPanel onRefetch={onRefetch} />;
  if (tab === "roles") return <RolesPanel />;
  if (tab === "audit") return <AuditPanel />;
  if (tab === "backup")
    return <PlatformPanel variant="backup" onExport={onExport} onImport={onImport} />;

  if ((ENV_OWNED_SECTION_IDS as readonly string[]).includes(tab)) {
    return <EnvOwnedPanel sectionId={tab} />;
  }

  if (tab === "carriage") return <CarriageTermsPanel />;
  if (tab === "route_pricing") return <RoutePricingPanel />;
  if (tab === "lead_ingest") {
    return <LeadIngestPanel />;
  }

  if (tab === "channels" && dash) {
    return (
      <IntegrationPanel
        sectionId="channels"
        data={{
          email: dash.health.email,
          sms: dash.health.sms,
          push: dash.health.push,
          status: "aggregated",
        }}
      />
    );
  }

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

  if (tab === "pricing") {
    return (
      <PricingPanel
        data={config.pricing}
        taxData={config.pricing_tax}
        fuelData={config.pricing_fuel}
        rateCardData={config.pricing_rate_card}
        vehicleCatalog={config.vehicles}
        customerData={config.pricing_customer}
        priceBookData={config.pricing_book}
        driverPayData={config.driver_pay}
        deliveryPromiseData={config.delivery_promise}
        saving={saving}
        onSaveGta={(value, reason) => onSaveConfig("pricing", value, reason)}
        onSaveTax={(value, reason) => onSaveConfig("pricing_tax", value, reason)}
        onSaveFuel={(value, reason) => onSaveConfig("pricing_fuel", value, reason)}
        onSaveRateCard={(value, reason) => onSaveConfig("pricing_rate_card", value, reason)}
        onSaveCustomer={(value, reason) => onSaveConfig("pricing_customer", value, reason)}
        onSavePriceBook={(value, reason) => onSaveConfig("pricing_book", value, reason)}
        onSaveDriverPay={(value, reason) => onSaveConfig("driver_pay", value, reason)}
        onSaveDeliveryPromise={(value, reason) => onSaveConfig("delivery_promise", value, reason)}
      />
    );
  }

  if (tab === "coverage") {
    return (
      <CoveragePanel
        data={config.coverage}
        saving={saving}
        onSave={(value, reason) => onSaveConfig("coverage", value, reason)}
      />
    );
  }

  if ((CONFIG_SECTION_IDS as readonly string[]).includes(tab)) {
    return (
      <ConfigFormPanel
        sectionId={tab}
        data={config[tab]}
        saving={saving}
        effect={bindingEffect}
        envRuntime={center?.env_runtime}
        onSave={(value, reason) => onSaveConfig(tab, value, reason)}
      />
    );
  }

  return (
    <p className="text-sm text-muted">
      {SECTION_DESCRIPTIONS[tab] ?? "Select a section from the navigation."}
    </p>
  );
}
