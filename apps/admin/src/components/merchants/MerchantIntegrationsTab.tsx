"use client";

import { useMemo, useState } from "react";
import { ExternalLink } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { ImpersonateModal } from "@/components/settings/panels/users/ImpersonateModal";
import { getSystemLinks } from "@/lib/system-links";
import {
  merchants,
  merchantActionMessage,
  type MerchantTeamUser,
  type MerchantWebhookDeliveryRow,
} from "@/lib/merchants";
import { Badge, Button, Field, Input, SectionCard } from "@/components/crm/primitives";
import { relativeTime, titleCase } from "@/lib/crmFormat";

/** Roles that may mutate merchant integrations (matches API MODULE_PERMISSIONS.merchants). */
const MERCHANTS_WRITE_ROLES = new Set([
  "super_admin",
  "admin",
  "sales",
  "sales_manager",
  "compliance",
]);

/** Freeze / force-disconnect — Superadmin or Compliance only. */
const INTEGRATIONS_ELEVATED_ROLES = new Set(["super_admin", "compliance"]);

/** Merchant seats that can mint keys / webhooks (matches merchant MODULE_PERMISSIONS.api_keys). */
const MERCHANT_KEYS_ROLES = new Set(["merchant_owner", "merchant_admin"]);

function pickIntegrationsSeat(
  team: MerchantTeamUser[] | null | undefined
): MerchantTeamUser | null {
  const active = (team ?? []).filter((u) => u.is_active);
  const owner = active.find((u) => u.role === "merchant_owner");
  if (owner) return owner;
  return active.find((u) => MERCHANT_KEYS_ROLES.has(u.role)) ?? null;
}

function deliveryFailed(d: MerchantWebhookDeliveryRow): boolean {
  if (typeof d.success === "boolean") return !d.success;
  const status = (d.status || "").toLowerCase();
  return status === "failed" || status === "error";
}

function deliveryLabel(d: MerchantWebhookDeliveryRow): string {
  if (typeof d.success === "boolean") return d.success ? "Ok" : "Failed";
  if (d.status) return titleCase(d.status);
  return "Unknown";
}

function deliveryHttp(d: MerchantWebhookDeliveryRow): number | null {
  return d.response_status ?? d.http_status ?? null;
}

function deliveryError(d: MerchantWebhookDeliveryRow): string | null {
  return d.error_message ?? d.error ?? null;
}

