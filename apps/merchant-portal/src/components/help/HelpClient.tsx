"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ClaimsPanel, SupportPanel } from "@/components/help/HelpPanels";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { hasMerchantModule } from "@/lib/merchant-nav";
import { settingsApi, type ClaimRow, type SupportTicket } from "@/lib/settings";

type Tab = "tickets" | "claims";

export default function HelpClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn, modules } = useMerchantAuth();
  const canTickets = hasMerchantModule(modules, "support");
  const canClaims = hasMerchantModule(modules, "claims");
  const tabs = useMemo(
    () =>
      [
        canTickets ? { id: "tickets" as const, label: "Tickets" } : null,
        canClaims ? { id: "claims" as const, label: "Claims" } : null,
      ].filter(Boolean) as { id: Tab; label: string }[],
    [canTickets, canClaims]
  );
  const [tab, setTab] = useState<Tab>("tickets");
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [claims, setClaims] = useState<ClaimRow[]>([]);
  const [kb, setKb] = useState<{
    articles: Array<{ id: string; title: string; body: string }>;
    faq: Array<{ question: string; answer: string }>;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    setError(null);
    try {
      const token = await getApiToken();
      const [tix, cl, knowledge] = await Promise.all([
        canTickets
          ? settingsApi.supportTickets(token, orgId)
          : Promise.resolve([] as SupportTicket[]),
        canClaims ? settingsApi.claims(token, orgId) : Promise.resolve([] as ClaimRow[]),
        canTickets ? settingsApi.knowledgeBase(token, orgId) : Promise.resolve(null),
      ]);
      setTickets(tix);
      setClaims(cl);
      setKb(knowledge);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load help");
    }
  }, [canClaims, canTickets, getApiToken, isSignedIn, orgId]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn, load]);

  useEffect(() => {
    if (tabs.some((t) => t.id === tab)) return;
    setTab(tabs[0]?.id ?? "tickets");
  }, [tab, tabs]);

  if (!isLoaded) return <p className="text-muted">Loading…</p>;
  if (!isSignedIn) return <p className="text-muted">Please sign in.</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Help</h1>
        <p className="text-sm text-muted">Open a ticket or file a claim by order number.</p>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {tabs.length > 1 ? (
        <nav className="flex flex-wrap gap-1 border-b border-primary/10 pb-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                tab === t.id
                  ? "bg-secondary/10 font-semibold text-secondary"
                  : "text-muted hover:text-primary"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      ) : null}
      {tab === "tickets" && canTickets ? (
        <SupportPanel
          tickets={tickets}
          kb={kb}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      ) : null}
      {tab === "claims" && canClaims ? (
        <ClaimsPanel claims={claims} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      ) : null}
    </div>
  );
}
