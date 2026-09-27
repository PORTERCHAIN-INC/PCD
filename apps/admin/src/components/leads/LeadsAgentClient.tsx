"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import AdminPage from "@/components/layout/AdminPage";
import { Button, Spinner } from "@/components/crm/primitives";
import { leadsApi, type AgentActivityRow } from "@/lib/leads";

type LaneKey = "inbox" | "welcomed" | "needs_enrich" | "awaiting_welcome" | "blocked" | "recent";

const LANES: Array<{ key: LaneKey; title: string; blurb: string }> = [
  {
    key: "inbox",
    title: "Inbox",
    blurb: "Every open lead with no owner, plus high-priority and SLA notices for the growth team",
  },
  {
    key: "welcomed",
    title: "Welcomed",
    blurb: "Agent already sent (email or WhatsApp reply)",
  },
  {
    key: "awaiting_welcome",
    title: "Awaiting welcome",
    blurb: "Email + marketing consent — next agent tick should send",
  },
  {
    key: "needs_enrich",
    title: "Needs email",
    blurb: "Phone-only / enrich failed — scrape website or Dial capture",
  },
  {
    key: "blocked",
    title: "Blocked",
    blurb: "Consent, suppression, or missing contact stopped the agent",
  },
  {
    key: "recent",
    title: "Recent agent touches",
    blurb: "Any lead with lead_agent custom fields updated",
  },
];

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={
        ok
          ? "rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800"
          : "rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-900"
      }
    >
      {label}
    </span>
  );
}

