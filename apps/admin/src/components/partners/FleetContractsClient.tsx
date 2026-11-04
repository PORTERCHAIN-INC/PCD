"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { TableSkeleton } from "@porterchain/ui/loading";
import {
  Badge,
  Button,
  Drawer,
  EmptyState,
  Field,
  Input,
  SectionCard,
  Select,
  Textarea,
} from "@/components/crm/primitives";
import AdminPage from "@/components/layout/AdminPage";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { money } from "@/lib/crmFormat";
import {
  dispatch,
  type FleetContract,
  type FleetRateBasis,
  type LogisticsPartner,
  type PayableStatement,
} from "@/lib/dispatch";

const BASIS_LABEL: Record<FleetRateBasis, string> = {
  stop: "Per stop",
  parcel: "Per parcel",
  route: "Per route",
  hour: "Per hour",
};
const dollars = (c: number) => (c / 100).toFixed(2);
const today = () => new Date().toISOString().slice(0, 10);
const monthStart = () => today().slice(0, 8) + "01";

function blank(partnerId: string): FleetContract {
  return {
    partner_id: partnerId,
    effective_from: today(),
    effective_to: null,
    rate_basis: "stop",
    rate_cents: 0,
    min_charge_cents: 0,
    document_ref: null,
    notes: null,
    is_dummy: false,
  };
}

