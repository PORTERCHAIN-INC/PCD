"use client";

import { useRef, useState } from "react";
import { Download, Upload, FileSpreadsheet, CheckCircle2, AlertTriangle } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { crm, type ImportResult } from "@/lib/crm";
import { Badge, Button, SectionCard, Select } from "@/components/crm/primitives";
import { downloadCsv, parseCsv, toCsv, titleCase } from "@/lib/crmFormat";

const TEMPLATES: Record<string, { headers: string[]; sample: string[][] }> = {
  companies: {
    headers: [
      "legal_name",
      "operating_name",
      "industry",
      "website",
      "email",
      "phone",
      "service_area",
      "estimated_deliveries_per_month",
      "merchant_status",
    ],
    sample: [
      [
        "Acme Freight Ltd.",
        "Acme Freight",
        "Wholesale & Distribution",
        "https://acme.ca",
        "ops@acme.ca",
        "+1 416-555-0100",
        "Greater Toronto Area",
        "450",
        "prospect",
      ],
      [
        "Lakeshore Foods Inc.",
        "Lakeshore Foods",
        "Food & Beverage",
        "https://lakeshore.ca",
        "logistics@lakeshore.ca",
        "+1 905-555-0110",
        "Ontario",
        "220",
        "lead",
      ],
    ],
  },
  contacts: {
    headers: ["first_name", "last_name", "designation", "email", "phone", "mobile", "company_id"],
    sample: [
      [
        "Jordan",
        "Lee",
        "Operations Manager",
        "jordan@acme.ca",
        "+1 416-555-0101",
        "+1 416-555-9101",
        "",
      ],
      ["Priya", "Sharma", "Accounts Payable", "priya@lakeshore.ca", "+1 905-555-0111", "", ""],
    ],
  },
  leads: {
    headers: [
      "company_name",
      "industry",
      "primary_contact_name",
      "email",
      "phone",
      "source",
      "estimated_deliveries_per_month",
      "estimated_revenue_cents",
      "service_area",
    ],
    sample: [
      [
        "Bright Pharma",
        "Healthcare & Medical",
        "Dana White",
        "dana@brightpharma.ca",
        "+1 647-555-0120",
        "website",
        "300",
        "1800000",
        "GTA",
      ],
      [
        "Urban Threads",
        "Retail",
        "Sam Okafor",
        "sam@urbanthreads.ca",
        "+1 416-555-0130",
        "referral",
        "150",
        "750000",
        "Toronto Core",
      ],
    ],
  },
  deals: {
    headers: ["name", "company_id", "stage", "expected_revenue_cents"],
    sample: [
      ["Acme Freight — Merchant Program", "", "qualified", "4800000"],
      ["Lakeshore Foods — Pilot", "", "prospecting", "1200000"],
    ],
  },
};

export default function ImportPage() {
  const { getApiToken } = useAdminAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [entity, setEntity] = useState("companies");
  const [rows, setRows] = useState<Array<Record<string, string>>>([]);
  const [filename, setFilename] = useState("");
  const [dedupe, setDedupe] = useState(true);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);

  function downloadTemplate(name: string) {
    const tpl = TEMPLATES[name];
    downloadCsv(`${name}.csv`, toCsv(tpl.headers, tpl.sample));
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFilename(file.name);
    setResult(null);
    const text = await file.text();
    setRows(parseCsv(text));
  }

  async function runImport() {
    if (rows.length === 0) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      const res = await crm.import(token, entity, rows, dedupe);
      setResult(res);
    } finally {
      setBusy(false);
    }
  }

  const headers = rows.length ? Object.keys(rows[0]) : [];

  return (
    <div className="space-y-6">
      <SectionCard title="Download sample templates">
        <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
          {Object.keys(TEMPLATES).map((name) => (
            <button
              key={name}
              onClick={() => downloadTemplate(name)}
              className="flex items-center gap-3 rounded-xl border border-primary/10 p-3 text-left transition-colors hover:bg-gray-bg"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
                <FileSpreadsheet className="h-4 w-4" />
              </span>
              <div>
                <p className="text-sm font-medium text-primary">{name}.csv</p>
                <p className="flex items-center gap-1 text-xs text-muted">
                  <Download className="h-3 w-3" /> Template
                </p>
              </div>
            </button>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Import records">
        <div className="space-y-4 p-5">
          <div className="flex flex-wrap items-end gap-3">
            <label className="space-y-1">
              <span className="text-xs font-medium text-primary/70">Record type</span>
              <Select value={entity} onChange={(e) => setEntity(e.target.value)} className="w-44">
                {Object.keys(TEMPLATES).map((name) => (
                  <option key={name} value={name}>
                    {titleCase(name)}
                  </option>
                ))}
              </Select>
            </label>
            <Button variant="outline" onClick={() => fileRef.current?.click()}>
              <Upload className="h-4 w-4" />
              {filename || "Choose CSV file"}
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={onFile}
            />
            <label className="flex items-center gap-2 text-sm text-primary">
              <input
                type="checkbox"
                checked={dedupe}
                onChange={(e) => setDedupe(e.target.checked)}
              />
              Detect duplicates
            </label>
            <Button onClick={runImport} disabled={busy || rows.length === 0} className="ml-auto">
              Import {rows.length > 0 ? `${rows.length} rows` : ""}
            </Button>
          </div>

          {result && (
            <div
              className={
                "flex flex-wrap items-center gap-4 rounded-xl border px-4 py-3 text-sm " +
                (result.errors.length
                  ? "border-amber-200 bg-amber-50"
                  : "border-green-200 bg-green-50")
              }
            >
              {result.errors.length ? (
                <AlertTriangle className="h-5 w-5 text-amber-600" />
              ) : (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              )}
              <span>
                <strong>{result.imported}</strong> imported
              </span>
              <span>
                <strong>{result.duplicates}</strong> duplicates skipped
              </span>
              <span>
                <strong>{result.errors.length}</strong> errors
              </span>
              {result.errors.slice(0, 3).map((err) => (
                <Badge key={err.row} tone="red">
                  Row {err.row}: {err.error}
                </Badge>
              ))}
            </div>
          )}

          {rows.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium text-muted">Preview ({rows.length} rows)</p>
              <div className="max-h-80 overflow-auto rounded-xl border border-primary/10">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-gray-bg/80 text-xs uppercase text-muted">
                    <tr>
                      {headers.map((h) => (
                        <th key={h} className="whitespace-nowrap px-3 py-2">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.slice(0, 50).map((row, i) => (
                      <tr key={i} className="border-t border-primary/5">
                        {headers.map((h) => (
                          <td key={h} className="whitespace-nowrap px-3 py-2 text-primary">
                            {row[h]}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
