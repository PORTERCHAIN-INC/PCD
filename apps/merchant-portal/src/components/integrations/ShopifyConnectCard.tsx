"use client";

import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import Button from "@/components/ui/Button";
import Link from "next/link";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { listSavedAddresses, type SavedAddress } from "@/lib/booking";
import { publicEnv } from "@/lib/env";
import { integrationsApi, type ShopifyConnection, type ShopifyGoLive } from "@/lib/integrations";
import { settingsApi } from "@/lib/settings";
import {
  SHOPIFY_SUPPORT_EMAIL,
  shopifyBlockingText,
  shopifyRatesProblem,
} from "@/lib/shopifyStatus";
import { useCallback, useEffect, useState } from "react";

function isWarehouse(addr: SavedAddress) {
  return addr.address_type === "pickup" || addr.address_type === "warehouse";
}

function setupStatus(goLive: ShopifyGoLive | undefined, pickup: string | null): string | null {
  if (!pickup) return null;
  if (goLive?.ready) return "Live. Checkout can use PorterChain.";
  return shopifyBlockingText(goLive?.blocking) ?? "PorterChain is finishing setup.";
}

export default function ShopifyConnectCard({
  initialShop = "",
  justConnected = false,
  ratesStatus = null,
}: {
  initialShop?: string;
  justConnected?: boolean;
  /** `rates` from the install redirect; the reason Shopify refused the carrier, if it did. */
  ratesStatus?: string | null;
}) {
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [data, setData] = useState<ShopifyConnection | null>(null);
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [shop, setShop] = useState(initialShop);
  const [token, setToken] = useState("");
  const [secret, setSecret] = useState("");
  const [pickupAddress, setPickupAddress] = useState<BookingAddress>({ formatted: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [carrierError, setCarrierError] = useState<string | null>(
    ratesStatus && ratesStatus !== "ready" ? ratesStatus : null
  );

  useEffect(() => {
    if (initialShop) setShop((current) => current || initialShop);
  }, [initialShop]);

  const load = useCallback(async () => {
    if (!isSignedIn || !orgId) return;
    const apiToken = await getApiToken();
    const [connection, saved] = await Promise.all([
      integrationsApi.shopify(apiToken, orgId, initialShop || undefined),
      listSavedAddresses(apiToken, orgId).catch(() => [] as SavedAddress[]),
    ]);
    setData(connection);
    setAddresses(saved);
  }, [getApiToken, initialShop, isSignedIn, orgId]);

  useEffect(() => {
    if (!isSignedIn || !orgId) return;
    void load().catch((e) => setError(e instanceof Error ? e.message : "Could not load Shopify"));
  }, [isSignedIn, orgId, load]);

  const warehouses = addresses.filter(isWarehouse);
  const defaultWarehouse = warehouses.find((row) => row.is_default) ?? warehouses[0];
  const shopDomain = (initialShop || shop).trim();
  const connectedShops = (data?.shops ?? []).filter((row) => row.connected);
  const connected = connectedShops.length > 0;
  const needsAddress = warehouses.length === 0;
  // The store from Shopify's "Open app" may already be held by another PorterChain account.
  const lookup = data?.shop_lookup ?? null;
  const linkedElsewhere = lookup?.status === "linked_elsewhere";
  const blockedElsewhere = linkedElsewhere && !lookup?.can_link;

  async function ensurePickupId(apiToken: string): Promise<string | undefined> {
    if (defaultWarehouse) return defaultWarehouse.id;
    const formatted = pickupAddress.formatted.trim();
    if (!formatted) return undefined;
    const created = await settingsApi.addPickup(
      apiToken,
      {
        label: "Warehouse",
        formatted,
        postal: pickupAddress.postal,
        lat: pickupAddress.lat,
        lng: pickupAddress.lng,
        place_id: pickupAddress.placeId,
        is_default: true,
      },
      orgId
    );
    return created.id;
  }

  async function startOAuth() {
    if (!shopDomain) return;
    setBusy(true);
    setError(null);
    try {
      const apiToken = await getApiToken();
      const pickupId = await ensurePickupId(apiToken);
      if (!pickupId) {
        setError("Add the pickup address.");
        setBusy(false);
        return;
      }
      const result = await integrationsApi.shopifyInstallUrl(apiToken, shopDomain, orgId, pickupId);
      window.location.assign(result.url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start Shopify install");
      setBusy(false);
    }
  }

  async function savePickup() {
    setBusy(true);
    setError(null);
    try {
      const apiToken = await getApiToken();
      const pickupId = await ensurePickupId(apiToken);
      if (!pickupId) {
        setError("Add the pickup address.");
        return;
      }
      setPickupAddress({ formatted: "" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the pickup address");
    } finally {
      setBusy(false);
    }
  }

  async function connectCustom() {
    if (!shopDomain || !token.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const apiToken = await getApiToken();
      const pickupId = await ensurePickupId(apiToken);
      if (!pickupId) {
        setError("Add the pickup address.");
        return;
      }
      await integrationsApi.shopifyConnect(
        apiToken,
        {
          shop_domain: shopDomain,
          admin_access_token: token,
          webhook_secret: secret || undefined,
          default_pickup_address_id: pickupId,
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

  async function retryRates(shopId: string) {
    setBusy(true);
    setError(null);
    try {
      const apiToken = await getApiToken();
      const result = await integrationsApi.shopifyGoLive(apiToken, { shop_id: shopId }, orgId);
      setData((current) => ({ ...result, shop_lookup: current?.shop_lookup ?? null }));
      setCarrierError(
        result.hooks?.carrier_registered
          ? null
          : (result.hooks?.carrier_error ?? "carrier_register_failed")
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not retry rate setup");
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

  const oneClick = Boolean(data?.oauth_configured ?? data?.go_live?.one_click_available);
  const shownPickup =
    connectedShops.find((row) => row.default_pickup)?.default_pickup ??
    defaultWarehouse?.formatted ??
    null;

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="text-lg font-semibold text-primary">Shopify</h2>
      <p className="mt-1 text-sm text-muted">
        Connect the store. Buyer name, email, phone, and street are kept only to deliver the order
        and to answer a privacy request. They are not used for marketing. PorterChain uses your
        pickup address for Shopify orders.{" "}
        <Link href="/settings?tab=privacy" className="underline">
          Privacy notice
        </Link>
      </p>
      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}

      {justConnected && connected && shownPickup ? (
        <p className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          Connected. Pickups use {shownPickup}.
        </p>
      ) : null}

      {connected ? (
        <ul className="mt-4 space-y-3">
          {connectedShops.map((row) => {
            const pickup = row.default_pickup ?? defaultWarehouse?.formatted ?? null;
            const status = setupStatus(data?.go_live, pickup);
            const ratesProblem = row.carrier_registered
              ? null
              : shopifyRatesProblem(carrierError ?? "carrier_register_failed");
            return (
              <li key={row.id} className="rounded-xl border border-primary/10 p-3 text-sm">
                <p className="font-medium text-primary">{row.shop_domain}</p>
                <p className="text-muted">
                  {pickup ? `Pickup: ${pickup}` : "Add a pickup address"}
                </p>
                {row.carrier_registered ? (
                  <p className="mt-1 text-emerald-800">
                    Checkout rates: PorterChain is registered as a carrier in Shopify.
                  </p>
                ) : (
                  <div className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-amber-900">
                    <p>{ratesProblem}</p>
                    <Button
                      size="sm"
                      variant="outline"
                      className="mt-2"
                      disabled={busy}
                      onClick={() => void retryRates(row.id)}
                    >
                      Retry rate setup
                    </Button>
                  </div>
                )}
                {status ? <p className="mt-1 text-muted">{status}</p> : null}
                {warehouses.length > 1 ? (
                  <label className="mt-2 block text-xs text-muted">
                    Pickup address
                    <select
                      className="mt-1 w-full rounded-lg border border-primary/15 px-2 py-1.5 text-sm"
                      value={row.default_pickup_address_id ?? defaultWarehouse?.id ?? ""}
                      onChange={(e) => void setPickup(row.id, e.target.value)}
                    >
                      {warehouses.map((addr) => (
                        <option key={addr.id} value={addr.id}>
                          {addr.label} — {addr.formatted}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
                <button
                  type="button"
                  className="mt-2 text-xs text-muted underline"
                  onClick={() => void disconnect(row.id)}
                >
                  Disconnect
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}

      {connected && needsAddress ? (
        <div className="mt-4 space-y-2">
          <AddressAutocompleteInput
            id="shopify-pickup"
            value={pickupAddress.formatted}
            onChange={(formatted) => setPickupAddress({ ...pickupAddress, formatted })}
            onPlaceSelect={setPickupAddress}
            apiKey={publicEnv.googleMapsApiKey}
            placeholder="Pickup address"
            fallbackClassName="w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
          />
          <Button
            size="sm"
            disabled={busy || !pickupAddress.formatted.trim()}
            onClick={() => void savePickup()}
          >
            Save pickup address
          </Button>
        </div>
      ) : null}

      {initialShop && blockedElsewhere ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <p className="font-medium">{initialShop} is linked to a different PorterChain account.</p>
          <p className="mt-1">
            Sign in with the account that installed PorterChain Delivery on this store, or email{" "}
            <a className="underline" href={`mailto:${SHOPIFY_SUPPORT_EMAIL}`}>
              {SHOPIFY_SUPPORT_EMAIL}
            </a>{" "}
            and we will move it to this account.
          </p>
        </div>
      ) : null}

      {initialShop && linkedElsewhere && !blockedElsewhere && !connected ? (
        <p className="mt-4 rounded-xl bg-primary/5 px-3 py-2 text-sm text-primary">
          PorterChain Delivery is installed on {initialShop} but not linked to this account yet.
          Connect links it here; Shopify will confirm you manage the store.
        </p>
      ) : null}

      {!connected && !blockedElsewhere ? (
        <div className="mt-4 space-y-3">
          {initialShop ? (
            <p className="text-sm text-primary">
              Store <span className="font-medium">{initialShop}</span>
            </p>
          ) : (
            <label className="block text-sm">
              Store
              <input
                className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
                placeholder="store.myshopify.com"
                value={shop}
                onChange={(e) => setShop(e.target.value)}
              />
            </label>
          )}
          {needsAddress ? (
            <AddressAutocompleteInput
              id="shopify-pickup-connect"
              value={pickupAddress.formatted}
              onChange={(formatted) => setPickupAddress({ ...pickupAddress, formatted })}
              onPlaceSelect={setPickupAddress}
              apiKey={publicEnv.googleMapsApiKey}
              placeholder="Pickup address"
              fallbackClassName="w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
            />
          ) : (
            <p className="text-sm text-muted">Pickup: {defaultWarehouse?.formatted}</p>
          )}
          {oneClick ? (
            <Button
              size="sm"
              disabled={busy || !shopDomain || (needsAddress && !pickupAddress.formatted.trim())}
              onClick={() => void startOAuth()}
            >
              Connect
            </Button>
          ) : (
            <p className="text-sm text-amber-800">
              One-click connect is offline until Shopify partner credentials are on the API.
            </p>
          )}
          <button
            type="button"
            className="block text-sm text-secondary underline"
            onClick={() => setShowAdvanced((v) => !v)}
          >
            {showAdvanced ? "Hide custom app" : "Use custom Admin API token instead"}
          </button>
          {showAdvanced ? (
            <div className="space-y-3 rounded-xl border border-primary/10 bg-gray-bg/40 p-3">
              <label className="block text-sm">
                Admin API token
                <input
                  className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="shpat_…"
                />
              </label>
              <label className="block text-sm">
                Webhook secret
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
                disabled={
                  busy ||
                  !shopDomain ||
                  !token.trim() ||
                  (needsAddress && !pickupAddress.formatted.trim())
                }
                onClick={() => void connectCustom()}
              >
                Connect custom app
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
