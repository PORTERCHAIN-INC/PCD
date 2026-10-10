"use client";

import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Inbox, Plus, Search, SearchX } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import AdminPage from "@/components/layout/AdminPage";
import { merchants, merchantActionMessage } from "@/lib/merchants";
import { merchantOps, cad, type BoardRow } from "@/lib/merchant-ops";
import { ScoreRing } from "./ops/ScoreRing";
import { Sparkline } from "./ops/Sparkline";
import {
  ActionMenu,
  Dialog,
  Empty,
  Kbd,
  PageHead,
  QuietButton,
  ReasonDialog,
  SkeletonRows,
  Stat,
  pillInputClass,
  primaryLinkClass,
  searchInputClass,
} from "./ops/ui";

const SEGMENT_OPTIONS: [string, string][] = [
  ["pharmacy_lab", "Pharmacy & lab"],
  ["shopify", "Shopify stores"],
  ["trades", "Construction & trades"],
  ["warehouse_3pl", "Warehouse & 3PL"],
  ["trader", "Traders & wholesale"],
  ["food", "Food & beverage"],
  ["other", "Other"],
];
const SORTS: [string, string][] = [
  ["priority", "Most urgent"],
  ["health", "Lowest health"],
  ["volume", "Most orders"],
  ["trend", "Biggest drop"],
  ["outstanding", "Most owed"],
  ["name", "Name"],
];
const SHORTCUTS: [string, string][] = [
  ["j / k", "Next / previous account"],
  ["Enter", "Open account"],
  ["x", "Select account"],
  ["/", "Search"],
  ["n", "Needs action"],
  ["a", "All accounts"],
  ["[ / ]", "Previous / next page"],
  ["Esc", "Clear selection"],
  ["?", "Show shortcuts"],
];

type Pending = { action: "credit_hold" | "credit_release" } | null;

/**
 * Accounts → Merchants. Answers one question: which accounts need me today?
 * Numbers first, one primary action (Add merchant), everything else in menus.
 */
