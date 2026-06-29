"use client";

import { useMemo, useState } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { Plus, Trash2, Send, CheckCircle2, FileSignature } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Company, type Deal, type Quotation } from "@/lib/crm";
import { CrmTable } from "@/components/crm/CrmTable";
import { Badge, Button, Drawer, Field, Input, Select } from "@/components/crm/primitives";
import { STATUS_TONE, money, shortDate, titleCase } from "@/lib/crmFormat";

type DraftLine = { label: string; quantity: number; unit_price_cents: number };

export default function QuotationsPage() {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data, error } = useApiData((t) => crm.quotations(t), [version]);
  const { data: companies } = useApiData((t) => crm.companies(t), []);
  const { data: deals } = useApiData((t) => crm.deals(t), []);

  const [creating, setCreating] = useState(false);
  const [companyId, setCompanyId] = useState("");
  const [dealId, setDealId] = useState("");
  const [taxCents, setTaxCents] = useState(0);
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([
    { label: "", quantity: 1, unit_price_cents: 0 },
  ]);
  const [selected, setSelected] = useState<Quotation | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const refresh = () => setVersion((v) => v + 1);
  const subtotal = lines.reduce((sum, l) => sum + l.quantity * l.unit_price_cents, 0);

  function resetForm() {
    setCompanyId("");
    setDealId("");
    setTaxCents(0);
    setNotes("");
    setLines([{ label: "", quantity: 1, unit_price_cents: 0 }]);
  }

  async function submitCreate() {
    const valid = lines.filter((l) => l.label.trim());
    if (valid.length === 0) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createQuotation(token, {
        company_id: companyId || undefined,
        deal_id: dealId || undefined,
        line_items: valid,
        tax_cents: Number(taxCents) || 0,
        notes: notes || undefined,
      });
      setCreating(false);
      resetForm();
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(q: Quotation, status: string) {
    setBusy(true);
    try {
      const token = await getApiToken();
      const updated = await crm.setQuotationStatus(token, q.id, status);
      setSelected(updated);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function convert(q: Quotation) {
    setBusy(true);
    try {
      const token = await getApiToken();
      const contract = await crm.convertQuotation(token, q.id);
      setSelected(null);
      setToast(`Contract ${contract.contract_number} created.`);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  const companyName = useMemo(() => {
    const m = new Map<string, string>();
    (companies ?? []).forEach((c: Company) => m.set(c.id, c.operating_name || c.legal_name));
    return m;
  }, [companies]);

  const columns = useMemo<ColumnDef<Quotation, unknown>[]>(
    () => [
      {
        accessorKey: "quote_number",
        header: "Quote",
        cell: ({ row }) => (
          <span className="font-semibold text-primary">
            {row.original.quote_number}{" "}
            <span className="text-xs text-muted">v{row.original.version}</span>
          </span>
        ),
      },
      {
        accessorKey: "company_id",
        header: "Company",
        cell: ({ getValue }) => companyName.get(String(getValue())) ?? "—",
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ getValue }) => (
          <Badge tone={STATUS_TONE[String(getValue())]}>{titleCase(String(getValue()))}</Badge>
        ),
      },
      {
        accessorKey: "total_cents",
        header: "Total",
        cell: ({ getValue }) => money(getValue() as number),
      },
      {
        accessorKey: "valid_until",
        header: "Valid until",
        cell: ({ getValue }) => shortDate(getValue() as string),
      },
      {
        accessorKey: "created_at",
        header: "Created",
        cell: ({ getValue }) => shortDate(String(getValue())),
      },
    ],
    [companyName]
  );

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      {toast && (
        <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
          {toast}
        </div>
      )}
      <CrmTable
        data={data}
        columns={columns}
        onRowClick={setSelected}
        searchPlaceholder="Search quotations…"
        emptyTitle="No quotations yet"
        emptyHint="Generate a quotation for a deal and convert it into a contract."
        toolbar={
          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" />
            New Quotation
          </Button>
        }
      />

      {/* Create quotation */}
      <Drawer
        open={creating}
        onClose={() => setCreating(false)}
        title="New quotation"
        footer={
          <>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button onClick={submitCreate} disabled={busy}>
              Create quotation
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Company">
              <Select value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
                <option value="">— None —</option>
                {(companies ?? []).map((c: Company) => (
                  <option key={c.id} value={c.id}>
                    {c.operating_name || c.legal_name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Deal">
              <Select value={dealId} onChange={(e) => setDealId(e.target.value)}>
                <option value="">— None —</option>
                {(deals ?? []).map((d: Deal) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium text-primary/70">Line items</p>
            <div className="space-y-2">
              {lines.map((line, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Input
                    placeholder="Description"
                    value={line.label}
                    onChange={(e) =>
                      setLines(lines.map((l, j) => (j === i ? { ...l, label: e.target.value } : l)))
                    }
                  />
                  <Input
                    type="number"
                    className="w-20"
                    placeholder="Qty"
                    value={line.quantity}
                    onChange={(e) =>
                      setLines(
                        lines.map((l, j) =>
                          j === i ? { ...l, quantity: Number(e.target.value) } : l
                        )
                      )
                    }
                  />
                  <Input
                    type="number"
                    className="w-28"
                    placeholder="Unit ¢"
                    value={line.unit_price_cents}
                    onChange={(e) =>
                      setLines(
                        lines.map((l, j) =>
                          j === i ? { ...l, unit_price_cents: Number(e.target.value) } : l
                        )
                      )
                    }
                  />
                  <button
                    type="button"
                    onClick={() => setLines(lines.filter((_, j) => j !== i))}
                    className="rounded-lg p-2 text-muted hover:bg-gray-bg"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
            <Button
              variant="ghost"
              className="mt-2"
              onClick={() => setLines([...lines, { label: "", quantity: 1, unit_price_cents: 0 }])}
            >
              <Plus className="h-4 w-4" />
              Add line
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Tax (cents)">
              <Input
                type="number"
                value={taxCents}
                onChange={(e) => setTaxCents(Number(e.target.value))}
              />
            </Field>
            <div className="flex items-end justify-end">
              <div className="text-right">
                <p className="text-xs text-muted">Subtotal {money(subtotal)}</p>
                <p className="text-lg font-bold text-primary">
                  Total {money(subtotal + Number(taxCents || 0))}
                </p>
              </div>
            </div>
          </div>
          <Field label="Notes">
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
        </div>
      </Drawer>

      {/* Quotation detail */}
      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected ? `${selected.quote_number} · v${selected.version}` : "Quotation"}
        footer={
          selected && (
            <div className="flex flex-wrap gap-2">
              {selected.status === "draft" && (
                <Button
                  variant="outline"
                  onClick={() => setStatus(selected, "sent")}
                  disabled={busy}
                >
                  <Send className="h-4 w-4" />
                  Send
                </Button>
              )}
              {(selected.status === "sent" || selected.status === "draft") && (
                <Button
                  variant="outline"
                  onClick={() => setStatus(selected, "approved")}
                  disabled={busy}
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Approve
                </Button>
              )}
              {selected.status !== "converted" && (
                <Button onClick={() => convert(selected)} disabled={busy}>
                  <FileSignature className="h-4 w-4" />
                  Convert to contract
                </Button>
              )}
            </div>
          )
        }
      >
        {selected && (
          <div className="space-y-5">
            <Badge tone={STATUS_TONE[selected.status]}>{titleCase(selected.status)}</Badge>
            <div className="overflow-hidden rounded-xl border border-primary/10">
              <table className="w-full text-sm">
                <thead className="bg-gray-bg/50 text-xs uppercase text-muted">
                  <tr>
                    <th className="px-3 py-2 text-left">Item</th>
                    <th className="px-3 py-2 text-right">Qty</th>
                    <th className="px-3 py-2 text-right">Unit</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.line_items.map((li, i) => (
                    <tr key={i} className="border-t border-primary/5">
                      <td className="px-3 py-2">{li.label}</td>
                      <td className="px-3 py-2 text-right">{li.quantity}</td>
                      <td className="px-3 py-2 text-right">{money(li.unit_price_cents)}</td>
                      <td className="px-3 py-2 text-right">{money(li.amount_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="space-y-1 text-right text-sm">
              <p className="text-muted">Subtotal {money(selected.subtotal_cents)}</p>
              <p className="text-muted">Tax {money(selected.tax_cents)}</p>
              <p className="text-lg font-bold text-primary">Total {money(selected.total_cents)}</p>
            </div>
            {selected.notes && <p className="text-sm text-muted">{selected.notes}</p>}
          </div>
        )}
      </Drawer>
    </div>
  );
}
