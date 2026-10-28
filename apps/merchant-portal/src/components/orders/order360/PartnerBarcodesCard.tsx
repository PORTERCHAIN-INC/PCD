"use client";

import Button from "@/components/ui/Button";
import { ordersApi } from "@/lib/orders";
import { barcodesFor, custodyStatusLabel, SOURCE_LABEL } from "@/lib/partnerBarcodes";
import {
  EXTERNAL_ID_SOURCES,
  type ExternalIdSource,
  type PackageExternalIdsResponse,
} from "@porterchain/types";
import { useCallback, useEffect, useState } from "react";

type Props = {
  orderId: string;
  canWrite: boolean;
  getApiToken?: () => Promise<string>;
  orgId?: string;
};

/** Barcodes already on the boxes (Shopify, marketplace...) so drivers can scan them instead of relabelling. */
export function PartnerBarcodesCard({ orderId, canWrite, getApiToken, orgId }: Props) {
  const [data, setData] = useState<PackageExternalIdsResponse | null>(null);
  const [pkgId, setPkgId] = useState("");
  const [source, setSource] = useState<ExternalIdSource>("merchant");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getApiToken) return;
    const out = await ordersApi.externalIds(await getApiToken(), orderId, orgId);
    setData(out);
    setPkgId((cur) => cur || out.packages[0]?.id || "");
  }, [getApiToken, orderId, orgId]);

  useEffect(() => {
    void load().catch(() => setData(null));
  }, [load]);

  if (!data || data.packages.length === 0) return null;

  async function add() {
    if (!getApiToken || !pkgId || !value.trim()) return;
    setBusy(true);
    setNote(null);
    try {
      await ordersApi.addExternalId(
        await getApiToken(),
        orderId,
        { package_id: pkgId, source, value: value.trim() },
        orgId
      );
      setValue("");
      await load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not add this barcode.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!getApiToken) return;
    setBusy(true);
    try {
      await ordersApi.removeExternalId(await getApiToken(), orderId, id, orgId);
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-primary/10 p-4">
      <h3 className="font-semibold text-primary">Boxes and partner barcodes</h3>
      <ul className="mt-2 space-y-2 text-sm">
        {data.packages.map((p) => (
          <li key={p.id}>
            <span className="font-medium">
              Box {p.parcel_index}/{p.total_parcels}
            </span>{" "}
            · {p.tracking_suffix} · {custodyStatusLabel(p.status)}
            {barcodesFor(data, p.id).map((i) => (
              <span key={i.id} className="ml-2 inline-flex items-center gap-1 text-muted">
                {SOURCE_LABEL[i.source] ?? i.source}: {i.value}
                {canWrite ? (
                  <button
                    type="button"
                    className="text-secondary hover:underline"
                    onClick={() => void remove(i.id)}
                    disabled={busy}
                    aria-label={`Remove ${i.value}`}
                  >
                    ×
                  </button>
                ) : null}
              </span>
            ))}
          </li>
        ))}
      </ul>
      {canWrite ? (
        <div className="mt-3 flex flex-wrap items-end gap-2 text-sm">
          <select
            aria-label="Box"
            value={pkgId}
            onChange={(e) => setPkgId(e.target.value)}
            className="rounded border px-2 py-1"
          >
            {data.packages.map((p) => (
              <option key={p.id} value={p.id}>
                Box {p.parcel_index}
              </option>
            ))}
          </select>
          <select
            aria-label="Barcode source"
            value={source}
            onChange={(e) => setSource(e.target.value as ExternalIdSource)}
            className="rounded border px-2 py-1"
          >
            {EXTERNAL_ID_SOURCES.map((s) => (
              <option key={s} value={s}>
                {SOURCE_LABEL[s]}
              </option>
            ))}
          </select>
          <input
            aria-label="Barcode"
            value={value}
            maxLength={128}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Barcode on the box"
            className="rounded border px-2 py-1"
          />
          <Button
            size="sm"
            variant="outline"
            onClick={() => void add()}
            disabled={busy || !value.trim()}
          >
            Add barcode
          </Button>
        </div>
      ) : null}
      {note ? <p className="mt-2 text-sm text-red-600">{note}</p> : null}
    </section>
  );
}
