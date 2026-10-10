"use client";

import ConnectionsStatus, {
  useConnectionsStatus,
} from "@/components/integrations/ConnectionsStatus";
import ShopifyConnectCard from "@/components/integrations/ShopifyConnectCard";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { integrationsApi } from "@/lib/integrations";
import { shopifyInstallError } from "@/lib/shopifyStatus";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

function normalizeShop(raw: string | null): string {
  if (!raw) return "";
  let value = raw.trim().toLowerCase();
  value = value.replace(/^https?:\/\//, "").split("/", 1)[0] ?? "";
  if (value && !value.includes(".")) {
    value = `${value}.myshopify.com`;
  }
  return value;
}

/**
 * Portal side of the Shopify app. A store installed from Shopify admin arrives
 * here with `?link=<token>` (from the embedded app) and is claimed for this company.
 */
export default function ShopifyAppClient() {
  const { isLoaded, isSignedIn, getApiToken, orgId } = useMerchantAuth();
  const status = useConnectionsStatus();
  const qc = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const shop = normalizeShop(searchParams.get("shop"));
  const linkToken = searchParams.get("link");
  const [linked, setLinked] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);
  const linking = useRef(false);
  const hasStore = (status.data?.shopify.shops.length ?? 0) > 0;

  useEffect(() => {
    if (!isSignedIn || !orgId || !linkToken || linking.current) return;
    linking.current = true;
    void (async () => {
      try {
        await integrationsApi.shopifyLink(await getApiToken(), linkToken, orgId);
        setLinked(true);
        await qc.invalidateQueries();
      } catch (e) {
        const code = e instanceof Error ? e.message : "";
        setLinkError(shopifyInstallError(code) ?? code);
      } finally {
        router.replace("/shopify");
      }
    })();
  }, [isSignedIn, orgId, linkToken, getApiToken, qc, router]);

  if (!isLoaded) return <PageSkeleton rows={3} />;

  return (
    <div className="mx-auto max-w-3xl space-y-4 py-4">
      <h1 className="sr-only">PorterChain for Shopify</h1>
      {linked ? (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          Store linked to this account. Orders that choose PorterChain at checkout now land here.
        </p>
      ) : null}
      {linkError ? (
        <p
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          {linkError}
        </p>
      ) : null}
      <ConnectionsStatus title="PorterChain for Shopify" />
      <details
        open={linked || (!hasStore && status.isSuccess)}
        className="group rounded-3xl border border-primary/10 bg-white"
      >
        <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between px-5 text-base font-bold text-primary sm:px-6">
          Store setup and pickup address
          <span aria-hidden className="text-slate-500 transition group-open:rotate-180">
            ⌄
          </span>
        </summary>
        <div className="border-t border-primary/10 p-4 sm:p-6">
          <ShopifyConnectCard initialShop={shop} justConnected={linked} />
        </div>
      </details>
    </div>
  );
}