function LeadRow({
  row,
  onInspect,
  selected,
}: {
  row: AgentActivityRow;
  onInspect: (id: string) => void;
  selected: boolean;
}) {
  return (
    <li
      className={
        selected
          ? "border-l-2 border-secondary bg-secondary/5 py-2.5 pl-3 pr-2"
          : "border-l-2 border-transparent py-2.5 pl-3 pr-2 hover:bg-slate-50"
      }
    >
      <div className="flex items-start justify-between gap-2">
        <button type="button" className="min-w-0 text-left" onClick={() => onInspect(row.id)}>
          <p className="truncate font-medium text-primary">{row.company_name}</p>
          <p className="truncate text-xs text-muted">
            {[
              row.priority,
              row.city,
              row.source,
              row.email || row.phone || "no contact",
              row.agent_status || (row.welcomed ? "welcomed" : null),
              row.last_channel,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {row.reason || (row.blocks && row.blocks.length) ? (
            <p className="mt-0.5 truncate text-xs text-amber-800">
              {row.reason || row.blocks?.join(", ")}
            </p>
          ) : null}
        </button>
        <Link href={`/leads/${row.id}`} className="shrink-0 text-xs text-secondary hover:underline">
          Open
        </Link>
      </div>
    </li>
  );
}

export default function LeadsAgentClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [lane, setLane] = useState<LaneKey>("inbox");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionMsg, setActionMsg] = useState("");

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["leads-agent-activity"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.agentActivity(await getApiToken()),
    refetchInterval: 30_000,
  });

  const { data: nbaData, isFetching: nbaLoading } = useQuery({
    queryKey: ["leads-agent-nba", selectedId],
    enabled: Boolean(selectedId),
    queryFn: async () => leadsApi.nba(await getApiToken(), selectedId!),
  });

  const rows = useMemo(() => {
    if (!data || lane === "inbox") return [];
    return data.lanes[lane] ?? [];
  }, [data, lane]);

  const selected = useMemo(() => {
    if (!data || !selectedId) return undefined;
    const pools = [...rows, ...data.inbox.unassigned, ...data.inbox.notices, ...data.lanes.recent];
    return pools.find((r) => r.id === selectedId);
  }, [rows, data, selectedId]);

  const runWelcome = async (force = false) => {
    if (!selectedId) return;
    setBusy(true);
    setActionMsg("");
    try {
      const token = await getApiToken();
      const result = await leadsApi.welcome(token, selectedId, { force });
      const channels = (result.channels || {}) as Record<
        string,
        { status?: string; reason?: string }
      >;
      const email = channels.email;
      setActionMsg(
        email?.status === "sent"
          ? "Welcome email queued"
          : `Result: ${email?.status || channels.agent?.status || channels.enrich?.status || "done"} (${email?.reason || channels.agent?.reason || channels.enrich?.reason || "ok"})`
      );
      await refetch();
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "welcome_failed");
    } finally {
      setBusy(false);
    }
  };

  const dryRun = async () => {
    if (!selectedId) return;
    setBusy(true);
    setActionMsg("");
    try {
      const token = await getApiToken();
      const result = await leadsApi.welcome(token, selectedId, { dry_run: true });
      const nba = (result.nba || {}) as { primary?: { action?: string; reason?: string } };
      setActionMsg(`NBA: ${nba.primary?.action || "—"} (${nba.primary?.reason || "no reason"})`);
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "dry_run_failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AdminPage>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-primary">Lead Agent</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Inbox holds every unassigned lead and the growth notices that stay inside PorterChain.
            The other tabs show what the welcome agent sent, skipped, or still needs.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/leads"
            className="rounded-lg border border-primary/10 px-3 py-1.5 text-sm text-muted hover:bg-slate-50"
          >
            Lead Workspace
          </Link>
          <Link
            href="/leads/today"
            className="rounded-lg border border-primary/10 px-3 py-1.5 text-sm text-muted hover:bg-slate-50"
          >
            Today Dial
          </Link>
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-lg border border-primary/10 px-3 py-1.5 text-sm text-muted hover:bg-slate-50"
          >
            {isFetching ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {isLoading ? (
        <Spinner label="Loading agent activity…" />
      ) : error ? (
        <p className="text-sm text-red-700">Failed to load agent activity.</p>
      ) : data ? (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <StatusPill
              ok={data.config.auto_send_enabled}
              label={
                data.config.auto_send_enabled
                  ? "Auto-send ON"
                  : `Auto-send OFF (${data.config.kill_switch_env})`
              }
            />
            <StatusPill
              ok={data.config.whatsapp_cloud_configured}
              label={
                data.config.whatsapp_cloud_configured
                  ? "WhatsApp Cloud connected"
                  : "WhatsApp Cloud not configured"
              }
            />
            {data.generated_at ? (
              <span className="text-xs text-muted">
                Updated {new Date(data.generated_at).toLocaleString()}
              </span>
            ) : null}
          </div>

          <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {(
              [
                ["Inbox", data.counts.unassigned, "inbox"],
                ["Welcomed", data.counts.welcomed, "welcomed"],
                ["Awaiting", data.counts.awaiting_welcome, "awaiting_welcome"],
                ["Needs email", data.counts.needs_enrich, "needs_enrich"],
                ["Blocked", data.counts.blocked, "blocked"],
                ["New leads", data.counts.new_total, "recent"],
              ] as const
            ).map(([label, n, key]) => (
              <button
                key={label}
                type="button"
                onClick={() => setLane(key)}
                className={
                  lane === key
                    ? "rounded-xl border border-secondary bg-secondary/10 p-4 text-left"
                    : "rounded-xl border border-primary/10 bg-white p-4 text-left hover:border-primary/20"
                }
              >
                <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
                <p className="mt-1 text-2xl font-semibold text-primary">{n}</p>
                {key === "inbox" ? (
                  <p className="mt-1 text-xs text-muted">{data.counts.notices} notices</p>
                ) : null}
              </button>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
            <section className="rounded-xl border border-primary/10 bg-white">
              <div className="flex flex-wrap gap-1 border-b border-primary/10 p-2">
                {LANES.map((l) => (
                  <button
                    key={l.key}
                    type="button"
                    onClick={() => setLane(l.key)}
                    className={
                      lane === l.key
                        ? "rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white"
                        : "rounded-lg px-3 py-1.5 text-xs font-medium text-muted hover:bg-slate-50"
                    }
                  >
                    {l.title}
                  </button>
                ))}
              </div>
              <div className="border-b border-primary/5 px-4 py-2">
                <p className="text-xs text-muted">{LANES.find((l) => l.key === lane)?.blurb}</p>
              </div>
              {lane === "inbox" ? (
                <div className="grid divide-y divide-primary/10 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
                  <div>
                    <div className="border-b border-primary/5 px-4 py-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-muted">
                        Unassigned · {data.counts.unassigned}
                      </p>
                    </div>
                    {data.inbox.unassigned.length === 0 ? (
                      <p className="p-6 text-sm text-muted">No open unassigned leads.</p>
                    ) : (
                      <ul className="max-h-[60vh] divide-y divide-primary/5 overflow-y-auto">
                        {data.inbox.unassigned.map((row) => (
                          <LeadRow
                            key={row.id}
                            row={row}
                            selected={selectedId === row.id}
                            onInspect={setSelectedId}
                          />
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <div className="border-b border-primary/5 px-4 py-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-muted">
                        Notices · {data.counts.notices}
                      </p>
                    </div>
                    {data.inbox.notices.length === 0 ? (
                      <p className="p-6 text-sm text-muted">No SLA or high-priority notices.</p>
                    ) : (
                      <ul className="max-h-[60vh] divide-y divide-primary/5 overflow-y-auto">
                        {data.inbox.notices.map((row) => (
                          <li
                            key={`${row.notice_kind}-${row.id}`}
                            className={
                              selectedId === row.id
                                ? "border-l-2 border-secondary bg-secondary/5 py-2.5 pl-3 pr-2"
                                : "border-l-2 border-transparent py-2.5 pl-3 pr-2 hover:bg-slate-50"
                            }
                          >
                            <div className="flex items-start justify-between gap-2">
                              <button
                                type="button"
                                className="min-w-0 text-left"
                                onClick={() => setSelectedId(row.id)}
                              >
                                <p className="text-[11px] font-medium uppercase tracking-wide text-muted">
                                  {row.notice_kind === "sla" ? "SLA" : "Unassigned"}
                                </p>
                                <p className="truncate font-medium text-primary">
                                  {row.notice_subject}
                                </p>
                                <p className="mt-0.5 text-xs text-muted">{row.notice_body}</p>
                              </button>
                              <Link
                                href={`/leads/${row.id}`}
                                className="shrink-0 text-xs text-secondary hover:underline"
                              >
                                Open
                              </Link>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              ) : rows.length === 0 ? (
                <p className="p-6 text-sm text-muted">Nothing in this lane.</p>
              ) : (
                <ul className="max-h-[60vh] divide-y divide-primary/5 overflow-y-auto">
                  {rows.map((row) => (
                    <LeadRow
                      key={row.id}
                      row={row}
                      selected={selectedId === row.id}
                      onInspect={setSelectedId}
                    />
                  ))}
                </ul>
              )}
            </section>

            <aside className="rounded-xl border border-primary/10 bg-white p-4">
              <h2 className="text-sm font-semibold text-primary">What&apos;s happening</h2>
              {!selectedId ? (
                <p className="mt-3 text-sm text-muted">
                  Select a lead to see next-best-action, last agent send, and run a welcome.
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  <div>
                    <p className="font-medium text-primary">{selected?.company_name}</p>
                    <p className="text-xs text-muted">
                      {[selected?.email, selected?.phone, selected?.source]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <dl className="space-y-1.5 text-xs">
                    <div className="flex justify-between gap-2">
                      <dt className="text-muted">Agent status</dt>
                      <dd className="font-medium text-primary">
                        {selected?.agent_status || (selected?.welcomed ? "welcomed" : "—")}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="text-muted">Last channel</dt>
                      <dd className="font-medium text-primary">{selected?.last_channel || "—"}</dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="text-muted">Last send</dt>
                      <dd className="font-medium text-primary">
                        {selected?.last_send_at
                          ? new Date(selected.last_send_at).toLocaleString()
                          : "—"}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="text-muted">Marketing</dt>
                      <dd className="font-medium text-primary">
                        {selected?.marketing_consent ? "yes" : "no"}
                      </dd>
                    </div>
                  </dl>

                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted">
                      Next best action
                    </p>
                    {nbaLoading ? (
                      <p className="mt-1 text-sm text-muted">Loading…</p>
                    ) : (
                      <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-primary">
                        {JSON.stringify(
                          (nbaData as { nba?: unknown } | undefined)?.nba ?? nbaData,
                          null,
                          2
                        )}
                      </pre>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
                    <Button type="button" disabled={busy} onClick={() => void dryRun()}>
                      Preview NBA (dry run)
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={busy}
                      onClick={() => void runWelcome(false)}
                    >
                      Run agent welcome
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={busy}
                      onClick={() => void runWelcome(true)}
                    >
                      Force re-welcome
                    </Button>
                    <Link
                      href={`/leads/${selectedId}`}
                      className="text-center text-sm text-secondary hover:underline"
                    >
                      Open lead detail / Dial
                    </Link>
                  </div>
                  {actionMsg ? <p className="text-xs text-muted">{actionMsg}</p> : null}
                </div>
              )}
            </aside>
          </div>
        </>
      ) : null}
    </AdminPage>
  );
}
