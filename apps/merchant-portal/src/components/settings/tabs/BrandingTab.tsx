"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import { settingsApi, type BrandingPrefs } from "@/lib/settings";
import { Field } from "./Field";

export function BrandingTab({
  branding,
  onRefresh,
  getToken,
  orgId,
  onSaved,
}: {
  branding: BrandingPrefs;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
  onSaved?: () => void;
}) {
  const [form, setForm] = useState(branding);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setError(null);
    try {
      const token = await getToken();
      await settingsApi.updateBranding(token, form, orgId);
      await onRefresh();
      onSaved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save branding.");
    }
  };

  return (
    <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Branding</h2>
      <p className="text-sm text-muted">
        This logo appears in the portal header and on the public track page consignees open.
      </p>
      {form.logo_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={form.logo_url}
          alt="Logo preview"
          referrerPolicy="no-referrer"
          className="h-12 w-12 rounded-lg object-cover"
        />
      ) : null}
      <Field
        label="Logo URL"
        value={form.logo_url || ""}
        onChange={(v) => setForm({ ...form, logo_url: v })}
      />
      <Field
        label="Primary color"
        value={form.primary_color}
        onChange={(v) => setForm({ ...form, primary_color: v })}
      />
      <Field
        label="Accent color"
        value={form.accent_color}
        onChange={(v) => setForm({ ...form, accent_color: v })}
      />
      <Field
        label="Tracking page message"
        value={form.tracking_page_message || ""}
        onChange={(v) => setForm({ ...form, tracking_page_message: v })}
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <Button size="sm" onClick={() => void save()}>
        Save branding
      </Button>
    </section>
  );
}
