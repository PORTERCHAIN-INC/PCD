"use client";

import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import { billingApi } from "@/lib/billing";

export function CodConnectPanel({
  getToken,
  orgId,
}: {
  getToken: () => Promise<string>;
  orgId?: string | null;
}) {
  const [status, setStatus] = useState<{
    cod_enabled: boolean;
    stripe_connect_account_id: string | null;
    connect_ready: boolean;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setErr(null);
    try {
      const token = await getToken();
      setStatus(await billingApi.codStatus(token, orgId ?? undefined));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load COD status");
    }
  }, [getToken, orgId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="space-y-4 rounded-lg border border-border bg-surface p-4">
      <h2 className="text-lg font-semibold text-primary">Cash on delivery (Stripe Connect)</h2>
      <p className="text-sm text-muted">
        Connect your Stripe account, then enable COD. Drivers collect via Payment Link QR at the
        door. Retail Checkout is unchanged.
      </p>
      {err && <p className="text-sm text-danger">{err}</p>}
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
            setErr(null);
            try {
              const token = await getToken();
              const res = await billingApi.codConnect(token, orgId ?? undefined);
              if (res.url) window.location.href = res.url;
              await refresh();
            } catch (e) {
              setErr(e instanceof Error ? e.message : "Connect failed");
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
            setErr(null);
            try {
              const token = await getToken();
              await billingApi.codEnable(token, !status?.cod_enabled, orgId ?? undefined);
              await refresh();
            } catch (e) {
              setErr(e instanceof Error ? e.message : "Update failed");
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
