"use client";

import { useMemo, useState } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Company, type Contract } from "@/lib/crm";
import { CrmTable } from "@/components/crm/CrmTable";
import { Badge, Button, Drawer, Field, Input, Select } from "@/components/crm/primitives";
import { STATUS_TONE, money, shortDate, titleCase } from "@/lib/crmFormat";

const STATUSES = ["draft", "pending_signature", "active", "expired", "renewed", "terminated"];
const NET_TERMS = ["NET_15", "NET_30", "NET_45", "NET_60", "IMMEDIATE"];

export default function ContractsPage() {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data, error } = useApiData((t) => crm.contracts(t), [version]);
  const { data: companies } = useApiData((t) => crm.companies(t), [], { key: "crm-companies" });

  const [creating, setCreating] = useState(false);
  const [companyId, setCompanyId] = useState("");
  const [netTerms, setNetTerms] = useState("NET_30");
  const [value, setValue] = useState(0);
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [expiry, setExpiry] = useState("");
  const [selected, setSelected] = useState<Contract | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => setVersion((v) => v + 1);

  async function submitCreate() {
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createContract(token, {
        company_id: companyId || undefined,
        net_terms: netTerms,
        value_cents: Number(value) || 0,
        effective_from: effectiveFrom || undefined,
        expiry_date: expiry || undefined,
      });
      setCreating(false);
      setCompanyId("");
      setValue(0);
      setEffectiveFrom("");
      setExpiry("");
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(status: string) {
    if (!selected) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      const updated = await crm.updateContract(token, selected.id, { status });
      setSelected(updated);
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

  const columns = useMemo<ColumnDef<Contract, unknown>[]>(
    () => [
      {
        accessorKey: "contract_number",
        header: "Contract",
        cell: ({ getValue }) => (
          <span className="font-semibold text-primary">{String(getValue())}</span>
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
        accessorKey: "net_terms",
        header: "Terms",
        cell: ({ getValue }) => titleCase(String(getValue())),
      },
      {
        accessorKey: "value_cents",
        header: "Value",
        cell: ({ getValue }) => money(getValue() as number),
      },
      {
        accessorKey: "expiry_date",
        header: "Expiry",
        cell: ({ getValue }) => shortDate(getValue() as string),
      },
    ],
    [companyName]
  );

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      <CrmTable
        data={data}
        columns={columns}
        onRowClick={setSelected}
        searchPlaceholder="Search contracts…"
        emptyTitle="No contracts yet"
        emptyHint="Convert a quotation or create a contract to lock in a merchant agreement."
        toolbar={
          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" />
            New Contract
          </Button>
        }
      />

      <Drawer
        open={creating}
        onClose={() => setCreating(false)}
        title="New contract"
        footer={
          <>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button onClick={submitCreate} disabled={busy}>
              Create contract
            </Button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Company" className="col-span-2">
            <Select value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
              <option value="">— None —</option>
              {(companies ?? []).map((c: Company) => (
                <option key={c.id} value={c.id}>
                  {c.operating_name || c.legal_name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Net terms">
            <Select value={netTerms} onChange={(e) => setNetTerms(e.target.value)}>
              {NET_TERMS.map((t) => (
                <option key={t} value={t}>
                  {titleCase(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Annual value (cents)">
            <Input type="number" value={value} onChange={(e) => setValue(Number(e.target.value))} />
          </Field>
          <Field label="Effective from">
            <Input
              type="date"
              value={effectiveFrom}
              onChange={(e) => setEffectiveFrom(e.target.value)}
            />
          </Field>
          <Field label="Expiry date">
            <Input type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
          </Field>
        </div>
      </Drawer>

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.contract_number ?? "Contract"}
      >
        {selected && (
          <div className="space-y-5">
            <Badge tone={STATUS_TONE[selected.status]}>{titleCase(selected.status)}</Badge>
            <Field label="Update status">
              <Select
                value={selected.status}
                onChange={(e) => changeStatus(e.target.value)}
                disabled={busy}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {titleCase(s)}
                  </option>
                ))}
              </Select>
            </Field>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <Detail label="Company" value={companyName.get(selected.company_id ?? "")} />
              <Detail label="Net terms" value={titleCase(selected.net_terms)} />
              <Detail label="Value" value={money(selected.value_cents)} />
              <Detail label="Effective from" value={shortDate(selected.effective_from)} />
              <Detail label="Expiry" value={shortDate(selected.expiry_date)} />
              <Detail label="Renewal reminder" value={shortDate(selected.renewal_reminder_at)} />
            </dl>
            {selected.company_id && (
              <p className="text-xs text-muted">
                SLA: {JSON.stringify(selected.sla) === "{}" ? "—" : JSON.stringify(selected.sla)}
              </p>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-primary">{value || "—"}</dd>
    </div>
  );
}
