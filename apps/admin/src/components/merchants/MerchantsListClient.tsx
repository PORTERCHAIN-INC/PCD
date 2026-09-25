"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  type ColumnDef,
  type VisibilityState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  ArrowUpDown,
  Building2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Columns3,
  Download,
  Mail,
  Rocket,
  Search,
  SlidersHorizontal,
  Store,
  TrendingUp,
  UserCheck,
  UserPlus,
  Wallet,
  X,
  Zap,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchantStatusLabel, onboardingPhaseLabel } from "@/lib/catalog";
import {
  merchants,
  healthTone,
  DEFAULT_MERCHANT_PRICING,
  type MerchantPricing,
  type MerchantRow,
} from "@/lib/merchants";
import { Dropdown, FilterChip, ProvincePills } from "@/components/crm/filters";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  Input,
  Modal,
  Spinner,
} from "@/components/crm/primitives";
import { money, shortDate, relativeTime, titleCase, downloadCsv, toCsv } from "@/lib/crmFormat";
import AdminPage from "@/components/layout/AdminPage";
import dynamic from "next/dynamic";

const MerchantPricingFields = dynamic(
  () => import("@/components/merchants/MerchantPricingFields"),
  { ssr: false }
);

const STATUSES = ["PENDING", "ONBOARDING", "ACTIVE", "SUSPENDED", "CLOSED"];
const TERMS = ["IMMEDIATE", "NET_7", "NET_14", "NET_15", "NET_30", "NET_45", "CUSTOM"];
const PROVINCE_NAMES: Record<string, string> = {
  ON: "Ontario",
  QC: "Quebec",
  BC: "British Columbia",
  AB: "Alberta",
  MB: "Manitoba",
  SK: "Saskatchewan",
  NS: "Nova Scotia",
  NB: "New Brunswick",
  NL: "Newfoundland",
  PE: "PEI",
  NT: "Northwest Territories",
  YT: "Yukon",
  NU: "Nunavut",
};
const STATUS_TONE: Record<string, string> = {
  ACTIVE: "green",
  PENDING: "amber",
  ONBOARDING: "sky",
  SUSPENDED: "red",
  CLOSED: "slate",
};
const ONBOARDING_TONE: Record<string, "green" | "amber" | "red" | "slate" | "sky"> = {
  ready: "green",
  needs_invite: "amber",
  awaiting_clerk: "sky",
  needs_activation: "red",
  needs_approval: "amber",
  onboarding: "slate",
};
const VIEWS_KEY = "pc.merchants.views";

type SavedView = { name: string; visibility: VisibilityState };

