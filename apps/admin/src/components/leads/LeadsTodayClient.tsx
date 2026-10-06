"use client";

import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import AdminPage from "@/components/layout/AdminPage";
import { PageSkeleton } from "@porterchain/ui/loading";
import { leadsApi } from "@/lib/leads";

type PackRow = {
  id?: string;
  company_name?: string;
  phone?: string | null;
  email?: string | null;
  primary_contact_name?: string | null;
  has_phone?: boolean;
  city?: string | null;
  priority?: string;
  status?: string;
  lead_score?: number;
  service_area?: string | null;
  agent_status?: string | null;
  needs_enrich?: boolean;
};

type ContactFilter = "all" | "with_phone" | "without_phone" | "exceptions";

/** Dial-floor city chips (match address.city / service_area, case-insensitive). */
const TODAY_DIAL_CITIES = [
  "Mississauga",
  "Vaughan",
  "Hamilton",
  "Toronto",
  "Brampton",
  "Markham",
  "Oakville",
  "Burlington",
  "Richmond Hill",
  "Ajax",
  "Pickering",
  "Oshawa",
] as const;

function rowHasPhone(row: PackRow): boolean {
  if (typeof row.has_phone === "boolean") return row.has_phone;
  return Boolean((row.phone || "").trim());
}

function rowCityHay(row: PackRow): string {
  return [row.city, row.service_area].filter(Boolean).join(" ").toLowerCase();
}

function rowMatchesCity(row: PackRow, city: string): boolean {
  if (!city) return true;
  return rowCityHay(row).includes(city.toLowerCase());
}

function rowMatchesContact(row: PackRow, contact: ContactFilter): boolean {
  if (contact === "all") return true;
  if (contact === "exceptions") {
    return Boolean(
      row.needs_enrich ||
      row.agent_status === "needs_enrich" ||
      row.agent_status === "enrich_failed" ||
      row.agent_status === "blocked"
    );
  }
  const has = rowHasPhone(row);
  return contact === "with_phone" ? has : !has;
}

function rowMatches(row: PackRow, q: string): boolean {
  if (!q) return true;
  const hay = [
    row.company_name,
    row.primary_contact_name,
    row.phone,
    row.email,
    row.city,
    row.service_area,
    row.priority,
    row.status,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  const digits = (row.phone || "").replace(/\D/g, "");
  const qDigits = q.replace(/\D/g, "");
  if (qDigits.length >= 3 && digits.includes(qDigits)) return true;
  return hay.includes(q);
}

function Pack({ title, rows, total }: { title: string; rows: PackRow[]; total: number }) {
  const countLabel = rows.length === total ? String(rows.length) : `${rows.length} of ${total}`;
  return (
    <section className="rounded-xl border border-primary/10 bg-white p-4">
      <h2 className="mb-3 text-sm font-semibold text-primary">
        {title} <span className="font-normal text-muted">({countLabel})</span>
      </h2>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">{total === 0 ? "Empty pack." : "No matches."}</p>
      ) : (
        <ul className="max-h-[70vh] divide-y divide-primary/5 overflow-y-auto">
          {rows.map((row) => (
            <li key={String(row.id)} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <Link
                  href={`/leads/${row.id}`}
                  className="truncate font-medium text-primary hover:underline"
                >
                  {row.company_name}
                </Link>
                <p className="truncate text-xs text-muted">
                  {[
                    row.city,
                    row.primary_contact_name,
                    row.phone || (row.email ? `email ${row.email}` : "no phone"),
                    row.priority,
                    `score ${row.lead_score ?? 0}`,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              {rowHasPhone(row) ? (
                <a
                  href={`tel:${String(row.phone).replace(/\D/g, "")}`}
                  className="shrink-0 text-sm text-secondary hover:underline"
                >
                  Call
                </a>
              ) : (
                <Link
                  href={`/leads/${row.id}`}
                  className="shrink-0 text-sm text-amber-700 hover:underline"
                >
                  Add contact
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function LeadsTodayClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [search, setSearch] = useState("");
  const [city, setCity] = useState("");
  const [contact, setContact] = useState<ContactFilter>("all");
  const deferredSearch = useDeferredValue(search.trim().toLowerCase());
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["leads-today"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.today(await getApiToken()),
  });

  const packs = useMemo(() => {
    const filterRow = (r: PackRow) =>
      rowMatchesContact(r, contact) && rowMatchesCity(r, city) && rowMatches(r, deferredSearch);
    const ready = (data?.ready ?? []) as PackRow[];
    const followups = (data?.followups ?? []) as PackRow[];
    const interested = (data?.interested ?? []) as PackRow[];
    return {
      ready: {
        all: ready,
        rows: ready.filter(filterRow),
      },
      followups: {
        all: followups,
        rows: followups.filter(filterRow),
      },
      interested: {
        all: interested,
        rows: interested.filter(filterRow),
      },
    };
  }, [data, deferredSearch, city, contact]);

  const hasFilters = Boolean(search || city || contact !== "all");

  return (
    <AdminPage>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-primary">Today Dial</h1>
          <p className="text-sm text-muted">
            Ready · follow-ups · interested — outbound vendor packs
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="today-dial-contact">
            Filter by contact details
          </label>
          <select
            id="today-dial-contact"
            value={contact}
            onChange={(e) => setContact(e.target.value as ContactFilter)}
            className="rounded-lg border border-primary/15 bg-white px-3 py-1.5 text-sm text-primary focus:border-secondary focus:outline-none focus:ring-1 focus:ring-secondary"
          >
            <option value="all">All contacts</option>
            <option value="with_phone">With phone</option>
            <option value="without_phone">Without phone</option>
            <option value="exceptions">Agent exceptions</option>
          </select>
          <label className="sr-only" htmlFor="today-dial-city">
            Filter by city
          </label>
          <select
            id="today-dial-city"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="rounded-lg border border-primary/15 bg-white px-3 py-1.5 text-sm text-primary focus:border-secondary focus:outline-none focus:ring-1 focus:ring-secondary"
          >
            <option value="">All cities</option>
            {TODAY_DIAL_CITIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <label className="sr-only" htmlFor="today-dial-search">
            Search dial packs
          </label>
          <input
            id="today-dial-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search company, contact, phone…"
            className="min-w-[220px] flex-1 rounded-lg border border-primary/15 bg-white px-3 py-1.5 text-sm text-primary placeholder:text-muted focus:border-secondary focus:outline-none focus:ring-1 focus:ring-secondary"
            autoComplete="off"
          />
          {hasFilters ? (
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setCity("");
                setContact("all");
              }}
              className="rounded-lg border border-primary/10 px-3 py-1.5 text-sm text-muted hover:bg-slate-50"
            >
              Clear
            </button>
          ) : null}
          <Link
            href="/leads?source=vendor_import&priority=high&status=new"
            className="rounded-lg border border-primary/10 px-3 py-1.5 text-sm text-muted hover:bg-slate-50"
          >
            Call queue list
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
        <PageSkeleton rows={4} />
      ) : error ? (
        <p className="text-sm text-red-700">Failed to load Today packs.</p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <Pack title="Ready to call" rows={packs.ready.rows} total={packs.ready.all.length} />
          <Pack
            title="Follow-ups due"
            rows={packs.followups.rows}
            total={packs.followups.all.length}
          />
          <Pack
            title="Interested"
            rows={packs.interested.rows}
            total={packs.interested.all.length}
          />
        </div>
      )}
    </AdminPage>
  );
}
