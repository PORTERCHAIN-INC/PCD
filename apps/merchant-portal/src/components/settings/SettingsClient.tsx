"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import CompanyCompletenessBanner from "@/components/onboarding/CompanyCompletenessBanner";
import MapsMissingBanner from "@/components/maps/MapsMissingBanner";
import WithGoogleMaps from "@/components/maps/WithGoogleMaps";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { settingsApi } from "@/lib/settings";

type Tab =
  | "profile"
  | "recipients"
  | "locations"
  | "notifications"
  | "branding"
  | "tax"
  | "documents"
  | "privacy";

const TABS: { id: Tab; label: string; module?: string }[] = [
  { id: "profile", label: "Business profile" },
  { id: "locations", label: "Locations" },
  { id: "recipients", label: "Delivery contacts" },
  { id: "notifications", label: "Alert preferences" },
  { id: "branding", label: "Branding" },
  { id: "tax", label: "Tax" },
  { id: "documents", label: "Documents" },
  { id: "privacy", label: "Privacy" },
];

const MOVED_TABS: Record<string, { href: string; label: string }> = {
  billing: { href: "/billing?tab=contacts", label: "Billing contacts" },
  contract: { href: "/billing?tab=rates", label: "Rate card" },
};

const ProfileTab = dynamic(() => import("./tabs/ProfileTab").then((m) => m.ProfileTab), {
  loading: () => <PageSkeleton rows={4} />,
});
const RecipientsTab = dynamic(() => import("./tabs/RecipientsTab").then((m) => m.RecipientsTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const LocationsTab = dynamic(() => import("./tabs/LocationsTab").then((m) => m.LocationsTab), {
  loading: () => <PageSkeleton rows={4} />,
});
const NotificationsTab = dynamic(
  () => import("./tabs/NotificationsTab").then((m) => m.NotificationsTab),
  { loading: () => <PageSkeleton rows={4} /> }
);
const BrandingTab = dynamic(() => import("./tabs/BrandingTab").then((m) => m.BrandingTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const TaxTab = dynamic(() => import("./tabs/TaxTab").then((m) => m.TaxTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const DocumentsTab = dynamic(() => import("./tabs/DocumentsTab").then((m) => m.DocumentsTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const PrivacyTab = dynamic(() => import("./tabs/PrivacyTab").then((m) => m.PrivacyTab), {
  loading: () => <PageSkeleton rows={3} />,
});

function parseSettingsTab(value: string | null): Tab {
  if (value && TABS.some((t) => t.id === value)) return value as Tab;
  return "profile";
}

export default function SettingsClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn, refreshSession, modules } = useMerchantAuth();
  const qc = useQueryClient();
  const visibleTabs = useMemo(
    () => TABS.filter((t) => !t.module || modules.includes(t.module)),
    [modules]
  );
  const searchParams = useSearchParams();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>(() => parseSettingsTab(searchParams.get("tab")));

  const enabled = Boolean(isLoaded && isSignedIn);

  const overviewQuery = useQuery({
    queryKey: ["merchant-settings-overview", orgId],
    enabled,
    staleTime: 30_000,
    queryFn: async () => settingsApi.overview(await getApiToken(), orgId),
  });

  const recipientsQuery = useQuery({
    queryKey: ["merchant-settings-recipients", orgId],
    enabled: enabled && tab === "recipients",
    staleTime: 30_000,
    queryFn: async () => settingsApi.recipients(await getApiToken(), orgId),
  });

  const data = overviewQuery.data ?? null;
  const recipients = recipientsQuery.data ?? [];
  const error =
    overviewQuery.error instanceof Error
      ? overviewQuery.error.message
      : overviewQuery.error
        ? "Failed to load settings"
        : null;

  const load = useCallback(async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["merchant-settings-overview", orgId] }),
      qc.invalidateQueries({ queryKey: ["merchant-settings-recipients", orgId] }),
    ]);
  }, [qc, orgId]);

  useEffect(() => {
    const raw = searchParams.get("tab");
    const moved = raw ? MOVED_TABS[raw] : null;
    if (moved) {
      router.replace(moved.href);
      return;
    }
    const next = parseSettingsTab(raw);
    const allowed = visibleTabs.some((t) => t.id === next)
      ? next
      : (visibleTabs[0]?.id ?? "profile");
    setTab(allowed);
  }, [searchParams, visibleTabs, router]);

  function gotoTab(id: Tab) {
    setTab(id);
    router.replace(`/settings?tab=${id}`, { scroll: false });
  }

  if (!isLoaded || !data) {
    if (error) {
      return <EmptyState title="Could not load settings" hint={error} />;
    }
    return <PageSkeleton rows={5} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-primary sm:text-2xl">Settings</h1>
        <p className="mt-1 text-sm text-muted">
          Company file, locations, tax, branding, and privacy. Invoices and the rate card are under{" "}
          <Link href="/billing" className="font-medium text-secondary underline">
            Billing
          </Link>
          . Seats are under{" "}
          <Link href="/team" className="font-medium text-secondary underline">
            Team
          </Link>
          .
        </p>
      </div>

      <CompanyCompletenessBanner completeness={data.completeness} />
      <MapsMissingBanner />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <nav
        className="ops-tab-rail rounded-2xl border border-primary/10 bg-white"
        aria-label="Settings sections"
      >
        {visibleTabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => gotoTab(t.id)}
            className={`min-h-10 shrink-0 rounded-xl px-3 py-1.5 text-sm font-medium whitespace-nowrap ${
              tab === t.id ? "bg-primary text-white" : "text-muted hover:bg-primary/5"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "profile" && (
        <WithGoogleMaps>
          <ProfileTab
            profile={data.profile}
            onRefresh={load}
            getToken={getApiToken}
            orgId={orgId}
          />
        </WithGoogleMaps>
      )}
      {tab === "recipients" && (
        <RecipientsTab
          recipients={recipients}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "locations" && (
        <WithGoogleMaps>
          <LocationsTab data={data} onRefresh={load} getToken={getApiToken} orgId={orgId} />
        </WithGoogleMaps>
      )}
      {tab === "notifications" && (
        <NotificationsTab
          prefs={data.notifications}
          quietHours={data.quiet_hours}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "branding" && (
        <BrandingTab
          branding={data.branding}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
          onSaved={() => void refreshSession()}
        />
      )}
      {tab === "tax" && (
        <TaxTab tax={data.tax} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
      {tab === "documents" && (
        <DocumentsTab
          documents={data.documents ?? []}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "privacy" && <PrivacyTab getToken={getApiToken} orgId={orgId} />}
    </div>
  );
}
