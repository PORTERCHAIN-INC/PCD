"use client";

import ShopifyConnectCard from "@/components/integrations/ShopifyConnectCard";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { publicEnv } from "@/lib/env";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

function normalizeShop(raw: string | null): string {
  if (!raw) return "";
  let value = raw.trim().toLowerCase();
  value = value.replace(/^https?:\/\//, "").split("/", 1)[0] ?? "";
  if (value && !value.includes(".")) {
    value = `${value}.myshopify.com`;
  }
  return value;
}

export default function ShopifyAppClient() {
  const { isLoaded, isSignedIn } = useMerchantAuth();
  const searchParams = useSearchParams();
  const shop = normalizeShop(searchParams.get("shop") ?? searchParams.get("shopify"));
  const justConnected = searchParams.get("connected") === "1";
  const publicInstallUrl = shop
    ? `${publicEnv.porterchainApiUrl}/v1/integrations/shopify/install?shop=${encodeURIComponent(shop)}`
    : null;

  if (!isLoaded) {
    return <p className="text-muted">Loading…</p>;
  }

  // After OAuth grant — show app UI immediately (App Store requirement 2.3.3).
  if (justConnected && !isSignedIn) {
    return (
      <div className="mx-auto max-w-xl space-y-4 py-8">
        <h1 className="text-2xl font-semibold text-primary">PorterChain for Shopify</h1>
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {shop
            ? `${shop} is connected. Checkout can request PorterChain delivery rates.`
            : "Your Shopify store is connected. Checkout can request PorterChain delivery rates."}
        </p>
        <p className="text-sm text-muted">
          Sign in to the merchant portal to manage pickup, rate readiness, and order sync.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link
            href={
              shop
                ? `/sign-in?redirect_url=${encodeURIComponent(`/shopify?shop=${encodeURIComponent(shop)}`)}`
                : "/sign-in?redirect_url=/shopify"
            }
            className="inline-flex items-center rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white"
          >
            Open merchant portal
          </Link>
        </div>
      </div>
    );
  }

  if (!isSignedIn) {
    const signInHref = shop
      ? `/sign-in?redirect_url=${encodeURIComponent(`/shopify?shop=${encodeURIComponent(shop)}`)}`
      : "/sign-in?redirect_url=/shopify";
    return (
      <div className="mx-auto max-w-xl space-y-4 py-8">
        <h1 className="text-2xl font-semibold text-primary">PorterChain for Shopify</h1>
        <p className="text-sm text-muted">
          One-click install connects Shopify rates and order sync
          {shop ? ` for ${shop}` : ""}. Sign in to finish if you are not already in the merchant
          portal.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link
            href={signInHref}
            className="inline-flex items-center rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white"
          >
            Sign in to merchant portal
          </Link>
          {publicInstallUrl ? (
            <a
              href={publicInstallUrl}
              className="inline-flex items-center rounded-xl border border-primary/20 px-4 py-2 text-sm font-medium text-primary"
            >
              Install / re-authorize app
            </a>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 py-4">
      <div>
        <h1 className="text-2xl font-semibold text-primary">PorterChain for Shopify</h1>
        <p className="mt-1 text-sm text-muted">
          Connect the store. PorterChain uses your pickup address.
        </p>
      </div>
      <ShopifyConnectCard initialShop={shop} justConnected={justConnected} />
    </div>
  );
}