export default function MerchantsListClient() {
  const router = useRouter();
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  // M-27: push status / terms / search to the API (avoid silent truncation at limit=500).
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [terms, setTerms] = useState("");
  const { data, error } = useApiData(
    (t) =>
      merchants.list(t, {
        limit: "500",
        status: status || undefined,
        payment_terms: terms || undefined,
        search: search.trim() || undefined,
      }),
    [version, status, terms, search],
    { key: "merchants-list" }
  );
  const { data: statsData } = useApiData((t) => merchants.stats(t), [version], {
    key: "merchants-stats",
  });
  const stats = statsData && typeof statsData.total === "number" ? statsData : null;
  const { data: unprovisioned, error: unprovisionedError } = useApiData(
    (t) => merchants.unprovisionedSignups(t),
    [version],
    {
      key: "merchants-unprovisioned",
    }
  );

  const [registerOpen, setRegisterOpen] = useState(false);
  const [registerForm, setRegisterForm] = useState({ email: "", company_name: "" });
  const [registerPricing, setRegisterPricing] = useState<MerchantPricing>(DEFAULT_MERCHANT_PRICING);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [registering, setRegistering] = useState(false);

  // Client-only facets (API already applied status/terms/search)
  const [industry, setIndustry] = useState("");
  const [province, setProvince] = useState("");
  const [city, setCity] = useState("");
  const [contract, setContract] = useState("");
  const [health, setHealth] = useState("");
  const [apiOnly, setApiOnly] = useState("");
  const [onboardingFilter, setOnboardingFilter] = useState("");
  const [sortBy, setSortBy] = useState("recent");

  // Grid state
  const [sorting, setSorting] = useState<SortingState>([]);
  const [rowSelection, setRowSelection] = useState<Record<string, boolean>>({});
  const [visibility, setVisibility] = useState<VisibilityState>({
    legal_name: false,
    service_area: false,
    created_at: false,
    industry: false,
    primary_contact: false,
    monthly_deliveries: false,
    monthly_revenue_cents: false,
    contract_status: false,
    payment_terms: false,
    api_connected: false,
  });
  const [chooserOpen, setChooserOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const chooserRef = useRef<HTMLDivElement>(null);

  const [views, setViews] = useState<SavedView[]>([]);
  useEffect(() => {
    try {
      setViews(JSON.parse(localStorage.getItem(VIEWS_KEY) || "[]"));
    } catch {
      setViews([]);
    }
  }, []);
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (chooserRef.current && !chooserRef.current.contains(e.target as Node))
        setChooserOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const facets = useMemo(() => {
    const list = Array.isArray(data) ? data : [];
    const industries = [...new Set(list.map((r) => r.industry).filter(Boolean) as string[])].sort();
    const provMap = new Map<string, number>();
    const cityMap = new Map<string, number>();
    list.forEach((r) => {
      if (r.province) provMap.set(r.province, (provMap.get(r.province) ?? 0) + 1);
      if (r.city) cityMap.set(r.city, (cityMap.get(r.city) ?? 0) + 1);
    });
    return {
      industries,
      provinces: [...provMap.entries()]
        .map(([code, count]) => ({ code, count }))
        .sort((a, b) => b.count - a.count),
      cities: [...cityMap.entries()]
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count),
    };
  }, [data]);

  const rows = useMemo(() => {
    let r = Array.isArray(data) ? [...data] : [];
    if (industry) r = r.filter((m) => m.industry === industry);
    if (province) r = r.filter((m) => m.province === province);
    if (city) r = r.filter((m) => m.city === city);
    if (contract) r = r.filter((m) => m.contract_status === contract);
    if (apiOnly) r = r.filter((m) => (apiOnly === "yes" ? m.api_connected : !m.api_connected));
    if (health === "hot") r = r.filter((m) => m.health_score >= 70);
    else if (health === "warm") r = r.filter((m) => m.health_score >= 40 && m.health_score < 70);
    else if (health === "risk") r = r.filter((m) => m.health_score < 40);
    if (onboardingFilter === "pending") r = r.filter((m) => !m.portal_ready);
    else if (onboardingFilter === "ready") r = r.filter((m) => m.portal_ready);
    if (sortBy === "revenue") r.sort((a, b) => b.monthly_revenue_cents - a.monthly_revenue_cents);
    else if (sortBy === "health") r.sort((a, b) => b.health_score - a.health_score);
    else if (sortBy === "outstanding")
      r.sort((a, b) => b.outstanding_balance_cents - a.outstanding_balance_cents);
    else if (sortBy === "name") r.sort((a, b) => a.company_name.localeCompare(b.company_name));
    return r;
  }, [data, industry, province, city, contract, apiOnly, health, onboardingFilter, sortBy]);

  const activeFilters =
    [status, industry, province, city, terms, contract, health, apiOnly, onboardingFilter].filter(
      Boolean
    ).length + (sortBy !== "recent" ? 1 : 0);

  function clearFilters() {
    setStatus("");
    setIndustry("");
    setProvince("");
    setCity("");
    setTerms("");
    setContract("");
    setHealth("");
    setApiOnly("");
    setOnboardingFilter("");
    setSortBy("recent");
  }

  const refresh = () => setVersion((v) => v + 1);

  async function registerMerchant(
    email: string,
    companyName: string,
    opts?: { closeModal?: boolean }
  ) {
    setRegistering(true);
    setRegisterError(null);
    try {
      const token = await getApiToken();
      const created = await merchants.create(token, {
        email: email.trim(),
        company_name: companyName.trim(),
        auto_activate: true,
        send_invite: false,
        pricing: registerPricing,
      });
      refresh();
      if (opts?.closeModal !== false) setRegisterOpen(false);
      router.push(`/merchants/${created.id}?tab=pricing`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Registration failed";
      if (msg === "merchant_email_exists" || msg === "merchant_user_email_exists") {
        setRegisterError(
          "This email is already registered — find them in the merchants list below."
        );
      } else if (msg === "merchant_create_failed") {
        setRegisterError("Could not create merchant. Check the API logs and try again.");
      } else {
        setRegisterError(msg);
      }
    } finally {
      setRegistering(false);
    }
  }

  async function runAction(
    merchantId: string,
    action: string,
    fn: (token: string) => Promise<unknown>
  ) {
    setBusy(`${merchantId}:${action}`);
    setActionError(null);
    try {
      const token = await getApiToken();
      await fn(token);
      refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : `${action} failed`;
      setActionError(
        msg === "owner_not_clerk_linked"
          ? "Owner seat reserved — merchant stays Onboarding until the owner accepts Clerk and links."
          : msg
      );
    } finally {
      setBusy(null);
    }
  }

  const columns = useMemo<ColumnDef<MerchantRow, unknown>[]>(
    () => [
      {
        id: "select",
        enableSorting: false,
        header: ({ table }) => (
          <input
            type="checkbox"
            checked={table.getIsAllPageRowsSelected()}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
            onClick={(e) => e.stopPropagation()}
          />
        ),
      },
      {
        accessorKey: "company_name",
        header: "Merchant",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-lg bg-secondary/10 text-secondary">
              {row.original.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={row.original.logo_url} alt="" className="h-full w-full object-cover" />
              ) : (
                <Building2 className="h-4 w-4" />
              )}
            </span>
            <div>
              <p className="font-semibold text-primary">{row.original.company_name}</p>
              <p className="text-xs text-muted">{row.original.email}</p>
            </div>
          </div>
        ),
      },
      {
        accessorKey: "legal_name",
        header: "Legal name",
        cell: ({ getValue }) => String(getValue() ?? "—"),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ getValue }) => (
          <Badge tone={STATUS_TONE[String(getValue())] ?? "slate"}>
            {merchantStatusLabel(String(getValue()))}
          </Badge>
        ),
      },
      {
        id: "onboarding",
        header: "Onboarding",
        cell: ({ row }) => {
          const m = row.original;
          const phase = m.onboarding_phase ?? "onboarding";
          const progress = m.onboarding_progress ?? 0;
          return (
            <div className="min-w-[10rem]">
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-bg">
                  <div
                    className="h-full rounded-full bg-secondary"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-xs text-muted">{progress}%</span>
              </div>
              <Badge tone={ONBOARDING_TONE[phase] ?? "slate"} className="mt-1">
                {m.onboarding_phase_label || onboardingPhaseLabel(phase)}
              </Badge>
              {m.owner_email && (
                <p className="mt-0.5 truncate text-[11px] text-muted">{m.owner_email}</p>
              )}
            </div>
          );
        },
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: ({ row }) => {
          const m = row.original;
          const id = m.id;
          const isBusy = busy?.startsWith(`${id}:`) ?? false;
          return (
            <div className="flex flex-wrap gap-1" onClick={(e) => e.stopPropagation()}>
              {!m.portal_ready && (
                <Button
                  variant="outline"
                  className="h-8 px-2 text-xs"
                  disabled={isBusy}
                  onClick={() =>
                    void runAction(id, "complete", (token) =>
                      merchants.completeOnboarding(token, id, m.owner_email ?? m.email)
                    )
                  }
                >
                  <Rocket className="h-3.5 w-3.5" />
                  Activate
                </Button>
              )}
              {m.can_invite_owner && (
                <Button
                  variant="ghost"
                  className="h-8 px-2 text-xs"
                  disabled={isBusy}
                  onClick={() =>
                    void runAction(id, "invite", (token) =>
                      merchants.inviteOwner(token, id, m.owner_email ?? m.email)
                    )
                  }
                >
                  <Mail className="h-3.5 w-3.5" />
                  Add seat
                </Button>
              )}
              {m.can_activate_user && (
                <Button
                  variant="ghost"
                  className="h-8 px-2 text-xs"
                  disabled={isBusy}
                  onClick={() =>
                    void runAction(id, "activate", (token) =>
                      merchants.activateUsers(token, id, m.owner_email)
                    )
                  }
                >
                  <UserCheck className="h-3.5 w-3.5" />
                  Enable user
                </Button>
              )}
              {m.can_approve &&
                m.portal_ready === false &&
                m.onboarding_phase === "needs_approval" && (
                  <Button
                    variant="ghost"
                    className="h-8 px-2 text-xs"
                    disabled={isBusy}
                    onClick={() =>
                      void runAction(id, "approve", (token) => merchants.approve(token, id))
                    }
                  >
                    Approve
                  </Button>
                )}
            </div>
          );
        },
      },
      {
        accessorKey: "industry",
        header: "Industry",
        cell: ({ getValue }) => String(getValue() ?? "—"),
      },
      {
        id: "location",
        header: "City",
        cell: ({ row }) =>
          [row.original.city, row.original.province].filter(Boolean).join(", ") || "—",
      },
      {
        accessorKey: "primary_contact",
        header: "Primary contact",
        cell: ({ getValue }) => String(getValue() ?? "—"),
      },
      {
        accessorKey: "monthly_deliveries",
        header: "Deliveries/mo",
        cell: ({ getValue }) => String(getValue() ?? 0),
      },
      {
        accessorKey: "monthly_revenue_cents",
        header: "Monthly revenue",
        cell: ({ getValue }) => money(getValue() as number),
      },
      {
        accessorKey: "outstanding_balance_cents",
        header: "Outstanding",
        cell: ({ getValue }) => {
          const v = getValue() as number;
          return (
            <span className={v > 0 ? "font-medium text-red-600" : "text-primary"}>{money(v)}</span>
          );
        },
      },
      {
        accessorKey: "contract_status",
        header: "Contract",
        cell: ({ getValue }) => titleCase(String(getValue())),
      },
      {
        accessorKey: "payment_terms",
        header: "Terms",
        cell: ({ getValue }) => titleCase(String(getValue())),
      },
      {
        accessorKey: "health_score",
        header: "Health",
        cell: ({ getValue }) => {
          const v = Number(getValue());
          return (
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-12 overflow-hidden rounded-full bg-gray-bg">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${v}%`,
                    background: v >= 70 ? "#16a34a" : v >= 40 ? "#f59e0b" : "#dc2626",
                  }}
                />
              </div>
              <Badge tone={healthTone(v)}>{v}</Badge>
            </div>
          );
        },
      },
      {
        accessorKey: "api_connected",
        header: "API",
        cell: ({ getValue }) =>
          getValue() ? (
            <Badge tone="green">Connected</Badge>
          ) : (
            <span className="text-xs text-muted">—</span>
          ),
      },
      {
        accessorKey: "last_activity_at",
        header: "Last activity",
        cell: ({ getValue }) => relativeTime(getValue() as string),
      },
      {
        accessorKey: "created_at",
        header: "Created",
        cell: ({ getValue }) => shortDate(String(getValue())),
      },
    ],
    [busy]
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, rowSelection, columnVisibility: visibility },
    onSortingChange: setSorting,
    onRowSelectionChange: setRowSelection,
    onColumnVisibilityChange: setVisibility,
    getRowId: (r) => r.id,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 25 } },
  });

  const selectedIds = Object.keys(rowSelection).filter((k) => rowSelection[k]);

  async function bulk(action: "approve" | "suspend" | "activate") {
    setBusy("bulk");
    setActionError(null);
    try {
      const token = await getApiToken();
      for (const id of selectedIds) {
        if (action === "approve") await merchants.approve(token, id);
        else if (action === "suspend") await merchants.suspend(token, id);
        else {
          const row = rows.find((r) => r.id === id);
          await merchants.completeOnboarding(token, id, row?.owner_email ?? row?.email);
        }
      }
      setRowSelection({});
      refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : `Bulk ${action} failed`;
      setActionError(
        msg === "owner_not_clerk_linked"
          ? "Owner seat reserved — merchant stays Onboarding until the owner accepts Clerk and links."
          : msg
      );
    } finally {
      setBusy(null);
    }
  }

  function exportCsv() {
    const cols = table.getVisibleLeafColumns().filter((c) => c.id !== "select");
    const headers = cols.map((c) => String(c.columnDef.header ?? c.id));
    const body = table.getFilteredRowModel().rows.map((r) =>
      cols.map((c) => {
        if (c.id === "status") {
          return r.original.status_label || merchantStatusLabel(r.original.status);
        }
        if (c.id === "onboarding") {
          return (
            r.original.onboarding_phase_label ||
            onboardingPhaseLabel(r.original.onboarding_phase ?? "onboarding")
          );
        }
        const v = r.getValue(c.id);
        return v == null ? "" : String(v);
      })
    );
    downloadCsv(`merchants-${new Date().toISOString().slice(0, 10)}.csv`, toCsv(headers, body));
  }

  function saveView() {
    const name = prompt("Save current view as:");
    if (!name) return;
    const next = [...views.filter((v) => v.name !== name), { name, visibility }];
    setViews(next);
    localStorage.setItem(VIEWS_KEY, JSON.stringify(next));
  }

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <AdminPage>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Merchants</h1>
          <p className="text-sm text-muted">
            Scan who needs a seat, approval, or collection. Open a row to price, staff, and operate
            that company.
          </p>
        </div>
        <Button
          onClick={() => {
            setRegisterForm({ email: "", company_name: "" });
            setRegisterPricing(DEFAULT_MERCHANT_PRICING);
            setRegisterError(null);
            setRegisterOpen(true);
          }}
        >
          <UserPlus className="h-4 w-4" />
          Register merchant
        </Button>
      </div>

      {actionError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {actionError}
        </p>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <StatTile icon={Store} label="Total merchants" value={stats.total.toLocaleString()} />
          <StatTile
            icon={CheckCircle2}
            label="Active"
            value={String(stats.active)}
            accent="text-green-600"
          />
          <StatTile
            icon={Zap}
            label="Onboarding"
            value={String(stats.onboarding_pending ?? stats.pending)}
            accent="text-amber-600"
          />
          <StatTile
            icon={TrendingUp}
            label="Monthly revenue"
            value={money(stats.monthly_revenue_cents)}
            accent="text-secondary"
          />
          <StatTile
            icon={Wallet}
            label="Ops AR outstanding"
            value={money(stats.outstanding_balance_cents)}
            accent="text-red-600"
          />
        </div>
      )}

      {(unprovisionedError || (unprovisioned && unprovisioned.length > 0)) && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-4 shadow-sm">
          <div className="mb-2 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-primary">
              Unprovisioned Clerk signups
              {unprovisioned && unprovisioned.length > 0 ? ` (${unprovisioned.length})` : ""}
            </h2>
            <p className="text-xs text-muted">
              Signed into the merchant app with no PorterChain seat — register to attach an org.
            </p>
          </div>
          {unprovisionedError && (
            <p className="rounded-lg border border-red-200 bg-white px-3 py-2 text-sm text-red-700">
              Could not load Clerk directory: {unprovisionedError}
            </p>
          )}
          {unprovisioned && unprovisioned.length > 0 && (
            <div className="mt-2 divide-y divide-amber-100 rounded-xl border border-amber-100 bg-white">
              {unprovisioned.slice(0, 8).map((u) => (
                <div
                  key={u.clerk_user_id}
                  className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm"
                >
                  <div>
                    <p className="font-medium text-primary">{u.name}</p>
                    <p className="text-xs text-muted">
                      {u.email}
                      {u.last_sign_in_at ? ` · last sign-in ${shortDate(u.last_sign_in_at)}` : ""}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    className="text-xs"
                    onClick={() => {
                      setRegisterForm({
                        email: u.email,
                        company_name: u.suggested_company_name || "",
                      });
                      setRegisterPricing(DEFAULT_MERCHANT_PRICING);
                      setRegisterError(null);
                      setRegisterOpen(true);
                    }}
                  >
                    <UserPlus className="h-3.5 w-3.5" /> Register merchant
                  </Button>
                </div>
              ))}
              {unprovisioned.length > 8 && (
                <p className="px-4 py-2 text-xs text-muted">
                  +{unprovisioned.length - 8} more in Account Clerk directory
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="space-y-3 rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-semibold text-primary">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
              <SlidersHorizontal className="h-4 w-4" />
            </span>
            Filters
            {activeFilters > 0 && <Badge tone="blue">{activeFilters} active</Badge>}
            <span className="text-xs font-normal text-muted">
              · {rows.length.toLocaleString()} merchants
            </span>
          </span>
          {activeFilters > 0 && (
            <Button variant="ghost" onClick={clearFilters} className="text-xs">
              <X className="h-4 w-4" /> Clear
            </Button>
          )}
        </div>
        {facets.provinces.length > 0 && (
          <ProvincePills provinces={facets.provinces} value={province} onChange={setProvince} />
        )}
        <div className="flex flex-wrap items-center gap-2 border-t border-primary/5 pt-3">
          <Dropdown
            label="Status"
            value={status}
            onChange={setStatus}
            options={STATUSES.map((s) => ({ value: s, label: merchantStatusLabel(s) }))}
          />
          <Dropdown
            label="Industry"
            value={industry}
            onChange={setIndustry}
            options={facets.industries.map((i) => ({ value: i, label: i }))}
          />
          <Dropdown
            label="Terms"
            value={terms}
            onChange={setTerms}
            options={TERMS.map((t) => ({ value: t, label: titleCase(t) }))}
          />
          <Dropdown
            label="Contract"
            value={contract}
            onChange={setContract}
            options={[
              { value: "active", label: "Active" },
              { value: "none", label: "None" },
            ]}
          />
          <Dropdown
            label="Health"
            value={health}
            onChange={setHealth}
            allLabel="Any"
            options={[
              { value: "hot", label: "Healthy 70+" },
              { value: "warm", label: "Watch 40-69" },
              { value: "risk", label: "At risk <40" },
            ]}
          />
          <Dropdown
            label="Onboarding"
            value={onboardingFilter}
            onChange={setOnboardingFilter}
            allLabel="Any"
            options={[
              { value: "pending", label: "Not portal-ready" },
              { value: "ready", label: "Portal ready" },
            ]}
          />
          <Dropdown
            label="API"
            value={apiOnly}
            onChange={setApiOnly}
            allLabel="Any"
            options={[
              { value: "yes", label: "Connected" },
              { value: "no", label: "Not connected" },
            ]}
          />
          <Dropdown
            label="Sort"
            value={sortBy === "recent" ? "" : sortBy}
            onChange={(v) => setSortBy(v || "recent")}
            allLabel="Recent"
            options={[
              { value: "revenue", label: "Revenue" },
              { value: "health", label: "Health" },
              { value: "outstanding", label: "Outstanding" },
              { value: "name", label: "Name A–Z" },
            ]}
          />
        </div>
        {activeFilters > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t border-primary/5 pt-3">
            {province && (
              <FilterChip
                label={`Province: ${PROVINCE_NAMES[province] ?? province}`}
                onRemove={() => setProvince("")}
              />
            )}
            {city && <FilterChip label={`City: ${city}`} onRemove={() => setCity("")} />}
            {status && (
              <FilterChip
                label={`Status: ${merchantStatusLabel(status)}`}
                onRemove={() => setStatus("")}
              />
            )}
            {industry && (
              <FilterChip label={`Industry: ${industry}`} onRemove={() => setIndustry("")} />
            )}
            {terms && (
              <FilterChip label={`Terms: ${titleCase(terms)}`} onRemove={() => setTerms("")} />
            )}
            {contract && (
              <FilterChip
                label={`Contract: ${titleCase(contract)}`}
                onRemove={() => setContract("")}
              />
            )}
            {health && <FilterChip label={`Health: ${health}`} onRemove={() => setHealth("")} />}
            {onboardingFilter && (
              <FilterChip
                label={`Onboarding: ${onboardingFilter === "pending" ? "Not ready" : "Ready"}`}
                onRemove={() => setOnboardingFilter("")}
              />
            )}
            {apiOnly && <FilterChip label={`API: ${apiOnly}`} onRemove={() => setApiOnly("")} />}
          </div>
        )}
      </div>

      {/* Grid */}
      <div className="rounded-2xl border border-primary/10 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-primary/10 px-4 py-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search merchants…"
              className="w-64 rounded-xl border border-primary/15 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20"
            />
          </div>
          <div className="flex items-center gap-2">
            {views.length > 0 && (
              <select
                onChange={(e) => {
                  const v = views.find((x) => x.name === e.target.value);
                  if (v) setVisibility(v.visibility);
                }}
                className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
                defaultValue=""
              >
                <option value="">Saved views</option>
                {views.map((v) => (
                  <option key={v.name} value={v.name}>
                    {v.name}
                  </option>
                ))}
              </select>
            )}
            <Button variant="outline" onClick={saveView} className="text-xs">
              Save view
            </Button>
            <div className="relative" ref={chooserRef}>
              <Button
                variant="outline"
                onClick={() => setChooserOpen((o) => !o)}
                className="text-xs"
              >
                <Columns3 className="h-4 w-4" /> Columns
              </Button>
              {chooserOpen && (
                <div className="absolute right-0 z-30 mt-1 max-h-72 w-52 overflow-y-auto rounded-xl border border-primary/10 bg-white p-2 shadow-xl">
                  {table
                    .getAllLeafColumns()
                    .filter((c) => c.id !== "select")
                    .map((c) => (
                      <label
                        key={c.id}
                        className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-gray-bg"
                      >
                        <input
                          type="checkbox"
                          checked={c.getIsVisible()}
                          onChange={c.getToggleVisibilityHandler()}
                        />
                        {String(c.columnDef.header ?? c.id)}
                      </label>
                    ))}
                </div>
              )}
            </div>
            <Button variant="outline" onClick={exportCsv} className="text-xs">
              <Download className="h-4 w-4" /> Export
            </Button>
          </div>
        </div>

        {selectedIds.length > 0 && (
          <div className="flex items-center gap-3 border-b border-primary/10 bg-secondary/5 px-4 py-2 text-sm">
            <span className="font-medium text-primary">{selectedIds.length} selected</span>
            <Button
              variant="outline"
              onClick={() => bulk("activate")}
              disabled={!!busy}
              className="text-xs"
            >
              <Rocket className="h-4 w-4" /> Activate onboarding
            </Button>
            <Button
              variant="outline"
              onClick={() => bulk("approve")}
              disabled={!!busy}
              className="text-xs"
            >
              <CheckCircle2 className="h-4 w-4" /> Approve
            </Button>
            <Button
              variant="outline"
              onClick={() => bulk("suspend")}
              disabled={!!busy}
              className="text-xs"
            >
              Suspend
            </Button>
            <button
              onClick={() => setRowSelection({})}
              className="ml-auto text-xs text-muted hover:text-primary"
            >
              Clear
            </button>
          </div>
        )}

        {!data || !Array.isArray(data) ? (
          <Spinner label="Loading merchants…" />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No merchants match these filters"
            hint="Convert a company to a merchant from the CRM, or adjust filters."
          />
        ) : (
          <>
            <div className="ops-table-scroll">
              <table className="w-full min-w-[48rem] text-left text-sm">
                <thead className="border-b border-primary/10 bg-gray-bg/40">
                  {table.getHeaderGroups().map((hg) => (
                    <tr key={hg.id}>
                      {hg.headers.map((header) => {
                        const sortable =
                          header.column.getCanSort() && header.column.id !== "select";
                        return (
                          <th
                            key={header.id}
                            onClick={sortable ? header.column.getToggleSortingHandler() : undefined}
                            className={cn(
                              "whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted",
                              sortable && "cursor-pointer select-none"
                            )}
                          >
                            <span className="inline-flex items-center gap-1">
                              {flexRender(header.column.columnDef.header, header.getContext())}
                              {sortable && <ArrowUpDown className="h-3 w-3 opacity-50" />}
                            </span>
                          </th>
                        );
                      })}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => router.push(`/merchants/${row.original.id}`)}
                      className="cursor-pointer border-b border-primary/5 last:border-0 hover:bg-secondary/5"
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="whitespace-nowrap px-4 py-3 text-primary">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between border-t border-primary/10 px-4 py-3 text-sm text-muted">
              <span>
                Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()} ·{" "}
                {table.getFilteredRowModel().rows.length} merchants
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                  className="rounded-lg border border-primary/15 p-1.5 disabled:opacity-40"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                  className="rounded-lg border border-primary/15 p-1.5 disabled:opacity-40"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <Modal
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
        title="Register merchant"
        panelClassName="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
        footer={
          <>
            <Button variant="outline" onClick={() => setRegisterOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={
                !registerForm.email.trim() || !registerForm.company_name.trim() || registering
              }
              onClick={() => void registerMerchant(registerForm.email, registerForm.company_name)}
            >
              {registering ? "Creating…" : "Create & activate"}
            </Button>
          </>
        }
      >
        <div className="max-h-[70vh] space-y-6 overflow-y-auto pr-1">
          <p className="text-sm text-muted">
            Creates the merchant organization and reserves an owner seat. Set how they are priced
            now — you can change it later on the merchant Pricing tab.
          </p>
          <Field label="Owner email">
            <Input
              type="email"
              value={registerForm.email}
              onChange={(e) => setRegisterForm((f) => ({ ...f, email: e.target.value }))}
              placeholder="parevalogistics@gmail.com"
            />
          </Field>
          <Field label="Company name">
            <Input
              value={registerForm.company_name}
              onChange={(e) => setRegisterForm((f) => ({ ...f, company_name: e.target.value }))}
              placeholder="Pareva Logistics"
            />
          </Field>
          <div className="border-t border-primary/10 pt-5">
            <MerchantPricingFields value={registerPricing} onChange={setRegisterPricing} />
          </div>
          {registerError && <p className="text-sm text-red-600">{registerError}</p>}
        </div>
      </Modal>
    </AdminPage>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
  accent = "text-secondary",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted">{label}</p>
        <Icon className={`h-4 w-4 ${accent}`} />
      </div>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
    </div>
  );
}