/** Network → Fleet contracts: manually entered contractor fleet rates and the payable per completed job. */
export function FleetContractsClient() {
  const { getApiToken } = useAdminAuth();
  const [items, setItems] = useState<FleetContract[] | null>(null);
  const [partners, setPartners] = useState<LogisticsPartner[]>([]);
  const [edit, setEdit] = useState<FleetContract | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [formErr, setFormErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [stPartner, setStPartner] = useState("");
  const [stStart, setStStart] = useState(monthStart());
  const [stEnd, setStEnd] = useState(today());
  const [statement, setStatement] = useState<PayableStatement | null>(null);

  const load = useCallback(async () => {
    const t = await getApiToken();
    const [c, p] = await Promise.all([dispatch.fleetContracts(t), dispatch.partners(t)]);
    setItems(c.items);
    setPartners(p.items);
  }, [getApiToken]);
  useEffect(() => {
    void load().catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, [load]);

  const fleets = useMemo(
    () => partners.filter((p) => p.kind === "courier" || p.kind === "3pl"),
    [partners]
  );
  const pick = fleets.length ? fleets : partners;

  async function save() {
    if (!edit) return;
    setSaving(true);
    setFormErr(null);
    try {
      await dispatch.saveFleetContract(await getApiToken(), edit);
      setEdit(null);
      await load();
    } catch (e) {
      setFormErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    if (!window.confirm("Delete this contract?")) return;
    try {
      await dispatch.deleteFleetContract(await getApiToken(), id);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function runStatement() {
    if (!stPartner) return;
    setErr(null);
    try {
      setStatement(await dispatch.payableStatement(await getApiToken(), stPartner, stStart, stEnd));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <AdminPage
      title="Fleet contracts"
      description="Fixed rates contractor fleets charge us. Entered by hand from the signed contract."
      actions={
        <Button onClick={() => setEdit(blank(pick[0]?.id ?? ""))} disabled={!pick.length}>
          Add contract
        </Button>
      }
    >
      {err ? (
        <p role="alert" className="text-sm text-red-700">
          {err}
        </p>
      ) : null}

      <SectionCard title={`Contracts (${items?.length ?? 0})`}>
        {items === null && !err ? (
          <TableSkeleton rows={4} />
        ) : !items?.length ? (
          <EmptyState
            title="No fleet contracts yet"
            hint="Add the company, dates and rate from the contract."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-2">Company</th>
                  <th className="px-4 py-2">Effective</th>
                  <th className="px-4 py-2">Basis</th>
                  <th className="px-4 py-2 text-right">Rate</th>
                  <th className="px-4 py-2 text-right">Minimum</th>
                  <th className="px-4 py-2">Document</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <tr key={c.id} className="border-b border-primary/5">
                    <td className="px-4 py-2 font-medium text-primary">
                      {c.partner_name ?? c.partner_id}{" "}
                      {c.is_dummy ? <Badge tone="amber">Dummy</Badge> : null}
                    </td>
                    <td className="px-4 py-2">
                      {c.effective_from} → {c.effective_to ?? "open"}
                    </td>
                    <td className="px-4 py-2">{BASIS_LABEL[c.rate_basis]}</td>
                    <td className="px-4 py-2 text-right">{money(c.rate_cents)}</td>
                    <td className="px-4 py-2 text-right">{money(c.min_charge_cents)}</td>
                    <td className="px-4 py-2">{c.document_ref ?? "—"}</td>
                    <td className="px-4 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => setEdit({ ...c })}>
                          Edit
                        </Button>
                        <Button variant="outline" onClick={() => c.id && void remove(c.id)}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Payable statement">
        <div className="flex flex-wrap items-end gap-3 p-4">
          <Field label="Company">
            <Select value={stPartner} onChange={(e) => setStPartner(e.target.value)}>
              <option value="">Choose…</option>
              {pick.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="From">
            <Input type="date" value={stStart} onChange={(e) => setStStart(e.target.value)} />
          </Field>
          <Field label="To">
            <Input type="date" value={stEnd} onChange={(e) => setStEnd(e.target.value)} />
          </Field>
          <Button onClick={() => void runStatement()} disabled={!stPartner}>
            Build statement
          </Button>
        </div>
        {statement ? (
          <div className="overflow-x-auto px-4 pb-4">
            {statement.jobs.length === 0 ? (
              <EmptyState title="No completed jobs in this period" />
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
                  <tr>
                    <th className="px-4 py-2">Completed</th>
                    <th className="px-4 py-2">Order</th>
                    <th className="px-4 py-2">Leg</th>
                    <th className="px-4 py-2">Basis</th>
                    <th className="px-4 py-2 text-right">Units</th>
                    <th className="px-4 py-2 text-right">Charge</th>
                  </tr>
                </thead>
                <tbody>
                  {statement.jobs.map((j) => (
                    <tr key={j.leg_id} className="border-b border-primary/5">
                      <td className="px-4 py-2">{j.completed_at.slice(0, 10)}</td>
                      <td className="px-4 py-2">{j.order_number ?? j.order_id.slice(0, 8)}</td>
                      <td className="px-4 py-2">
                        {j.from} → {j.to}
                      </td>
                      <td className="px-4 py-2">{BASIS_LABEL[j.rate_basis]}</td>
                      <td className="px-4 py-2 text-right">{j.units}</td>
                      <td className="px-4 py-2 text-right">
                        {money(j.charge_cents)}{" "}
                        {j.min_applied ? <Badge tone="slate">Minimum</Badge> : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={5} className="px-4 py-2 text-right font-medium">
                      Total payable
                    </td>
                    <td className="px-4 py-2 text-right font-semibold" data-testid="payable-total">
                      {money(statement.total_cents)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            )}
            {statement.unpriced.length ? (
              <p className="mt-2 text-sm text-amber-700">
                {statement.unpriced.length} completed job(s) have no contract on their date and are
                not priced.
              </p>
            ) : null}
          </div>
        ) : null}
      </SectionCard>

      <Drawer
        open={edit !== null}
        onClose={() => setEdit(null)}
        title={edit?.id ? "Edit contract" : "Add contract"}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setEdit(null)}>Cancel</Button>
            <Button onClick={() => void save()} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        }
      >
        {edit && (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Company" className="sm:col-span-2">
              <Select
                value={edit.partner_id}
                disabled={!!edit.id}
                onChange={(e) => setEdit({ ...edit, partner_id: e.target.value })}
              >
                {pick.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Effective from">
              <Input
                type="date"
                value={edit.effective_from}
                onChange={(e) => setEdit({ ...edit, effective_from: e.target.value })}
              />
            </Field>
            <Field label="Effective to" hint="Leave blank if open-ended">
              <Input
                type="date"
                value={edit.effective_to ?? ""}
                onChange={(e) => setEdit({ ...edit, effective_to: e.target.value || null })}
              />
            </Field>
            <Field label="Rate basis">
              <Select
                value={edit.rate_basis}
                onChange={(e) => setEdit({ ...edit, rate_basis: e.target.value as FleetRateBasis })}
              >
                {(Object.keys(BASIS_LABEL) as FleetRateBasis[]).map((b) => (
                  <option key={b} value={b}>
                    {BASIS_LABEL[b]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Rate ($)">
              <Input
                type="number"
                min={0}
                step="0.01"
                value={dollars(edit.rate_cents)}
                onChange={(e) =>
                  setEdit({ ...edit, rate_cents: Math.round((Number(e.target.value) || 0) * 100) })
                }
              />
            </Field>
            <Field label="Minimum per job ($)">
              <Input
                type="number"
                min={0}
                step="0.01"
                value={dollars(edit.min_charge_cents)}
                onChange={(e) =>
                  setEdit({
                    ...edit,
                    min_charge_cents: Math.round((Number(e.target.value) || 0) * 100),
                  })
                }
              />
            </Field>
            <Field label="Contract document reference">
              <Input
                value={edit.document_ref ?? ""}
                onChange={(e) => setEdit({ ...edit, document_ref: e.target.value || null })}
              />
            </Field>
            <Field label="Notes" className="sm:col-span-2">
              <Textarea
                rows={3}
                value={edit.notes ?? ""}
                onChange={(e) => setEdit({ ...edit, notes: e.target.value || null })}
              />
            </Field>
            <label className="flex items-center gap-2 text-sm text-primary sm:col-span-2">
              <input
                type="checkbox"
                checked={edit.is_dummy}
                onChange={(e) => setEdit({ ...edit, is_dummy: e.target.checked })}
              />{" "}
              Dummy (rehearsal only)
            </label>
            {formErr ? (
              <p role="alert" className="text-sm text-red-700 sm:col-span-2">
                {formErr}
              </p>
            ) : null}
          </div>
        )}
      </Drawer>
    </AdminPage>
  );
}
