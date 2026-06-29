"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { cancelOrder, duplicateOrder, listOrders, type MerchantOrder } from "@/lib/api";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function OrdersPage() {
  const { getApiToken, orgId, isSignedIn, isLoaded } = useMerchantAuth();
  const [orders, setOrders] = useState<MerchantOrder[]>([]);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!isSignedIn) return;
    const token = await getApiToken();
    const data = await listOrders(token, orgId, {
      search: search || undefined,
      state: stateFilter || undefined,
    });
    setOrders(data);
  }

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch orders on mount
    void load().catch((e) => setError(e instanceof Error ? e.message : "Failed to load orders"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn, orgId]);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    try {
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    }
  }

  async function onCancel(orderId: string) {
    const token = await getApiToken();
    await cancelOrder(token, orderId, orgId);
    await load();
  }

  async function onDuplicate(orderId: string) {
    const token = await getApiToken();
    await duplicateOrder(token, orderId, orgId);
    await load();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Orders</h1>

      <form onSubmit={onSearch} className="flex flex-wrap gap-3">
        <input
          className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
          placeholder="Search tracking, PO, reference…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
        >
          <option value="">All states</option>
          <option value="BOOKED">Booked</option>
          <option value="DISPATCH_READY">Dispatch ready</option>
          <option value="IN_TRANSIT">In transit</option>
          <option value="DELIVERED">Delivered</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
        <Button type="submit" size="sm">
          Search
        </Button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-primary/10 bg-gray-bg/50">
            <tr>
              <th className="px-4 py-3 font-medium">Tracking</th>
              <th className="px-4 py-3 font-medium">State</th>
              <th className="px-4 py-3 font-medium">Route</th>
              <th className="px-4 py-3 font-medium">Amount</th>
              <th className="px-4 py-3 font-medium">Scheduled</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.order_id} className="border-b border-primary/5">
                <td className="px-4 py-3 font-mono text-xs">
                  <Link href={`/orders/${o.order_id}`} className="text-secondary hover:underline">
                    {o.tracking_number}
                  </Link>
                </td>
                <td className="px-4 py-3">{o.state}</td>
                <td className="max-w-xs truncate px-4 py-3 text-muted">
                  {o.pickup?.formatted} → {o.dropoff?.formatted}
                </td>
                <td className="px-4 py-3">
                  {formatCents(o.amount_cents, o.currency.toUpperCase())}
                </td>
                <td className="px-4 py-3">{formatDate(o.scheduled_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="text-xs text-secondary"
                      onClick={() => onDuplicate(o.order_id)}
                    >
                      Duplicate
                    </button>
                    {o.state !== "CANCELLED" && (
                      <button
                        type="button"
                        className="text-xs text-red-600"
                        onClick={() => onCancel(o.order_id)}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {orders.length === 0 && (
          <p className="p-6 text-center text-sm text-muted">No orders found</p>
        )}
      </div>
    </div>
  );
}
