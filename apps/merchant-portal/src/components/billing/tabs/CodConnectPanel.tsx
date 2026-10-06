"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { PageSkeleton } from "@porterchain/ui/loading";
import Button from "@/components/ui/Button";
import { billingApi } from "@/lib/billing";

export function CodConnectPanel({
  getToken,
  orgId,
}: {
  getToken: () => Promise<string>;
  orgId?: string | null;
}) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [actionErr, setActionErr] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["merchant-cod-status", orgId ?? null],
    queryFn: async () => billingApi.codStatus(await getToken(), orgId ?? undefined),
  });
  const status = query.data ?? null;
  const err =
    actionErr ||
    (query.error instanceof Error ? query.error.message : query.error ? String(query.error) : null);

  const refresh = () => qc.invalidateQueries({ queryKey: ["merchant-cod-status", orgId ?? null] });

  return (
    <div className="space-y-4 rounded-lg border border-border bg-surface p-4">
      <h2 className="text-lg font-semibold text-primary">Cash on delivery (Stripe Connect)</h2>
      <p className="text-sm text-muted">
        Connect your Stripe account, then enable COD. Drivers collect via Payment Link QR at the
        door. Retail Checkout is unchanged.
      </p>
      {err && <p className="text-sm text-danger">{err}</p>}
      {query.isLoading && !status ? <PageSkeleton rows={2} /> : null}
      {status && (
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted">Connect account</dt>
            <dd className="font-mono text-primary">
              {status.stripe_connect_account_id || "Not connected"}
            </dd>
          </div>
          <div>
            <dt className="text-muted">COD enabled</dt>
            <dd className="text-primary">{status.cod_enabled ? "Yes" : "No"}</dd>
          </div>
        </dl>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setActionErr(null);
            try {
              const token = await getToken();
              const res = await billingApi.codConnect(token, orgId ?? undefined);
              if (res.url) window.location.href = res.url;
              await refresh();
            } catch (e) {
              setActionErr(e instanceof Error ? e.message : "Connect failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          {status?.connect_ready ? "Reconnect Stripe" : "Connect Stripe"}
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={busy || !status?.connect_ready}
          onClick={async () => {
            setBusy(true);
            setActionErr(null);
            try {
              const token = await getToken();
              await billingApi.codEnable(token, !status?.cod_enabled, orgId ?? undefined);
              await refresh();
            } catch (e) {
              setActionErr(e instanceof Error ? e.message : "Update failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          {status?.cod_enabled ? "Disable COD" : "Enable COD"}
        </Button>
      </div>
    </div>
  );
}