export default function MerchantBoardClient() {
  const router = useRouter();
  const { getApiToken } = useAdminAuth();
  const [view, setView] = useState<"needs_action" | "all">("needs_action");
  const [segment, setSegment] = useState("");
  const [owner, setOwner] = useState("");
  const [sort, setSort] = useState("priority");
  const [search, setSearch] = useState("");
  const deferred = useDeferredValue(search.trim());
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [cursor, setCursor] = useState(-1);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ text: string; bad?: boolean } | null>(null);
  const [pending, setPending] = useState<Pending>(null);
  const [help, setHelp] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const { data, error } = useApiData(
    (t) =>
      merchantOps.board(t, {
        view,
        segment: segment || undefined,
        owner_id: owner || undefined,
        search: deferred || undefined,
        sort,
        page,
        page_size: 25,
      }),
    [view, segment, owner, deferred, sort, page, version],
    { key: "merchant-board" }
  );
  const { data: owners } = useApiData((t) => merchantOps.owners(t), [], { key: "merchant-owners" });

  const rows = useMemo(() => data?.items ?? [], [data]);
  const counts = data?.counts;
  const filtered = Boolean(segment || owner || deferred);

  const reset = useCallback(() => {
    setPage(1);
    setSelected(new Set());
    setCursor(-1);
  }, []);

  const toggle = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // Keyboard: j/k/Enter/x, / search, n/a views, [ ] pages, Esc, ?
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      const typing =
        el &&
        (el.tagName === "INPUT" ||
          el.tagName === "SELECT" ||
          el.tagName === "TEXTAREA" ||
          el.isContentEditable);
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (document.querySelector('[role="dialog"]') && e.key !== "?") return;
      if (typing) {
        if (e.key === "Escape") (el as HTMLElement).blur();
        return;
      }
      const move = (d: number) => {
        if (!rows.length) return;
        const next = Math.max(
          0,
          Math.min(rows.length - 1, (cursor < 0 ? (d > 0 ? -1 : rows.length) : cursor) + d)
        );
        setCursor(next);
        listRef.current?.querySelectorAll<HTMLElement>("[data-row-link]")[next]?.focus();
      };
      switch (e.key) {
        case "j":
        case "ArrowDown":
          e.preventDefault();
          move(1);
          break;
        case "k":
        case "ArrowUp":
          e.preventDefault();
          move(-1);
          break;
        case "x":
          if (cursor >= 0 && rows[cursor]) toggle(rows[cursor].id);
          break;
        case "Enter":
          if (el?.tagName === "A" || el?.tagName === "BUTTON") break; // native activation
          if (cursor >= 0 && rows[cursor]) router.push(`/merchants/${rows[cursor].id}`);
          break;
        case "/":
          e.preventDefault();
          searchRef.current?.focus();
          break;
        case "n":
          setView("needs_action");
          reset();
          break;
        case "a":
          setView("all");
          reset();
          break;
        case "[":
          if (page > 1) setPage((p) => p - 1);
          break;
        case "]":
          if (data && page < data.pages) setPage((p) => p + 1);
          break;
        case "Escape":
          setSelected(new Set());
          break;
        case "?":
          setHelp((v) => !v);
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [rows, cursor, page, data, router, toggle, reset]);

  async function bulk(action: string, value?: string | null, reason?: string) {
    const ids = [...selected];
    if (!ids.length) return;
    setBusy(true);
    setNote(null);
    try {
      const t = await getApiToken();
      if (action === "approve" || action === "suspend" || action === "activate") {
        let ok = 0;
        const failed: string[] = [];
        for (const id of ids) {
          try {
            if (action === "approve") await merchants.approve(t, id);
            else if (action === "suspend") await merchants.suspend(t, id);
            else await merchants.unsuspend(t, id);
            ok += 1;
          } catch (e) {
            failed.push(merchantActionMessage(e));
          }
        }
        setNote({
          text: `${ok} updated${failed.length ? ` · ${failed.length} failed: ${failed[0]}` : ""}`,
          bad: failed.length > 0,
        });
      } else {
        const res = await merchantOps.bulk(t, { action, merchant_ids: ids, value, reason });
        setNote({
          text: `${res.ok.length} updated${res.failed.length ? ` · ${res.failed.length} failed: ${res.failed[0]?.error}` : ""}`,
          bad: res.failed.length > 0,
        });
      }
      setSelected(new Set());
      setVersion((v) => v + 1);
    } catch (e) {
      setNote({ text: e instanceof Error ? e.message : "Bulk action failed", bad: true });
    } finally {
      setBusy(false);
      setPending(null);
    }
  }

  const allOnPage = rows.length > 0 && rows.every((r) => selected.has(r.id));

  return (
    <AdminPage>
      <PageHead
        eyebrow="Accounts"
        title="Merchants"
        sub={
          counts
            ? `${counts.all} accounts · ${counts.needs_action} need you today`
            : "Loading accounts…"
        }
        action={
          <Link href="/merchants?mode=table&register=1" className={primaryLinkClass}>
            <Plus className="h-4 w-4" aria-hidden /> Add merchant
          </Link>
        }
      />

      {/* Numbers first */}
      <div className="grid grid-cols-2 gap-1 rounded-3xl border border-primary/10 bg-white p-1.5 lg:grid-cols-4">
        <Stat
          label="Need action"
          value={counts ? counts.needs_action : "—"}
          tone={counts && counts.needs_action > 0 ? "bad" : "default"}
          active={view === "needs_action"}
          onClick={() => {
            setView("needs_action");
            reset();
          }}
        />
        <Stat
          label="Overdue"
          value={counts?.overdue_cents != null ? cad(counts.overdue_cents) : "—"}
          tone={counts?.overdue_cents ? "bad" : "default"}
          hint={counts?.on_hold ? `${counts.on_hold} on credit hold` : "No credit holds"}
        />
        <Stat label="At risk" value={counts?.at_risk ?? "—"} hint="Health under 40" />
        <Stat
          label="Accounts"
          value={counts ? counts.all : "—"}
          active={view === "all"}
          hint={
            counts?.outstanding_cents != null
              ? `${cad(counts.outstanding_cents)} outstanding`
              : undefined
          }
          onClick={() => {
            setView("all");
            reset();
          }}
        />
      </div>

      {/* One quiet filter row */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div
          className="grid grid-cols-2 rounded-full bg-slate-100 p-1"
          role="tablist"
          aria-label="View"
        >
          {(
            [
              ["needs_action", "Needs action"],
              ["all", "All"],
            ] as const
          ).map(([v, label]) => (
            <button
              key={v}
              role="tab"
              aria-selected={view === v}
              onClick={() => {
                setView(v);
                reset();
              }}
              className={cn(
                "min-h-10 rounded-full px-4 text-sm font-semibold whitespace-nowrap",
                view === v ? "bg-white text-primary shadow-sm" : "text-slate-600 hover:text-primary"
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <label className="relative min-w-0 flex-1">
          <span className="sr-only">Search merchants</span>
          <Search
            className="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-slate-500"
            aria-hidden
          />
          <input
            ref={searchRef}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              reset();
            }}
            placeholder="Search name or email"
            className={searchInputClass}
          />
          <span className="pointer-events-none absolute top-1/2 right-3 hidden -translate-y-1/2 sm:block">
            <Kbd>/</Kbd>
          </span>
        </label>
        <div className="grid grid-cols-2 gap-2 sm:flex">
          <select
            aria-label="Segment"
            value={segment}
            onChange={(e) => {
              setSegment(e.target.value);
              reset();
            }}
            className={`${pillInputClass} col-span-2 sm:col-span-1`}
          >
            <option value="">All segments</option>
            {SEGMENT_OPTIONS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
                {counts?.segments[v] != null ? ` (${counts.segments[v]})` : ""}
              </option>
            ))}
          </select>
          <select
            aria-label="Owner"
            value={owner}
            onChange={(e) => {
              setOwner(e.target.value);
              reset();
            }}
            className={pillInputClass}
          >
            <option value="">Any owner</option>
            {(owners ?? []).map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Sort"
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              reset();
            }}
            className={pillInputClass}
          >
            {SORTS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Bulk bar: one primary (owner) + menu */}
      {selected.size > 0 && (
        <div
          className="sticky top-2 z-20 flex flex-wrap items-center gap-2 rounded-full bg-primary py-2 pr-2 pl-5 text-white shadow-xl"
          role="region"
          aria-label="Bulk actions"
        >
          <span className="mr-auto text-sm font-bold tabular-nums">{selected.size} selected</span>
          <select
            aria-label="Assign owner"
            className="min-h-10 max-w-[11rem] rounded-full border-0 bg-white px-3 text-sm font-semibold text-primary"
            value=""
            disabled={busy}
            onChange={(e) =>
              e.target.value &&
              void bulk("assign_owner", e.target.value === "_none" ? null : e.target.value)
            }
          >
            <option value="">Assign owner…</option>
            <option value="_none">No owner</option>
            {(owners ?? []).map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
          <div className="text-primary">
            <ActionMenu
              label="More bulk actions"
              items={[
                ...SEGMENT_OPTIONS.map(([v, l]) => ({
                  label: `Segment: ${l}`,
                  onSelect: () => void bulk("set_segment", v),
                })),
                { label: "Approve", onSelect: () => void bulk("approve") },
                { label: "Unsuspend", onSelect: () => void bulk("activate") },
                {
                  label: "Put on credit hold",
                  onSelect: () => setPending({ action: "credit_hold" }),
                },
                {
                  label: "Release credit hold",
                  onSelect: () => setPending({ action: "credit_release" }),
                },
                { label: "Suspend", tone: "danger", onSelect: () => void bulk("suspend") },
              ]}
            />
          </div>
          <button
            className="min-h-10 rounded-full px-3 text-sm font-semibold text-white/90 hover:bg-white/10"
            onClick={() => setSelected(new Set())}
          >
            Clear
          </button>
        </div>
      )}
      {note && (
        <p
          role="status"
          className={cn(
            "rounded-2xl px-4 py-3 text-sm font-medium",
            note.bad ? "bg-red-50 text-red-800" : "bg-emerald-50 text-emerald-800"
          )}
        >
          {note.text}
        </p>
      )}

      {/* List */}
      <section
        className="overflow-hidden rounded-3xl border border-primary/10 bg-white"
        aria-label="Merchants"
      >
        {rows.length > 0 && (
          <div className="flex items-center gap-3 border-b border-primary/5 px-3 py-2 text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase sm:px-5">
            <label className="flex min-h-10 min-w-10 items-center justify-center">
              <input
                type="checkbox"
                checked={allOnPage}
                onChange={() => setSelected(allOnPage ? new Set() : new Set(rows.map((r) => r.id)))}
                className="h-4 w-4 accent-[var(--color-primary)]"
                aria-label="Select all on this page"
              />
            </label>
            <span className="hidden w-10 sm:block">Health</span>
            <span className="flex-1">Account</span>
            <span className="hidden w-24 text-right md:block">8 weeks</span>
            <span className="w-28 text-right">Owed</span>
          </div>
        )}
        {!data && !error ? (
          <div className="px-5 py-4">
            <SkeletonRows rows={6} label="Loading merchants" />
          </div>
        ) : error ? (
          <Empty
            icon={<SearchX className="h-6 w-6" aria-hidden />}
            title="Couldn't load merchants"
            hint={error}
            action={<QuietButton onClick={() => setVersion((v) => v + 1)}>Try again</QuietButton>}
          />
        ) : rows.length === 0 ? (
          view === "needs_action" && !filtered ? (
            <Empty
              icon={<Inbox className="h-6 w-6" aria-hidden />}
              title="Nothing needs you."
              hint="No holds, overdue invoices, broken connections or accounts going quiet."
              action={<QuietButton onClick={() => setView("all")}>See all accounts</QuietButton>}
            />
          ) : (
            <Empty
              icon={<SearchX className="h-6 w-6" aria-hidden />}
              title="No merchants match."
              hint="Try another search, segment or owner."
              action={
                <QuietButton
                  onClick={() => {
                    setSearch("");
                    setSegment("");
                    setOwner("");
                    reset();
                  }}
                >
                  Clear filters
                </QuietButton>
              }
            />
          )
        ) : (
          <ul ref={listRef} className="divide-y divide-primary/5">
            {rows.map((r, i) => (
              <BoardItem
                key={r.id}
                r={r}
                active={i === cursor}
                checked={selected.has(r.id)}
                onToggle={() => toggle(r.id)}
                onFocus={() => setCursor(i)}
              />
            ))}
          </ul>
        )}
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
        {data && data.pages > 1 ? (
          <nav className="flex items-center gap-2" aria-label="Pages">
            <QuietButton
              aria-label="Previous page"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              square
            >
              <ChevronLeft className="h-4 w-4" aria-hidden />
            </QuietButton>
            <span className="tabular-nums">
              {data.page} / {data.pages}
            </span>
            <QuietButton
              aria-label="Next page"
              disabled={page >= data.pages}
              onClick={() => setPage((p) => p + 1)}
              square
            >
              <ChevronRight className="h-4 w-4" aria-hidden />
            </QuietButton>
          </nav>
        ) : (
          <span />
        )}
        <span className="flex items-center gap-4">
          <button
            className="hidden items-center gap-1.5 hover:text-primary sm:inline-flex"
            onClick={() => setHelp(true)}
          >
            <Kbd>?</Kbd> Shortcuts
          </button>
          <Link
            href="/merchants?mode=table"
            className="font-medium underline-offset-4 hover:text-primary hover:underline"
          >
            Table, CSV & signups
          </Link>
        </span>
      </footer>

      <ReasonDialog
        open={pending != null}
        title={
          pending?.action === "credit_hold"
            ? `Hold ${selected.size} accounts`
            : `Release ${selected.size} holds`
        }
        description={
          pending?.action === "credit_hold"
            ? "New bookings stop until the hold is released."
            : "Bookings resume now. Overdue invoices can put them back on hold."
        }
        confirm={pending?.action === "credit_hold" ? "Put on hold" : "Release holds"}
        tone={pending?.action === "credit_hold" ? "danger" : "default"}
        busy={busy}
        onCancel={() => setPending(null)}
        onConfirm={(reason) => pending && void bulk(pending.action, null, reason)}
      />
      <Dialog open={help} onClose={() => setHelp(false)} title="Keyboard shortcuts">
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5 text-sm">
          {SHORTCUTS.map(([k, d]) => (
            <div key={k} className="contents">
              <dt>
                <Kbd>{k}</Kbd>
              </dt>
              <dd className="text-primary">{d}</dd>
            </div>
          ))}
        </dl>
      </Dialog>
    </AdminPage>
  );
}

function BoardItem({
  r,
  checked,
  active,
  onToggle,
  onFocus,
}: {
  r: BoardRow;
  checked: boolean;
  active: boolean;
  onToggle: () => void;
  onFocus: () => void;
}) {
  const reason = r.needs_labels[0] ?? (r.signals.includes("expansion") ? "Growing" : null);
  const urgent = r.needs_action.length > 0;
  return (
    <li
      className={cn(
        "flex items-center gap-3 px-3 py-3 sm:px-5",
        checked ? "bg-secondary/[0.06]" : active && "bg-slate-50"
      )}
    >
      <label className="flex min-h-11 min-w-10 items-center justify-center">
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          className="h-4 w-4 accent-[var(--color-primary)]"
          aria-label={`Select ${r.company_name}`}
        />
      </label>
      <ScoreRing score={r.health.score} size="sm" />
      <Link
        href={`/merchants/${r.id}`}
        data-row-link
        onFocus={onFocus}
        className="flex min-w-0 flex-1 items-center gap-4 rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-secondary"
      >
        <span className="min-w-0 flex-1">
          <span className="flex min-w-0 flex-col sm:flex-row sm:items-baseline sm:gap-2">
            <span className="truncate text-[15px] font-bold text-primary">{r.company_name}</span>
            {reason ? (
              <span
                className={cn(
                  "truncate text-xs font-semibold sm:shrink-0",
                  urgent ? "text-red-700" : "text-emerald-700"
                )}
              >
                {reason}
                {r.needs_labels.length > 1 ? ` +${r.needs_labels.length - 1}` : ""}
              </span>
            ) : null}
          </span>
          <span className="mt-0.5 hidden truncate text-sm text-slate-600 sm:block">
            {urgent
              ? r.next_action
              : `${r.segment_label}${r.owner_name ? ` · ${r.owner_name}` : ""}`}
          </span>
        </span>
        <span className="hidden w-24 justify-end md:flex">
          <Sparkline values={r.trend.weekly} />
        </span>
        <span className="w-24 shrink-0 text-right tabular-nums sm:w-28">
          <span
            className={cn(
              "block text-[15px] font-bold",
              r.overdue_cents > 0 ? "text-red-700" : "text-primary"
            )}
          >
            {cad(r.overdue_cents > 0 ? r.overdue_cents : r.outstanding_cents)}
          </span>
          <span className="block text-xs text-slate-600">
            {r.overdue_cents > 0 ? "overdue" : "outstanding"}
          </span>
        </span>
      </Link>
    </li>
  );
}
