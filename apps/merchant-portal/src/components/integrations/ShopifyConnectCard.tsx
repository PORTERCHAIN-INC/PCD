"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { listSavedAddresses, type SavedAddress } from "@/lib/booking";
import { integrationsApi, type ShopifyConnection } from "@/lib/integrations";
import { useCallback, useEffect, useState } from "react";

const BLOCKING_COPY: Record<string, string> = {
  oauth_not_configured: "Shopify partner app credentials are not live on the API yet.",
  shop_not_connected: "Connect your store with one click below.",
  pickup_required: "Choose a default pickup warehouse.",
  merchant_not_active: "Account is not active yet — PorterChain ops must finish activation.",
  rate_card_required: "Rate card is not on this account yet — PorterChain ops must apply pricing.",
};

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
  const [showAdvanced, setShowAdvanced] = useState(false);

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
      const result = await integrationsApi.shopifyInstallUrl(
        apiToken,
        shop,
        orgId,
        pickupId || undefined
      );
      window.location.href = result.url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start Shopify install");
      setBusy(false);
    }
  }

  async function finishGoLive(shopId?: string) {
    setBusy(true);
    setError(null);
    try {
      const apiToken = await getApiToken();
      const next = await integrationsApi.shopifyGoLive(
        apiToken,
        { shop_id: shopId, pickup_address_id: pickupId || undefined },
        orgId
      );
      setData(next);
      if (next.go_live && !next.go_live.ready) {
        const msgs = next.go_live.blocking.map((b) => BLOCKING_COPY[b] ?? b);
        setError(msgs.join(" "));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not finish Shopify go-live");
    } finally {
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

  const goLive = data?.go_live;
  const oneClick = Boolean(data?.oauth_configured ?? goLive?.one_click_available);
  const needsFinish =
    Boolean(goLive) &&
    !goLive?.ready &&
    Boolean(goLive?.checks.shop_connected) &&
    Boolean(goLive?.blocking.includes("pickup_required") || goLive?.checks.pickup_set === false);

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="text-lg font-semibold text-primary">Shopify</h2>
      <p className="mt-1 text-sm text-muted">
        One click installs PorterChain rates and order sync on your Shopify store. Pickup must be
        set so checkout can price capacity.
      </p>
      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}

      {goLive ? (
        <div
          className={`mt-3 rounded-xl px-3 py-2 text-sm ${
            goLive.ready
              ? "bg-emerald-50 text-emerald-900"
              : "border border-amber-200 bg-amber-50 text-amber-950"
          }`}
        >
          {goLive.ready
            ? "Live — Shopify checkout can return PorterChain rates when pickup and rates are set."
            : `Almost there: ${goLive.blocking.map((b) => BLOCKING_COPY[b] ?? b).join(" ")}`}
        </div>
      ) : null}

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
                <div className="flex flex-wrap gap-2">
                  {row.connected && needsFinish ? (
                    <Button
                      size="sm"
                      disabled={busy || (!pickupId && !row.default_pickup_address_id)}
                      onClick={() => void finishGoLive(row.id)}
                    >
                      Finish go-live
                    </Button>
                  ) : null}
                  {row.connected ? (
                    <Button size="sm" variant="outline" onClick={() => void disconnect(row.id)}>
                      Disconnect
                    </Button>
                  ) : null}
                </div>
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
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {oneClick ? (
          <Button size="sm" disabled={busy || !shop} onClick={() => void startOAuth()}>
            Connect with one click
          </Button>
        ) : (
          <p className="text-sm text-amber-800">
            One-click OAuth is offline until Shopify partner credentials are on the API.
          </p>
        )}
        <button
          type="button"
          className="text-sm text-secondary underline"
          onClick={() => setShowAdvanced((v) => !v)}
        >
          {showAdvanced ? "Hide custom app" : "Use custom Admin API token instead"}
        </button>
      </div>

      {showAdvanced ? (
        <div className="mt-3 space-y-3 rounded-xl border border-primary/10 bg-gray-bg/40 p-3">
          <label className="block text-sm">
            Admin API token (custom app)
            <input
              className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="shpat_…"
            />
          </label>
          <label className="block text-sm">
            Webhook secret (optional if the platform Shopify secret is set)
            <input
              className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
            />
          </label>
          <Button
            size="sm"
            variant="outline"
            disabled={busy || !shop || !token || !pickupId}
            onClick={() => void connectCustom()}
          >
            Connect custom app
          </Button>
        </div>
      ) : null}

      <p className="mt-3 text-xs text-muted">
        Webhook URL: <code className="break-all">{data?.webhook_url ?? "…"}</code>
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
      {addresses.length === 0 ? (
        <p className="mt-3 text-sm text-amber-800">
          Add a default pickup under Settings → Locations, then use one-click connect (pickup binds
          automatically).
        </p>
      ) : null}
    </section>
  );
}
