"use client";

import { useCallback, useDeferredValue, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Building2, Layers, Plus, Store } from "lucide-react";
import { TableSkeleton } from "@porterchain/ui/loading";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  Input,
  Modal,
  SectionCard,
  Select,
} from "@/components/crm/primitives";
import { FilterChip } from "@/components/crm/filters";
import { CsvButton, FacetButton, SearchBox, StatTile } from "@/components/console/ConsoleKit";
import AdminPage from "@/components/layout/AdminPage";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { orgsApi, typeLabel, type BusinessTypes, type OrgList } from "@/lib/orgs";

const PAGE = 25;
const STATUS_TONE: Record<string, string> = {
  active: "green",
  pending: "amber",
  suspended: "red",
  closed: "slate",
};

/** Types & packs: every account's business type, capability pack and review state. */
export function OrgsListClient() {
  const { getApiToken } = useAdminAuth();
  const [types, setTypes] = useState<BusinessTypes | null>(null);
  const [data, setData] = useState<OrgList | null>(null);
  const [filter, setFilter] = useState("");
  const [review, setReview] = useState(false);
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const dq = useDeferredValue(q);
  const [offset, setOffset] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [newType, setNewType] = useState("small_shop");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    void (async () => setTypes(await orgsApi.types(await getApiToken())))().catch((e) =>
      setErr(String(e))
    );
  }, [getApiToken]);

  const load = useCallback(async () => {
    const t = await getApiToken();
    setData(
      await orgsApi.list(t, {
        business_type: filter || undefined,
        needs_review: review ? true : undefined,
        status: status || undefined,
        q: dq,
        limit: PAGE,
        offset,
      })
    );
  }, [getApiToken, filter, review, status, dq, offset]);
  useEffect(() => {
    void load().catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, [load]);
  useEffect(() => setOffset(0), [filter, review, status, dq]);

  async function create() {
    if (!name.trim()) return;
    try {
      const org = await orgsApi.create(await getApiToken(), {
        display_name: name.trim(),
        business_type: newType,
      });
      setName("");
      setCreateOpen(false);
      setMsg(`Created ${org.public_id}`);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Create failed");
    }
  }

  const items = data?.items ?? [];
  const total = data?.total ?? items.length;
  const counts = data?.counts;
  const bt = types?.business_types ?? [];
  const topTypes = [...bt]
    .sort((a, b) => (counts?.by_type[b.code] ?? 0) - (counts?.by_type[a.code] ?? 0))
    .slice(0, 6);
  const capCount = (caps: Record<string, boolean>) =>
    Object.values(caps ?? {}).filter(Boolean).length;

  return (
    <AdminPage
      title="Types & packs"
      description="Business type, capability pack and operating profile for every account."
      actions={
        <div className="flex flex-wrap gap-2">
          <CsvButton
            filename="organisations.csv"
            headers={["ID", "Name", "Type", "Subtype", "Status", "Capabilities on", "Needs review"]}
            rows={items.map((o) => [
              o.public_id,
              o.display_name,
              typeLabel(bt, o.business_type),
              o.subtype ?? "",
              o.status,
              String(capCount(o.capabilities)),
              o.needs_review ? "yes" : "",
            ])}
          />
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" /> New organisation
          </Button>
        </div>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={Building2}
          label="Organisations"
          value={String(counts?.all ?? total)}
          active={!filter && !review}
          onClick={() => {
            setFilter("");
            setReview(false);
          }}
        />
        <StatTile
          icon={AlertTriangle}
          label="Needs type review"
          value={String(counts?.needs_review ?? 0)}
          accent="text-amber-600"
          active={review}
          onClick={() => setReview(!review)}
        />
        <StatTile
          icon={Layers}
          label="Business types in use"
          value={String(Object.values(counts?.by_type ?? {}).filter((n) => n > 0).length)}
        />
        <StatTile
          icon={Store}
          label="Types available"
          value={String(bt.length)}
          accent="text-slate-600"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <SearchBox value={q} onChange={setQ} placeholder="Search name, legal name or ID…" />
        <FacetButton active={filter === ""} onClick={() => setFilter("")}>
          All types
        </FacetButton>
        {topTypes.map((b) => (
          <FacetButton
            key={b.code}
            active={filter === b.code}
            onClick={() => setFilter(filter === b.code ? "" : b.code)}
          >
            {b.label} <span className="text-muted">{counts?.by_type[b.code] ?? 0}</span>
          </FacetButton>
        ))}
        <Select
          aria-label="Business type"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="!w-auto min-w-[10rem]"
        >
          <option value="">More types…</option>
          {bt.map((b) => (
            <option key={b.code} value={b.code}>
              {b.label} ({counts?.by_type[b.code] ?? 0})
            </option>
          ))}
        </Select>
        <Select
          aria-label="Status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="!w-auto min-w-[10rem]"
        >
          <option value="">Any status</option>
          {Object.keys(STATUS_TONE).map((s) => (
            <option key={s} value={s}>
              {s[0].toUpperCase() + s.slice(1)}
            </option>
          ))}
        </Select>
      </div>
      {(filter || review || status) && (
        <div className="flex flex-wrap gap-2">
          {filter && (
            <FilterChip label={`Type: ${typeLabel(bt, filter)}`} onRemove={() => setFilter("")} />
          )}
          {status && <FilterChip label={`Status: ${status}`} onRemove={() => setStatus("")} />}
          {review && <FilterChip label="Needs type review" onRemove={() => setReview(false)} />}
        </div>
      )}
      {msg ? <p className="text-sm text-green-700">{msg}</p> : null}
      {err ? (
        <p role="alert" className="text-sm text-red-700">
          {err}
        </p>
      ) : null}

      <SectionCard title={`Organisations (${total})`}>
        {data === null && !err ? (
          <TableSkeleton rows={8} />
        ) : items.length === 0 ? (
          <EmptyState
            title={counts?.all ? "No organisations match" : "No organisations yet"}
            hint={
              counts?.all
                ? "Clear the search or filters."
                : "Organisations are created at merchant signup, or add one here."
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-2">Organisation</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="hidden px-4 py-2 md:table-cell">Pack</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="hidden px-4 py-2 sm:table-cell">Merchant</th>
                </tr>
              </thead>
              <tbody>
                {items.map((o) => (
                  <tr key={o.id} className="border-b border-primary/5 hover:bg-gray-bg/40">
                    <td className="px-4 py-3">
                      <Link
                        className="font-medium text-primary hover:underline"
                        href={`/orgs/${o.id}`}
                      >
                        {o.display_name}
                      </Link>
                      <p className="font-mono text-xs text-muted">{o.public_id}</p>
                    </td>
                    <td className="px-4 py-3">
                      {typeLabel(bt, o.business_type)}
                      {o.subtype ? (
                        <span className="block text-xs text-muted">
                          {o.subtype.replace(/_/g, " ")}
                        </span>
                      ) : null}
                      {o.needs_review ? (
                        <Badge tone="amber" className="mt-1">
                          Review type
                        </Badge>
                      ) : null}
                    </td>
                    <td className="hidden px-4 py-3 text-xs text-muted md:table-cell">
                      {capCount(o.capabilities)} capabilities on
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={STATUS_TONE[o.status] ?? "slate"}>{o.status}</Badge>
                    </td>
                    <td className="hidden px-4 py-3 sm:table-cell">
                      {o.merchant_id ? (
                        <Link
                          className="text-secondary hover:underline"
                          href={`/merchants/${o.merchant_id}`}
                        >
                          Open
                        </Link>
                      ) : (
                        <span className="text-xs text-muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-between px-4 py-3 text-sm text-muted">
              <span>
                {offset + 1}–{Math.min(offset + PAGE, total)} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE))}
                >
                  Previous
                </Button>
                <Button disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>
                  Next
                </Button>
              </div>
            </div>
          </div>
        )}
      </SectionCard>

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="New organisation"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={() => void create()} disabled={!name.trim()}>
              Create
            </Button>
          </div>
        }
      >
        <div className="grid gap-3">
          <Field label="Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field
            label="Business type"
            hint="Sets the default capability pack; staff can change it later."
          >
            <Select value={newType} onChange={(e) => setNewType(e.target.value)}>
              {bt.map((b) => (
                <option key={b.code} value={b.code}>
                  {b.label}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </Modal>
    </AdminPage>
  );
}
