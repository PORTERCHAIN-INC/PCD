"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { listSavedAddresses, type SavedAddress } from "@/lib/booking";
import { integrationsApi, type ShopifyConnection } from "@/lib/integrations";
import { useCallback, useEffect, useState } from "react";

export default function ShopifyConnectCard({ initialShop = "" }: { initialShop?: string }) {
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [data, setData] = useState<ShopifyConnection | null>(null);
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [shop, setShop] = useState(initialShop);
  const [token, setToken] = useState("");
  const [secret, setSecret] = useState("");
  const [pickupId, setPickupId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (initialShop) setShop((current) => current || initialShop);
  }, [initialShop]);

  const load = useCallback(async () => {
    if (!isSignedIn || !orgId) return;
    const apiToken = await getApiToken();
    const [connection, saved] = await Promise.all([
      integrationsApi.shopify(apiToken, orgId),
      listSavedAddresses(apiToken, orgId).catch(() => [] as SavedAddress[]),
    ]);
    setData(connection);
    setAddresses(saved);
    const defaultPickup = saved.find((row) => row.is_default) ?? saved[0];
    if (defaultPickup) setPickupId((current) => current || defaultPickup.id);
  }, [getApiToken, isSignedIn, orgId]);

  useEffect(() => {
    if (!isSignedIn || !orgId) return;
    void load().catch((e) => setError(e instanceof Error ? e.message : "Could not load Shopify"));
  }, [isSignedIn, orgId, load]);

  async function connectCustom() {
    setBusy(true);
    setError(null);
    try {
      const apiToken = await getApiToken();
      await integrationsApi.shopifyConnect(
        apiToken,
        {
          shop_domain: shop,
          admin_access_token: token,
          webhook_secret: secret || undefined,
          default_pickup_address_id: pickupId || undefined,
        },
        orgId
      );
      setToken("");
      setSecret("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not connect that shop");
    } finally {
      setBusy(false);
    }
  }

  async function startOAuth() {
    setBusy(true);
    setError(null);
    try {
      const apiToken = await getApiToken();
      const result = await integrationsApi.shopifyInstallUrl(apiToken, shop, orgId);
      window.location.href = result.url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start Shopify install");
      setBusy(false);
    }
  }

  async function setPickup(shopId: string, addressId: string) {
    const apiToken = await getApiToken();
    await integrationsApi.shopifySetPickup(apiToken, shopId, addressId, orgId);
    await load();
  }

  async function disconnect(shopId: string) {
    if (!window.confirm("Disconnect this Shopify store?")) return;
    const apiToken = await getApiToken();
    await integrationsApi.shopifyDisconnect(apiToken, shopId, orgId);
    await load();
  }

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="text-lg font-semibold text-primary">Shopify</h2>
      <p className="mt-1 text-sm text-muted">
        Shopify orders become bookings from your default pickup. That is the only store connector we
        sell today. Webhook URL:{" "}
        <code className="break-all text-xs">{data?.webhook_url ?? "…"}</code>
        {data?.webhook_url ? (
          <button
            type="button"
            className="ml-2 text-xs text-secondary underline"
            onClick={() => {
              void navigator.clipboard.writeText(data.webhook_url).then(() => {
                setCopied(true);
                window.setTimeout(() => setCopied(false), 2000);
              });
            }}
          >
            {copied ? "Copied" : "Copy"}
          </button>
        ) : null}
      </p>
      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}

      {data?.shops.length ? (
        <ul className="mt-4 space-y-3">
          {data.shops.map((row) => (
            <li key={row.id} className="rounded-xl border border-primary/10 p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-primary">{row.shop_domain}</p>
                  <p className="text-muted">
                    {row.connected ? "Connected" : "Disconnected"}
                    {row.default_pickup
                      ? ` · pickup ${row.default_pickup}`
                      : " · no default pickup"}
                  </p>
                </div>
                {row.connected ? (
                  <Button size="sm" variant="outline" onClick={() => void disconnect(row.id)}>
                    Disconnect
                  </Button>
                ) : null}
              </div>
              {addresses.length > 0 && row.connected ? (
                <label className="mt-2 block text-xs text-muted">
                  Default pickup
                  <select
                    className="mt-1 w-full rounded-lg border border-primary/15 px-2 py-1.5 text-sm"
                    value={row.default_pickup_address_id ?? ""}
                    onChange={(e) => void setPickup(row.id, e.target.value)}
                  >
                    <option value="">Select…</option>
                    {addresses.map((addr) => (
                      <option key={addr.id} value={addr.id}>
                        {addr.label} — {addr.formatted}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-muted">No shop connected yet.</p>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          Shop domain
          <input
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
            placeholder="store.myshopify.com"
            value={shop}
            onChange={(e) => setShop(e.target.value)}
          />
        </label>
        <label className="text-sm">
          Default pickup
          <select
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
            value={pickupId}
            onChange={(e) => setPickupId(e.target.value)}
          >
            <option value="">Select a saved warehouse…</option>
            {addresses.map((addr) => (
              <option key={addr.id} value={addr.id}>
                {addr.label} — {addr.formatted}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm sm:col-span-2">
          Admin API token (custom app)
          <input
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="shpat_…"
          />
        </label>
        <label className="text-sm sm:col-span-2">
          Webhook secret (optional if the platform Shopify secret is set)
          <input
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
          />
        </label>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          size="sm"
          disabled={busy || !shop || !token || !pickupId}
          onClick={() => void connectCustom()}
        >
          Connect custom app
        </Button>
        {data?.oauth_configured ? (
          <Button
            size="sm"
            variant="outline"
            disabled={busy || !shop}
            onClick={() => void startOAuth()}
          >
            Install via Shopify OAuth
          </Button>
        ) : null}
      </div>
      {addresses.length === 0 ? (
        <p className="mt-3 text-sm text-amber-800">
          Add a default pickup under Settings → Locations before Shopify can book.
        </p>
      ) : null}
    </section>
  );
}