export default function MerchantIntegrationsTab({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const { profile } = useAdminProfile();
  const role = profile?.role?.toLowerCase() || "";
  const canMutate = !profile?.role || MERCHANTS_WRITE_ROLES.has(role);
  const canElevate = INTEGRATIONS_ELEVATED_ROLES.has(role);
  const canImpersonate = role === "super_admin";
  const merchantPortalBase =
    getSystemLinks().find((l) => l.id === "merchant")?.href ?? "https://merchant.porterchain.com";

  const [version, setVersion] = useState(0);
  const { data } = useApiData((t) => merchants.api(t, id), [id, version], {
    key: `merchant-api-${id}-${version}`,
  });
  const { data: team } = useApiData((t) => merchants.team(t, id), [id, version], {
    key: `merchant-team-integrations-${id}-${version}`,
  });
  const integrationsSeat = useMemo(() => pickIntegrationsSeat(team), [team]);
  const [impersonateOpen, setImpersonateOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [rateEdits, setRateEdits] = useState<Record<string, string>>({});
  const [openHook, setOpenHook] = useState<string | null>(null);
  const [deliveries, setDeliveries] = useState<MerchantWebhookDeliveryRow[]>([]);
  const [installShop, setInstallShop] = useState("");
  const [freezeReason, setFreezeReason] = useState("");
  const [dlqOpen, setDlqOpen] = useState(false);
  const [dlqRows, setDlqRows] = useState<
    Array<{
      id: string;
      shop_domain: string;
      action: string;
      shopify_order_id: string | null;
      reason_code: string;
      detail: string | null;
      status: string;
      attempts: number;
      porterchain_order_id: string | null;
      created_at: string | null;
    }>
  >([]);

  const apiKeys = data?.api_keys ?? [];
  const webhooks = data?.webhooks ?? [];
  const shops = data?.shopify_shops ?? [];
  const usage = data?.usage;
  const limits = data?.rate_limits ?? [];
  const recent = data?.recent_webhook_deliveries ?? [];
  const health = data?.health;
  const audit = data?.audit_events ?? [];
  const partner = data?.shopify_partner;

  async function copyText(kind: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(kind);
      window.setTimeout(() => setCopied(null), 1500);
    } catch {
      setError("Could not copy to clipboard");
    }
  }

  async function revoke(keyId: string) {
    if (!canMutate) return;
    if (!window.confirm("Revoke this API key? The merchant cannot use it after this.")) return;
    setBusy(keyId);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.revokeApiKey(token, id, keyId);
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Could not revoke that key"));
    } finally {
      setBusy(null);
    }
  }

  async function saveRate(keyId: string) {
    if (!canMutate) return;
    const raw = rateEdits[keyId];
    const rpm = Number(raw);
    if (!Number.isFinite(rpm) || rpm < 10) {
      setError(merchantActionMessage("rate_limit_invalid"));
      return;
    }
    setBusy(`rate-${keyId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.updateApiKeyRateLimit(token, id, keyId, Math.round(rpm));
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Rate limit update failed"));
    } finally {
      setBusy(null);
    }
  }

  async function disableHook(webhookId: string) {
    if (!canMutate) return;
    if (!window.confirm("Disable this webhook? PorterChain will stop posting events to it.")) {
      return;
    }
    setBusy(webhookId);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.disableWebhook(token, id, webhookId);
      setVersion((v) => v + 1);
    } catch (e) {
      setError(
        merchantActionMessage(e instanceof Error ? e.message : "Could not disable that webhook")
      );
    } finally {
      setBusy(null);
    }
  }

  async function enableHook(webhookId: string) {
    if (!canMutate) return;
    setBusy(`enable-${webhookId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.enableWebhook(token, id, webhookId);
      setVersion((v) => v + 1);
    } catch (e) {
      setError(
        merchantActionMessage(e instanceof Error ? e.message : "Could not re-enable that webhook")
      );
    } finally {
      setBusy(null);
    }
  }

  async function sendTest(webhookId: string) {
    if (!canMutate) return;
    setBusy(`test-${webhookId}`);
    setError(null);
    try {
      const token = await getApiToken();
      const result = await merchants.testWebhook(token, id, webhookId);
      if (result && result.success === false) {
        setError(
          merchantActionMessage(
            typeof result.error_message === "string" ? result.error_message : "Test delivery failed"
          )
        );
      }
      setVersion((v) => v + 1);
      if (openHook === webhookId) {
        const rows = await merchants.webhookDeliveries(token, id, webhookId);
        setDeliveries(rows);
      }
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Test webhook failed"));
    } finally {
      setBusy(null);
    }
  }

  async function freezeApi() {
    if (!canElevate) return;
    const reason =
      freezeReason.trim() || window.prompt("Reason for freezing Partner API (required):") || "";
    if (!reason.trim()) {
      setError(merchantActionMessage("reason_required"));
      return;
    }
    if (
      !window.confirm(
        "Freeze Partner API? This revokes all active keys and disables all webhooks for this merchant."
      )
    ) {
      return;
    }
    setBusy("freeze");
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.freezePartnerApi(token, id, reason.trim());
      setFreezeReason("");
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Freeze failed"));
    } finally {
      setBusy(null);
    }
  }

  async function forceDisconnect(shopId: string, domain: string) {
    if (!canElevate) return;
    const reason = window.prompt(`Force-disconnect ${domain}? Enter reason (required):`) || "";
    if (!reason.trim()) {
      setError(merchantActionMessage("reason_required"));
      return;
    }
    setBusy(`disc-${shopId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.forceDisconnectShopify(token, id, shopId, reason.trim());
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Force-disconnect failed"));
    } finally {
      setBusy(null);
    }
  }

  async function toggleIngressPause(shopId: string, domain: string, currentlyPaused: boolean) {
    if (!canElevate) return;
    const next = !currentlyPaused;
    const reason =
      window.prompt(
        `${next ? "Pause" : "Resume"} Shopify ingress for ${domain}? Enter reason (required):`
      ) || "";
    if (!reason.trim()) {
      setError(merchantActionMessage("reason_required"));
      return;
    }
    setBusy(`pause-${shopId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.shopifyIngressPause(token, id, shopId, next, reason.trim());
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Ingress pause failed"));
    } finally {
      setBusy(null);
    }
  }

  async function toggleAutoDispatch(shopId: string, domain: string, currentlyOn: boolean) {
    if (!canElevate) return;
    const next = !currentlyOn;
    const reason =
      window.prompt(
        `${next ? "Enable" : "Disable"} auto-dispatch for ${domain}? Enter reason (required):`
      ) || "";
    if (!reason.trim()) {
      setError(merchantActionMessage("reason_required"));
      return;
    }
    setBusy(`auto-${shopId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.shopifyAutoDispatch(token, id, shopId, next, reason.trim());
      setVersion((v) => v + 1);
    } catch (e) {
      setError(
        merchantActionMessage(e instanceof Error ? e.message : "Auto-dispatch update failed")
      );
    } finally {
      setBusy(null);
    }
  }

  async function loadDlq() {
    if (dlqOpen) {
      setDlqOpen(false);
      return;
    }
    setBusy("dlq");
    setError(null);
    try {
      const token = await getApiToken();
      const res = await merchants.shopifyIngressDlq(token, id);
      setDlqRows(res.items);
      setDlqOpen(true);
    } catch (e) {
      setError(
        merchantActionMessage(e instanceof Error ? e.message : "Could not load ingress DLQ")
      );
    } finally {
      setBusy(null);
    }
  }

  async function replayDlq(dlqId: string) {
    if (!canMutate) return;
    setBusy(`replay-${dlqId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.shopifyIngressDlqReplay(token, id, dlqId);
      const res = await merchants.shopifyIngressDlq(token, id);
      setDlqRows(res.items);
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Replay failed"));
    } finally {
      setBusy(null);
    }
  }

  async function reregisterHooks(shopId: string, domain: string) {
    if (!canElevate) return;
    const reason =
      window.prompt(`Re-register Shopify webhooks + CarrierService for ${domain}? Reason:`) || "";
    if (!reason.trim()) {
      setError(merchantActionMessage("reason_required"));
      return;
    }
    setBusy(`reg-${shopId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.shopifyReregisterHooks(token, id, shopId, reason.trim());
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Re-register failed"));
    } finally {
      setBusy(null);
    }
  }

  async function editBookingPolicy(
    shopId: string,
    domain: string,
    vehicle?: string | null,
    pkg?: string | null
  ) {
    if (!canElevate) return;
    const vehicleNext =
      window.prompt(
        `Default vehicle for ${domain} (e.g. cargo_van, box_16):`,
        vehicle || "cargo_van"
      ) ?? "";
    const packageNext =
      window.prompt(
        `Default package for ${domain} (e.g. looseParcel, ltlPallet):`,
        pkg || "looseParcel"
      ) ?? "";
    const reason = window.prompt("Reason for booking policy change:") || "";
    if (!reason.trim()) {
      setError(merchantActionMessage("reason_required"));
      return;
    }
    setBusy(`policy-${shopId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.shopifyBookingPolicy(token, id, shopId, {
        default_vehicle_class: vehicleNext.trim() || null,
        default_package_type: packageNext.trim() || null,
        reason: reason.trim(),
      });
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Policy update failed"));
    } finally {
      setBusy(null);
    }
  }

  async function copyInstallUrl(shopDomain?: string) {
    if (!canMutate) return;
    const shop = (shopDomain || installShop).trim();
    if (!shop) {
      setError("Enter a myshopify.com shop domain first");
      return;
    }
    setBusy("install-url");
    setError(null);
    try {
      const token = await getApiToken();
      const res = await merchants.shopifyInstallUrl(token, id, shop);
      await copyText("install-url", res.install_url);
      setInstallShop(res.shop_domain);
    } catch (e) {
      setError(
        merchantActionMessage(e instanceof Error ? e.message : "Could not build install URL")
      );
    } finally {
      setBusy(null);
    }
  }

  async function loadDeliveries(webhookId: string) {
    if (openHook === webhookId) {
      setOpenHook(null);
      setDeliveries([]);
      return;
    }
    setBusy(`del-${webhookId}`);
    setError(null);
    try {
      const token = await getApiToken();
      const rows = await merchants.webhookDeliveries(token, id, webhookId);
      setDeliveries(rows);
      setOpenHook(webhookId);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Could not load deliveries"));
    } finally {
      setBusy(null);
    }
  }

  async function retryDelivery(deliveryId: string) {
    if (!canMutate) return;
    setBusy(`retry-${deliveryId}`);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.retryWebhookDelivery(token, id, deliveryId);
      if (openHook) {
        const rows = await merchants.webhookDeliveries(token, id, openHook);
        setDeliveries(rows);
      }
      setVersion((v) => v + 1);
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Retry failed"));
    } finally {
      setBusy(null);
    }
  }

  const keysHref = `${merchantPortalBase}/api?tab=keys`;
  const hooksHref = `${merchantPortalBase}/api?tab=webhooks`;
  const shopifyHref = `${merchantPortalBase}/shopify`;
  const docsHref = `${merchantPortalBase}/api?tab=docs`;

  return (
    <div className="space-y-5">
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {profile?.role && !canMutate && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          Read-only role — revoke, rate limits, disable, and retry need a merchants write seat.
        </p>
      )}

      <div className="space-y-2 rounded-xl border border-primary/10 bg-gray-bg/40 px-4 py-3 text-sm">
        <p className="text-muted">
          Integrations health for this merchant. Keys, webhooks, and Shopify connect are minted in
          the merchant portal by an Owner/Manager seat — staff Super Admin on this page cannot mint
          while signed into Admin. Admin revokes, throttles, re-enables, and retries.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {canImpersonate && integrationsSeat ? (
            <Button variant="outline" className="text-xs" onClick={() => setImpersonateOpen(true)}>
              Open Integrations as {integrationsSeat.role_label || "Owner"}
            </Button>
          ) : null}
          {canImpersonate && !integrationsSeat ? (
            <p className="text-xs text-amber-800">
              No active Owner/Manager seat yet — add one on the Team tab, then open Integrations as
              that user.
            </p>
          ) : null}
          {!canImpersonate ? (
            <a
              href={keysHref}
              className="inline-flex items-center gap-1 text-xs text-secondary underline"
              target="_blank"
              rel="noreferrer"
            >
              Merchant portal (your own seat) <ExternalLink className="h-3 w-3" />
            </a>
          ) : null}
        </div>
      </div>

      {impersonateOpen && integrationsSeat ? (
        <ImpersonateModal
          open
          targetType="merchant"
          targetId={integrationsSeat.id}
          targetLabel={integrationsSeat.email}
          getApiToken={getApiToken}
          nextPath="/api?tab=keys"
          onClose={() => setImpersonateOpen(false)}
        />
      ) : null}

      {/* 1. Health — Overview mirror */}
      <SectionCard title="Health">
        <div className="grid gap-3 px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="API keys" value={String(data?.api_keys_count ?? apiKeys.length)} />
          <Metric label="Webhooks" value={String(data?.webhooks_count ?? webhooks.length)} />
          <Metric label="Requests (7d)" value={String(usage?.total_requests ?? 0)} />
          <Metric label="Test preference" value={data?.sandbox_mode ? "On" : "Off"} />
        </div>
        {health?.failed_deliveries_recent || health?.throttled_keys ? (
          <p className="border-t border-primary/5 px-5 py-2 text-xs text-muted">
            {health.throttled_keys ? (
              <span className="mr-3 text-red-600">{health.throttled_keys} key(s) throttled</span>
            ) : null}
            {health.failed_deliveries_recent ? (
              <span className="text-red-600">
                {health.failed_deliveries_recent} failed delivery(ies) in recent log
              </span>
            ) : null}
          </p>
        ) : null}
        <div className="border-t border-primary/5 px-5 py-4">
          <h3 className="text-sm font-semibold text-primary">Live rate limits</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {limits.length === 0 && <li className="text-muted">No active keys</li>}
            {limits.map((l) => (
              <li key={l.api_key_id} className="flex justify-between gap-4">
                <span>
                  {l.name} <span className="text-muted">({l.environment})</span>
                </span>
                <span className={l.throttled ? "text-red-600" : "text-muted"}>
                  {l.requests_last_minute}/{l.rate_limit_per_minute} per min
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="border-t border-primary/5 px-5 py-4">
          <h3 className="text-sm font-semibold text-primary">Recent webhook deliveries</h3>
          {recent.length === 0 ? (
            <p className="mt-2 text-sm text-muted">No deliveries yet.</p>
          ) : (
            <ul className="mt-2 divide-y divide-primary/5">
              {recent.map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-2 py-2 text-xs">
                  <div className="min-w-0">
                    <p className="font-medium text-primary">
                      {d.event_type || "event"} · {deliveryLabel(d)}
                      {deliveryHttp(d) != null ? ` · HTTP ${deliveryHttp(d)}` : ""}
                    </p>
                    <p className="truncate text-muted">
                      {deliveryError(d) || relativeTime(d.created_at)}
                    </p>
                  </div>
                  {deliveryFailed(d) && canMutate ? (
                    <Button
                      variant="outline"
                      className="text-xs"
                      disabled={busy === `retry-${d.id}`}
                      onClick={() => void retryDelivery(d.id)}
                    >
                      {busy === `retry-${d.id}` ? "…" : "Retry"}
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
        {canElevate ? (
          <div className="space-y-2 border-t border-primary/5 px-5 py-4">
            <h3 className="text-sm font-semibold text-primary">Freeze Partner API</h3>
            <p className="text-xs text-muted">
              Superadmin / Compliance — revokes every active key and disables every webhook.
            </p>
            <div className="flex flex-wrap items-end gap-2">
              <Field label="Reason">
                <Input
                  className="min-w-[16rem]"
                  value={freezeReason}
                  onChange={(e) => setFreezeReason(e.target.value)}
                  placeholder="Abuse / compromised / suspend"
                />
              </Field>
              <Button
                variant="outline"
                className="text-xs text-red-700"
                disabled={busy === "freeze"}
                onClick={() => void freezeApi()}
              >
                {busy === "freeze" ? "Freezing…" : "Freeze Partner API"}
              </Button>
            </div>
          </div>
        ) : null}
      </SectionCard>

      {/* Audit strip */}
      <SectionCard title="Integrations audit">
        {audit.length === 0 ? (
          <p className="px-5 py-6 text-sm text-muted">
            No key, webhook, Shopify, or freeze events yet.
          </p>
        ) : (
          <ul className="divide-y divide-primary/5">
            {audit.map((ev) => {
              const email =
                typeof ev.payload?.admin_email === "string" ? ev.payload.admin_email : null;
              const reason = typeof ev.payload?.reason === "string" ? ev.payload.reason : null;
              return (
                <li key={ev.id} className="px-5 py-2 text-xs">
                  <p className="font-medium text-primary">
                    {ev.action}
                    {email ? ` · ${email}` : ev.actor_user_id ? ` · ${ev.actor_user_id}` : ""}
                  </p>
                  <p className="text-muted">
                    {relativeTime(ev.created_at)}
                    {reason ? ` · ${reason}` : ""}
                    {ev.resource_id ? ` · ${ev.resource_type} ${ev.resource_id.slice(0, 8)}…` : ""}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </SectionCard>

      {/* 2. Shopify — always on + partner health */}
      <SectionCard title={`Shopify (${shops.length})`}>
        {data?.shopify_webhook_url ? (
          <div className="flex flex-wrap items-center gap-2 border-b border-primary/5 px-5 py-3 text-xs">
            <span className="text-muted">Ingress webhook</span>
            <code className="max-w-full truncate rounded bg-gray-bg px-1.5 py-0.5 text-[11px] text-primary">
              {data.shopify_webhook_url}
            </code>
            <Button
              variant="outline"
              className="text-xs"
              onClick={() => void copyText("shopify-wh", data.shopify_webhook_url || "")}
            >
              {copied === "shopify-wh" ? "Copied" : "Copy"}
            </Button>
          </div>
        ) : null}
        {partner ? (
          <div className="grid gap-3 border-b border-primary/5 px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Carrier quotes (24h)" value={String(partner.rate_quotes_24h ?? 0)} />
            <Metric
              label="Last quote"
              value={partner.last_rate_quote_at ? relativeTime(partner.last_rate_quote_at) : "—"}
            />
            <Metric
              label="Last Shopify book"
              value={partner.last_book_at ? relativeTime(partner.last_book_at) : "—"}
            />
            <Metric
              label="Last fulfillment"
              value={partner.last_fulfillment_at ? relativeTime(partner.last_fulfillment_at) : "—"}
            />
            <Metric
              label="Last tracking event"
              value={
                partner.last_fulfillment?.last_event_status
                  ? titleCase(partner.last_fulfillment.last_event_status)
                  : "—"
              }
            />
            <Metric label="Ingress DLQ open" value={String(partner.ingress_dlq_open ?? 0)} />
            {partner.fulfillment_callback_url ? (
              <div className="sm:col-span-2 lg:col-span-4 flex flex-wrap items-center gap-2 text-xs">
                <span className="text-muted">Fulfillment callback</span>
                <code className="max-w-full truncate rounded bg-gray-bg px-1.5 py-0.5 text-[11px]">
                  {partner.fulfillment_callback_url}
                </code>
                <Button
                  variant="outline"
                  className="text-xs"
                  onClick={() => void copyText("fs-url", partner.fulfillment_callback_url || "")}
                >
                  {copied === "fs-url" ? "Copied" : "Copy"}
                </Button>
              </div>
            ) : null}
            {partner.carrier_rates_url ? (
              <div className="sm:col-span-2 lg:col-span-4 flex flex-wrap items-center gap-2 text-xs">
                <span className="text-muted">CarrierService callback</span>
                <code className="max-w-full truncate rounded bg-gray-bg px-1.5 py-0.5 text-[11px]">
                  {partner.carrier_rates_url}
                </code>
                <Button
                  variant="outline"
                  className="text-xs"
                  onClick={() => void copyText("carrier-url", partner.carrier_rates_url || "")}
                >
                  {copied === "carrier-url" ? "Copied" : "Copy"}
                </Button>
                {partner.quote_book_locked ? (
                  <Badge tone="green">Last book Quote≡Book</Badge>
                ) : partner.last_book_at ? (
                  <Badge tone="amber">Last book missing rate quote</Badge>
                ) : null}
                {partner.mid_flight_tracking ? (
                  <Badge tone="green">Mid-flight tracking</Badge>
                ) : null}
                {partner.fo_partner_path === "flag_off" || partner.fo_partner_path === "pending" ? (
                  <Badge tone="slate">FO partner path off</Badge>
                ) : partner.fo_partner_path === "flag_on" ? (
                  <Badge tone="green">FO accept live</Badge>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
        {canMutate ? (
          <div className="flex flex-wrap items-end gap-2 border-b border-primary/5 px-5 py-3">
            <Field label="Shop domain for install URL">
              <Input
                className="min-w-[14rem]"
                value={installShop}
                onChange={(e) => setInstallShop(e.target.value)}
                placeholder="store.myshopify.com"
              />
            </Field>
            <Button
              variant="outline"
              className="text-xs"
              disabled={busy === "install-url"}
              onClick={() => void copyInstallUrl()}
            >
              {busy === "install-url"
                ? "…"
                : copied === "install-url"
                  ? "Copied install URL"
                  : "Copy OAuth install URL"}
            </Button>
            {!partner?.oauth_configured ? (
              <span className="text-xs text-amber-700">OAuth not configured on this API</span>
            ) : null}
          </div>
        ) : null}
        {shops.length === 0 ? (
          <div className="space-y-2 px-5 py-8 text-center">
            <p className="text-sm font-medium text-primary">Not connected</p>
            <p className="text-sm text-muted">
              Merchant Owner connects the store in the merchant portal (Shopify or Integrations).
              Support can copy an OAuth install URL above.
            </p>
            <a
              href={shopifyHref}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-sm text-secondary underline"
            >
              Open merchant Shopify setup <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        ) : (
          <div className="divide-y divide-primary/5">
            {shops.map((s) => (
              <div key={s.id} className="flex items-start justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-primary">{s.shop_domain}</p>
                  <p className="text-xs text-muted">
                    {s.last_webhook_at
                      ? `Last webhook ${relativeTime(s.last_webhook_at)}`
                      : "No webhooks yet"}
                    {s.default_pickup ? ` · Pickup: ${s.default_pickup}` : ""}
                  </p>
                  {s.missing_pickup ? (
                    <p className="mt-1 text-xs text-amber-700">
                      Missing default pickup — Shopify bookings will fail until set.
                    </p>
                  ) : null}
                  <div className="mt-2 flex flex-wrap gap-2">
                    {s.installed ? (
                      <Badge tone={s.carrier_registered ? "slate" : "amber"}>
                        {s.carrier_registered
                          ? "Checkout rates registered"
                          : "Checkout rates not registered"}
                      </Badge>
                    ) : null}
                    {s.installed ? (
                      <Badge tone={s.fulfillment_service_registered ? "slate" : "amber"}>
                        {s.fulfillment_service_registered
                          ? "Fulfillment service registered"
                          : "Fulfillment service not registered"}
                      </Badge>
                    ) : null}
                    {s.ingress_paused ? <Badge tone="amber">Ingress paused</Badge> : null}
                    {s.auto_dispatch === false ? <Badge tone="amber">Hold at BOOKED</Badge> : null}
                    {s.default_vehicle_class || s.default_package_type ? (
                      <Badge tone="slate">
                        {s.default_vehicle_class || "cargo_van"} /{" "}
                        {s.default_package_type || "looseParcel"}
                      </Badge>
                    ) : null}
                    {canMutate && s.installed ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === "install-url"}
                        onClick={() => void copyInstallUrl(s.shop_domain)}
                      >
                        Copy install URL
                      </Button>
                    ) : null}
                    {canElevate && s.installed ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === `reg-${s.id}`}
                        onClick={() => void reregisterHooks(s.id, s.shop_domain)}
                      >
                        {busy === `reg-${s.id}` ? "…" : "Re-register hooks"}
                      </Button>
                    ) : null}
                    {canElevate && s.installed ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === `policy-${s.id}`}
                        onClick={() =>
                          void editBookingPolicy(
                            s.id,
                            s.shop_domain,
                            s.default_vehicle_class,
                            s.default_package_type
                          )
                        }
                      >
                        {busy === `policy-${s.id}` ? "…" : "Booking policy"}
                      </Button>
                    ) : null}
                    {canElevate && s.installed ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === `pause-${s.id}`}
                        onClick={() =>
                          void toggleIngressPause(s.id, s.shop_domain, Boolean(s.ingress_paused))
                        }
                      >
                        {busy === `pause-${s.id}`
                          ? "…"
                          : s.ingress_paused
                            ? "Resume ingress"
                            : "Pause ingress"}
                      </Button>
                    ) : null}
                    {canElevate && s.installed ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === `auto-${s.id}`}
                        onClick={() =>
                          void toggleAutoDispatch(s.id, s.shop_domain, s.auto_dispatch !== false)
                        }
                      >
                        {busy === `auto-${s.id}`
                          ? "…"
                          : s.auto_dispatch === false
                            ? "Enable auto-dispatch"
                            : "Hold at BOOKED"}
                      </Button>
                    ) : null}
                    {canElevate && s.installed ? (
                      <Button
                        variant="outline"
                        className="text-xs text-red-700"
                        disabled={busy === `disc-${s.id}`}
                        onClick={() => void forceDisconnect(s.id, s.shop_domain)}
                      >
                        {busy === `disc-${s.id}` ? "…" : "Force-disconnect"}
                      </Button>
                    ) : null}
                  </div>
                </div>
                <Badge tone={s.installed ? "green" : "slate"}>
                  {s.installed ? "Connected" : "Uninstalled"}
                </Badge>
              </div>
            ))}
          </div>
        )}
        <div className="border-t border-primary/5 px-5 py-3">
          <Button
            variant="outline"
            className="text-xs"
            disabled={busy === "dlq"}
            onClick={() => void loadDlq()}
          >
            {busy === "dlq" ? "…" : dlqOpen ? "Hide ingress DLQ" : "Show ingress DLQ"}
          </Button>
          {dlqOpen ? (
            <ul className="mt-3 max-h-64 space-y-2 overflow-y-auto text-xs">
              {dlqRows.length === 0 ? (
                <li className="text-muted">No DLQ rows.</li>
              ) : (
                dlqRows.map((row) => (
                  <li
                    key={row.id}
                    className="flex flex-wrap items-start justify-between gap-2 rounded-lg bg-gray-bg px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-primary">
                        {row.reason_code} · {row.status}
                      </p>
                      <p className="text-muted">
                        {row.shop_domain}
                        {row.shopify_order_id ? ` · #${row.shopify_order_id}` : ""}
                        {row.created_at ? ` · ${relativeTime(row.created_at)}` : ""}
                      </p>
                      {row.detail ? <p className="mt-0.5 text-muted">{row.detail}</p> : null}
                    </div>
                    {canMutate && row.status !== "resolved" ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === `replay-${row.id}`}
                        onClick={() => void replayDlq(row.id)}
                      >
                        {busy === `replay-${row.id}` ? "…" : "Replay"}
                      </Button>
                    ) : null}
                  </li>
                ))
              )}
            </ul>
          ) : null}
        </div>
      </SectionCard>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* 3. API keys */}
        <SectionCard title={`API keys (${apiKeys.length})`}>
          <div className="divide-y divide-primary/5">
            {apiKeys.map((k) => {
              const live = limits.find((l) => l.api_key_id === k.id);
              return (
                <div key={k.id} className="space-y-2 px-5 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-primary">
                        {k.name}{" "}
                        <Badge tone={k.environment === "production" ? "green" : "slate"}>
                          {titleCase(k.environment)}
                        </Badge>
                        {!k.is_active && (
                          <Badge tone="red" className="ml-1">
                            Revoked
                          </Badge>
                        )}
                        {live?.throttled ? (
                          <Badge tone="red" className="ml-1">
                            Throttled
                          </Badge>
                        ) : null}
                      </p>
                      <p className="text-xs text-muted">
                        {k.key_prefix}••• · {k.rate_limit_per_minute}/min · last used{" "}
                        {relativeTime(k.last_used_at)}
                      </p>
                      {(k.scopes || []).length > 0 ? (
                        <p className="mt-1 flex flex-wrap gap-1">
                          {k.scopes.map((scope) => (
                            <Badge key={scope} tone="slate" className="text-[10px]">
                              {scope}
                            </Badge>
                          ))}
                        </p>
                      ) : null}
                    </div>
                    {k.is_active && canMutate ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === k.id}
                        onClick={() => void revoke(k.id)}
                      >
                        {busy === k.id ? "Revoking…" : "Revoke"}
                      </Button>
                    ) : null}
                  </div>
                  {k.is_active && canMutate ? (
                    <div className="flex flex-wrap items-end gap-2">
                      <Field label="Rate / min">
                        <Input
                          type="number"
                          min={10}
                          className="w-28"
                          value={rateEdits[k.id] ?? String(k.rate_limit_per_minute)}
                          onChange={(e) =>
                            setRateEdits((prev) => ({ ...prev, [k.id]: e.target.value }))
                          }
                        />
                      </Field>
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === `rate-${k.id}`}
                        onClick={() => void saveRate(k.id)}
                      >
                        {busy === `rate-${k.id}` ? "Saving…" : "Save limit"}
                      </Button>
                    </div>
                  ) : null}
                </div>
              );
            })}
            {apiKeys.length === 0 && (
              <div className="space-y-2 px-5 py-10 text-center">
                <p className="text-sm text-muted">No API keys.</p>
                <p className="text-xs text-muted">
                  Merchant Owner generates keys at Integrations → API keys (sandbox first, then
                  production).
                </p>
                {canImpersonate && integrationsSeat ? (
                  <Button
                    variant="outline"
                    className="text-xs"
                    onClick={() => setImpersonateOpen(true)}
                  >
                    Open Integrations as {integrationsSeat.role_label || "Owner"}
                  </Button>
                ) : (
                  <a
                    href={keysHref}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-secondary underline"
                  >
                    Open merchant API keys <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            )}
          </div>
        </SectionCard>

        {/* 4. Webhooks */}
        <SectionCard title={`Webhooks (${webhooks.length})`}>
          <div className="divide-y divide-primary/5">
            {webhooks.map((w) => (
              <div key={w.id} className="space-y-2 px-5 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-primary">{w.url}</p>
                    <p className="text-xs text-muted">
                      <Badge
                        tone={w.environment === "production" ? "green" : "slate"}
                        className="mr-1"
                      >
                        {titleCase(w.environment || "production")}
                      </Badge>
                      {w.events.join(", ") || "all events"}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col gap-1">
                    <Button
                      variant="outline"
                      className="text-xs"
                      disabled={busy === `del-${w.id}`}
                      aria-busy={busy === `del-${w.id}`}
                      onClick={() => void loadDeliveries(w.id)}
                    >
                      {openHook === w.id
                        ? "Hide deliveries"
                        : busy === `del-${w.id}`
                          ? "Working…"
                          : "Deliveries"}
                    </Button>
                    {canMutate ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === `test-${w.id}`}
                        onClick={() => void sendTest(w.id)}
                      >
                        {busy === `test-${w.id}` ? "Sending…" : "Send test"}
                      </Button>
                    ) : null}
                    {w.is_active && canMutate ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === w.id}
                        onClick={() => void disableHook(w.id)}
                      >
                        {busy === w.id ? "Disabling…" : "Disable"}
                      </Button>
                    ) : !w.is_active && canMutate ? (
                      <Button
                        variant="outline"
                        className="text-xs"
                        disabled={busy === `enable-${w.id}`}
                        onClick={() => void enableHook(w.id)}
                      >
                        {busy === `enable-${w.id}` ? "Enabling…" : "Re-enable"}
                      </Button>
                    ) : !w.is_active ? (
                      <Badge tone="red">Disabled</Badge>
                    ) : null}
                  </div>
                </div>
                {openHook === w.id && (
                  <div className="rounded-xl border border-primary/10 bg-gray-bg/40">
                    {deliveries.length === 0 ? (
                      <p className="px-3 py-4 text-center text-xs text-muted">No deliveries yet.</p>
                    ) : (
                      deliveries.map((d) => (
                        <div
                          key={d.id}
                          className="flex items-center justify-between gap-2 border-t border-primary/5 px-3 py-2 first:border-t-0"
                        >
                          <div className="min-w-0">
                            <p className="text-xs font-medium text-primary">
                              {deliveryLabel(d)}
                              {deliveryHttp(d) != null ? ` · HTTP ${deliveryHttp(d)}` : ""} ·
                              attempt {d.attempt}
                              {d.event_type ? ` · ${d.event_type}` : ""}
                            </p>
                            <p className="truncate text-[11px] text-muted">
                              {deliveryError(d) || relativeTime(d.created_at)}
                            </p>
                          </div>
                          {deliveryFailed(d) && canMutate && (
                            <Button
                              variant="outline"
                              className="text-xs"
                              disabled={busy === `retry-${d.id}`}
                              onClick={() => void retryDelivery(d.id)}
                            >
                              {busy === `retry-${d.id}` ? "…" : "Retry"}
                            </Button>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            ))}
            {webhooks.length === 0 && (
              <div className="space-y-2 px-5 py-10 text-center">
                <p className="text-sm text-muted">No webhooks.</p>
                <p className="text-xs text-muted">
                  Merchant creates HTTPS webhooks in Integrations → Webhooks, then Send test.
                </p>
                <a
                  href={hooksHref}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-secondary underline"
                >
                  Open merchant webhooks <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            )}
          </div>
        </SectionCard>
      </div>

      {/* 5. Usage */}
      <SectionCard title="API usage (7d)">
        <div className="grid gap-3 px-5 py-4 sm:grid-cols-3">
          <Metric label="Total requests" value={String(usage?.total_requests ?? 0)} />
          <Metric label="Errors" value={String(usage?.error_requests ?? 0)} />
          <Metric label="Sandbox calls" value={String(usage?.by_environment?.sandbox ?? 0)} />
        </div>
        {(usage?.by_path?.length ?? 0) > 0 ? (
          <div className="border-t border-primary/5 px-5 py-4">
            <h3 className="text-sm font-semibold text-primary">Top endpoints</h3>
            <ul className="mt-2 space-y-1 text-sm">
              {usage!.by_path.slice(0, 5).map((p) => (
                <li key={p.path} className="flex justify-between gap-4">
                  <code className="truncate text-xs text-primary">{p.path}</code>
                  <span className="text-muted">{p.count}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="border-t border-primary/5 px-5 py-4 text-sm text-muted">
            No Partner API traffic in the last 7 days.
          </p>
        )}
      </SectionCard>

      {/* 6. Sandbox read-only */}
      <SectionCard title="Sandbox">
        <div className="px-5 py-4 text-sm">
          <p>
            Test preference:{" "}
            <Badge tone={data?.sandbox_mode ? "amber" : "green"}>
              {data?.sandbox_mode ? "On" : "Off"}
            </Badge>
            <span className="ml-2 text-muted">
              ({data?.booking_env_preference || (data?.sandbox_mode ? "sandbox" : "live")})
            </span>
          </p>
          <p className="mt-2 text-xs text-muted">
            Portal reminder only — Partner API dry-run is controlled by{" "}
            <code className="rounded bg-gray-bg px-1">pk_sandbox_</code> vs{" "}
            <code className="rounded bg-gray-bg px-1">pk_production_</code> keys. Console, simulate,
            and purge stay in the merchant portal.
          </p>
        </div>
      </SectionCard>

      {/* 7. Docs / go-live */}
      <SectionCard title="Go-live checklist">
        <ol className="list-decimal space-y-1 px-5 py-4 pl-9 text-sm text-primary">
          <li>Create a sandbox API key and sandbox webhook URL in the merchant portal.</li>
          <li>Book a test shipment or run Sandbox → simulate lifecycle.</li>
          <li>
            Verify HMAC: <code className="text-xs">X-Porterchain-Signature</code> + timestamp.
          </li>
          <li>Owner mints a production key and production webhook after handlers pass.</li>
          <li>Connect Shopify (if retail) and set default pickup.</li>
        </ol>
        <div className="flex flex-wrap gap-3 border-t border-primary/5 px-5 py-3 text-sm">
          <a
            href={docsHref}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-secondary underline"
          >
            Merchant docs <ExternalLink className="h-3.5 w-3.5" />
          </a>
          {canImpersonate && integrationsSeat ? (
            <Button variant="outline" className="text-xs" onClick={() => setImpersonateOpen(true)}>
              Open Integrations as {integrationsSeat.role_label || "Owner"}
            </Button>
          ) : (
            <a
              href={keysHref}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-secondary underline"
            >
              Merchant Integrations <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-gray-bg/40 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-0.5 text-lg font-semibold text-primary">{value}</p>
    </div>
  );
}
