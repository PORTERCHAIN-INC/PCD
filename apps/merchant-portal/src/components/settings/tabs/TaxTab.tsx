"use client";

import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import { settingsApi, type SettingsOverview } from "@/lib/settings";
import { formatDate } from "@/lib/utils";
import { Field } from "./Field";

export function TaxTab({
  tax,
  onRefresh,
  getToken,
  orgId,
}: {
  tax: SettingsOverview["tax"];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [form, setForm] = useState(tax);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setForm(tax);
  }, [tax]);

  const save = async () => {
    const token = await getToken();
    const patch: Parameters<typeof settingsApi.updateTax>[1] = {};
    if ((form.hst_number || "") !== (tax.hst_number || "")) {
      patch.hst_number = form.hst_number || "";
    }
    if ((form.business_number || "") !== (tax.business_number || "")) {
      patch.business_number = form.business_number || "";
    }
    if (form.tax_exempt !== tax.tax_exempt) {
      patch.tax_exempt = form.tax_exempt;
    }
    if ((form.tax_region || "ON") !== (tax.tax_region || "ON")) {
      patch.tax_region = form.tax_region || "ON";
    }
    if (Object.keys(patch).length) {
      await settingsApi.updateTax(token, patch, orgId);
    }
    setSaved(true);
    await onRefresh();
    setTimeout(() => setSaved(false), 2000);
  };

  const writer = tax.tax_legal_meta;

  return (
    <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Tax information</h2>
      <p className="text-sm text-muted">
        Legal name on invoices is on the Business profile tab. Last save of HST, business number,
        region, or exemption wins — admin and this portal share the same fields.
      </p>
      <p className="text-sm">
        <span className="font-medium text-primary">Legal name</span>
        <span className="mt-1 block text-muted">{tax.legal_name || "—"}</span>
      </p>
      <Field
        label="HST number"
        value={form.hst_number || ""}
        onChange={(v) => setForm({ ...form, hst_number: v })}
      />
      <Field
        label="Business number"
        value={form.business_number || ""}
        onChange={(v) => setForm({ ...form, business_number: v })}
      />
      <Field
        label="Tax region"
        value={form.tax_region}
        onChange={(v) => setForm({ ...form, tax_region: v })}
      />
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.tax_exempt}
          onChange={(e) => setForm({ ...form, tax_exempt: e.target.checked })}
        />
        Tax exempt
      </label>
      {writer?.updated_at ? (
        <p className="text-xs text-muted">
          Last updated by {writer.updated_by || "someone"} {formatDate(writer.updated_at)}
          {writer.fields?.length ? ` · ${writer.fields.join(", ")}` : ""}
        </p>
      ) : null}
      <Button size="sm" onClick={() => void save()}>
        Save tax info
      </Button>
      {saved ? <p className="text-sm text-green-700">Saved</p> : null}
    </section>
  );
}
