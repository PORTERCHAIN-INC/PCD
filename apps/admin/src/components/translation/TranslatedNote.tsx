"use client";

import { useEffect, useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { adminFetch } from "@/lib/api";

export type TranslationItem = {
  field: string;
  original: string;
  source_lang: string | null;
  source_language: string | null;
  translated_en: string | null;
  status: "pending" | "translated" | "same" | "failed";
  label: string | null;
};

/**
 * Shows the English translation of merchant/customer free text under the original.
 * Admin is English only; originals are never replaced.
 */
export function TranslatedNote({
  entityType,
  entityId,
  field,
}: {
  entityType: "order" | "booking" | "claim" | "support_ticket";
  entityId: string | null | undefined;
  field: string;
}) {
  const { getApiToken } = useAdminAuth();
  const [item, setItem] = useState<TranslationItem | null>(null);
  useEffect(() => {
    if (!entityId) return;
    let live = true;
    void (async () => {
      try {
        const t = await getApiToken();
        const res = await adminFetch<{ items: TranslationItem[] }>(
          `/v1/admin/translations?entity_type=${entityType}&entity_id=${encodeURIComponent(entityId)}`,
          t
        );
        if (live) setItem(res.items.find((i) => i.field === field) ?? null);
      } catch {
        /* translation is a convenience; never block the page */
      }
    })();
    return () => {
      live = false;
    };
  }, [entityType, entityId, field, getApiToken]);

  if (!item) return null;
  if (item.status === "translated" && item.translated_en) {
    return (
      <div
        className="mb-2 rounded-lg bg-gray-bg/60 px-3 py-2 text-sm"
        data-testid="translated-note"
      >
        <p className="text-xs font-medium text-muted">{item.label ?? "Translated"}</p>
        <p className="text-primary">{item.translated_en}</p>
      </div>
    );
  }
  if (item.status === "pending") {
    return <p className="mb-2 text-xs text-muted">Translation pending…</p>;
  }
  return null;
}

const NOTE_LABELS: Record<string, string> = {
  notes: "notes",
  instructions: "instructions",
  access_notes: "access notes",
  delivery_instructions: "delivery instructions",
  buzzer_notes: "buzzer",
  site_access_notes: "site access",
};

/** L71: every pickup/dropoff note typed by the merchant or customer, original first, English under it. */
export function AddressNoteTranslations({ entityId }: { entityId: string | null | undefined }) {
  const { getApiToken } = useAdminAuth();
  const [items, setItems] = useState<TranslationItem[]>([]);
  useEffect(() => {
    if (!entityId) return;
    let live = true;
    void (async () => {
      try {
        const t = await getApiToken();
        const res = await adminFetch<{ items: TranslationItem[] }>(
          `/v1/admin/translations?entity_type=order&entity_id=${encodeURIComponent(entityId)}`,
          t
        );
        if (live)
          setItems(res.items.filter((i) => /^(pickup|dropoff)\./.test(i.field) && i.original));
      } catch {
        /* convenience only */
      }
    })();
    return () => {
      live = false;
    };
  }, [entityId, getApiToken]);
  if (!items.length) return null;
  return (
    <div className="mt-2 space-y-2" data-testid="address-note-translations">
      {items.map((i) => {
        const [side, key] = i.field.split(".");
        const label = `${side === "pickup" ? "Pickup" : "Dropoff"} ${NOTE_LABELS[key] ?? key.replace(/_/g, " ")}`;
        return (
          <div key={i.field} className="rounded-lg bg-gray-bg/60 px-3 py-2 text-sm">
            <p className="text-xs font-medium text-muted">{label}</p>
            <p className="text-primary">{i.original}</p>
            {i.status === "translated" && i.translated_en ? (
              <p className="mt-1 text-primary">
                <span className="text-xs font-medium text-muted">{i.label ?? "Translated"}: </span>
                {i.translated_en}
              </p>
            ) : i.status === "pending" ? (
              <p className="mt-1 text-xs text-muted">Translation pending…</p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
