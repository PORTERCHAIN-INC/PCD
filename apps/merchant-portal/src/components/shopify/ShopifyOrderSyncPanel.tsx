"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  AddressDisambiguationModal,
  type AddressCandidate,
  type BookingAddress,
} from "@porterchain/maps";
import {
  bookShopifyOrderSync,
  getShopifySyncAddressCandidates,
  listShopifyOrderSyncs,
  refreshShopifyOrderSyncs,
  type ShopifyOrderSyncRow,
} from "@/lib/api";
import { formatCents } from "@/lib/utils";

const STATUS_LABEL: Record<ShopifyOrderSyncRow["status"], string> = {
  booked: "Booked",
  not_booked: "Not booked",
  cancelled: "Cancelled",
  error: "Needs attention",
};

const STATUS_CLASS: Record<ShopifyOrderSyncRow["status"], string> = {
  booked: "bg-emerald-50 text-emerald-800 border-emerald-200",
  not_booked: "bg-amber-50 text-amber-900 border-amber-200",
  cancelled: "bg-gray-100 text-gray-700 border-gray-200",
  error: "bg-red-50 text-red-800 border-red-200",
};

/** Every Shopify order we received, searchable by its Shopify number (e.g. #1374). */
export function ShopifyOrderSyncPanel({
  search,
  hideWhenEmpty = false,
}: {
  search?: string;
  hideWhenEmpty?: boolean;
}) {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const qc = useQueryClient();
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [review, setReview] = useState<{
    row: ShopifyOrderSyncRow;
    original: string;
    candidates: AddressCandidate[];
    error: string | null;
  } | null>(null);
  const enabled = Boolean(isLoaded && isSignedIn && orgId);
  const key = ["merchant-shopify-syncs", orgId ?? null, search ?? ""];
  const query = useQuery({
    queryKey: key,
    enabled,
    queryFn: async () => listShopifyOrderSyncs(await getApiToken(), orgId, search),
  });
  const rows = query.data ?? [];
  const heldCount = rows.filter((r) => r.needs_address_review).length;
  if (hideWhenEmpty && !search && !query.isLoading && rows.length === 0) return null;

  async function syncNow() {
    setBusy("sync");
    setNote(null);
    try {
      const r = await refreshShopifyOrderSyncs(await getApiToken(), orgId);
      setNote(`Checked Shopify: ${r.found ?? 0} recent order(s), ${r.new ?? 0} new.`);
      await qc.invalidateQueries({ queryKey: ["merchant-shopify-syncs"] });
      await qc.invalidateQueries({ queryKey: ["merchant-orders"] });
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not reach Shopify. Try again.");
    } finally {
      setBusy(null);
    }
  }

  async function openReview(row: ShopifyOrderSyncRow) {
    setBusy(row.id);
    setNote(null);
    try {
      const r = await getShopifySyncAddressCandidates(await getApiToken(), row.id, orgId);
      setReview({ row, original: r.original_address, candidates: r.candidates ?? [], error: null });
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not load address suggestions.");
    } finally {
      setBusy(null);
    }
  }

  async function bookReviewed(lat: number, lng: number) {
    if (!review) return;
    const row = review.row;
    const ok = await book(row, { lat, lng });
    if (ok) setReview(null);
  }

  function pickUpdated(_address: string, place: BookingAddress | null) {
    if (!review) return;
    if (place?.lat == null || place?.lng == null) {
      setReview({ ...review, error: "Pick a suggestion from the list so we can pin the address." });
      return;
    }
    void bookReviewed(place.lat, place.lng);
  }

  async function book(
    row: ShopifyOrderSyncRow,
    point?: { lat: number; lng: number }
  ): Promise<boolean> {
    if (row.needs_address_review && !point) {
      await openReview(row);
      return false;
    }
    setBusy(row.id);
    setNote(null);
    try {
      const r = await bookShopifyOrderSync(await getApiToken(), row.id, orgId, point);
      setNote(
        r.order_id
          ? `${row.order_name ?? "Order"} booked${r.tracking_number ? ` (${r.tracking_number})` : ""}.`
          : `${row.order_name ?? "Order"} was not booked. The reason is shown next to the order.`
      );
      await qc.invalidateQueries({ queryKey: ["merchant-shopify-syncs"] });
      await qc.invalidateQueries({ queryKey: ["merchant-orders"] });
      return Boolean(r.order_id);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not book this order.";
      if (point && review) setReview({ ...review, error: msg });
      else setNote(msg);
      return false;
    } finally {
      setBusy(null);
    }
  }

  return (
    <section
      aria-labelledby="shopify-syncs-title"
      className="rounded-2xl border border-primary/10 bg-white p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="shopify-syncs-title" className="font-semibold text-primary">
            Shopify orders
          </h2>
          <p className="text-sm text-muted">
            Every paid order from your store shows here, even when the customer picked another
            shipping rate. Search by the Shopify number, e.g. #1001.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void syncNow()}
          disabled={busy !== null}
          className="rounded-xl border border-primary/20 px-3 py-2 text-sm font-medium text-primary disabled:opacity-50"
        >
          {busy === "sync" ? "Syncing…" : "Sync now"}
        </button>
      </div>
      {heldCount > 0 ? (
        <p
          role="alert"
          className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
        >
          {heldCount} Shopify order{heldCount === 1 ? "" : "s"} on hold: we couldn&apos;t
          confidently place the delivery address. Use &ldquo;Fix address&rdquo; to pick the right
          one and book.
        </p>
      ) : null}
      {note ? (
        <p role="status" className="mt-3 rounded-xl bg-gray-bg px-3 py-2 text-sm">
          {note}
        </p>
      ) : null}
      {query.isLoading ? (
        <p className="mt-3 text-sm text-muted">Loading Shopify orders…</p>
      ) : rows.length === 0 ? (
        <p className="mt-3 text-sm text-muted">
          {search ? `No Shopify order matches “${search}”.` : "No Shopify orders yet."}
        </p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-primary/10 text-muted">
                <th className="px-2 py-2">Order</th>
                <th className="px-2 py-2">Customer / ship to</th>
                <th className="px-2 py-2">Items</th>
                <th className="px-2 py-2">Total</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">
                  <span className="sr-only">Action</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-primary/5 align-top">
                  <td className="px-2 py-2 font-medium text-primary">
                    {row.order_name ?? row.shopify_order_id}
                    {row.is_test ? (
                      <span className="ml-1 rounded bg-amber-100 px-1 text-xs text-amber-900">
                        Test
                      </span>
                    ) : null}
                    <div className="text-xs text-muted">{row.shipping_title ?? ""}</div>
                  </td>
                  <td className="px-2 py-2">
                    {row.customer_name ?? "—"}
                    <div className="text-xs text-muted">{row.ship_to ?? ""}</div>
                  </td>
                  <td className="px-2 py-2">
                    {row.line_items
                      .slice(0, 3)
                      .map((li) => `${li.quantity ?? 1} × ${li.title ?? "item"}`)
                      .join(", ") || "—"}
                    {row.line_items.length > 3 ? ` +${row.line_items.length - 3} more` : ""}
                  </td>
                  <td className="px-2 py-2">
                    {row.total_cents != null
                      ? formatCents(row.total_cents, (row.currency ?? "CAD").toUpperCase())
                      : "—"}
                  </td>
                  <td className="px-2 py-2">
                    <span
                      className={`rounded-full border px-2 py-0.5 text-xs ${STATUS_CLASS[row.status]}`}
                    >
                      {STATUS_LABEL[row.status]}
                    </span>
                    {row.status !== "booked" && row.reason ? (
                      <div className="mt-1 text-xs text-muted">{row.reason}</div>
                    ) : null}
                  </td>
                  <td className="px-2 py-2 text-right">
                    {row.porterchain_order_id ? (
                      <Link
                        className="text-primary underline"
                        href={`/orders/${row.porterchain_order_id}`}
                      >
                        Open
                      </Link>
                    ) : row.can_book ? (
                      <button
                        type="button"
                        onClick={() => void book(row)}
                        disabled={busy !== null}
                        className="rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                      >
                        {busy === row.id
                          ? "Working…"
                          : row.needs_address_review
                            ? "Fix address"
                            : "Book with PorterChain"}
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <AddressDisambiguationModal
        open={review !== null}
        originalAddress={review?.original ?? ""}
        candidates={review?.candidates ?? []}
        contextLabel={
          review ? `Shopify ${review.row.order_name ?? review.row.shopify_order_id}` : undefined
        }
        busy={review !== null && busy === review.row.id}
        error={review?.error ?? null}
        onPickCandidate={(_i, c) => void bookReviewed(c.lat, c.lng)}
        onUpdateAddress={pickUpdated}
        onClose={() => setReview(null)}
      />
    </section>
  );
}
