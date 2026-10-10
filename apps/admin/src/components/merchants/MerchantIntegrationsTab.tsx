"use client";

/**
 * Connections tab. One status line per integration (light + plain reason), one Fix per
 * problem, everything else in a ⋯ menu or a collapsed "Details". Replaces the old
 * Integrations wall and the separate watchdog panel (they showed health twice).
 */

import { useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, PlugZap, RefreshCw, ShoppingBag, KeyRound, Webhook } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { ImpersonateModal } from "@/components/settings/panels/users/ImpersonateModal";
import { getSystemLinks } from "@/lib/system-links";
import {
  merchants,
  merchantActionMessage,
  RETAIL_VEHICLE_OPTIONS,
  vehicleClassLabel,
  type MerchantTeamUser,
  type MerchantWebhookDeliveryRow,
} from "@/lib/merchants";
import { merchantOps, cad, type ConnectionItem } from "@/lib/merchant-ops";
import { ordersApi } from "@/lib/orders";
import {
  ago,
  canElevateIntegrations,
  canMutateIntegrations,
  deliveryFailed,
  hookStatus,
  keyStatus,
  policyPayload,
  shopStatus,
  summarize,
  type Light,
  type Status,
} from "@/lib/merchant-connections";
import {
  ActionMenu,
  Dialog,
  Empty,
  FieldLabel,
  Panel,
  PrimaryAction,
  QuietButton,
  ReasonDialog,
  SkeletonRows,
  inputClass,
  type MenuItem,
} from "./ops/ui";

const DOT: Record<Light, string> = {
  red: "bg-red-600",
  amber: "bg-amber-500",
  green: "bg-emerald-600",
  off: "bg-slate-300",
};
const WORD: Record<Light, string> = {
  red: "Needs fixing",
  amber: "Watch",
  green: "Healthy",
  off: "Off",
};
const MERCHANT_KEYS_ROLES = new Set(["merchant_owner", "merchant_admin"]);

function pickSeat(team: MerchantTeamUser[] | null | undefined): MerchantTeamUser | null {
  const active = (team ?? []).filter((u) => u.is_active !== false);
  return (
    active.find((u) => u.role === "merchant_owner") ??
    active.find((u) => MERCHANT_KEYS_ROLES.has(u.role)) ??
    null
  );
}

type Reasoned =
  | { kind: "pause"; shopId: string; domain: string; paused: boolean }
  | { kind: "auto"; shopId: string; domain: string; on: boolean }
  | { kind: "repair"; shopId: string; domain: string }
  | { kind: "disconnect"; shopId: string; domain: string }
  | { kind: "freeze" }
  | { kind: "rotate"; keyId: string; name: string };
type Confirm =
  | { kind: "revoke"; keyId: string; name: string }
  | { kind: "hook_off"; hookId: string; url: string };

const REASONED_COPY: Record<
  Reasoned["kind"],
  (r: Reasoned) => { title: string; body: string; cta: string; danger?: boolean }
> = {
  pause: (r) => {
    const p = r as Extract<Reasoned, { kind: "pause" }>;
    return p.paused
      ? {
          title: `Resume orders from ${p.domain}?`,
          body: "New Shopify orders will be booked again.",
          cta: "Resume orders",
        }
      : {
          title: `Pause orders from ${p.domain}?`,
          body: "New Shopify orders wait in a queue until you resume.",
          cta: "Pause orders",
          danger: true,
        };
  },
  auto: (r) => {
    const a = r as Extract<Reasoned, { kind: "auto" }>;
    return a.on
      ? {
          title: "Turn off auto-dispatch?",
          body: "Shopify orders will wait for staff to release them.",
          cta: "Turn off",
        }
      : {
          title: "Turn on auto-dispatch?",
          body: "Shopify orders go straight to drivers.",
          cta: "Turn on",
        };
  },
  repair: (r) => ({
    title: `Repair ${(r as Extract<Reasoned, { kind: "repair" }>).domain}?`,
    body: "Re-registers order updates and checkout shipping rates with Shopify.",
    cta: "Repair",
  }),
  disconnect: (r) => ({
    title: `Disconnect ${(r as Extract<Reasoned, { kind: "disconnect" }>).domain}?`,
    body: "Stops all Shopify orders and rates for this store until the merchant reconnects.",
    cta: "Disconnect",
    danger: true,
  }),
  freeze: () => ({
    title: "Freeze all API access?",
    body: "Revokes every API key and turns off every webhook for this merchant. Use for a leak or abuse.",
    cta: "Freeze",
    danger: true,
  }),
  rotate: (r) => ({
    title: `Replace ${(r as Extract<Reasoned, { kind: "rotate" }>).name}?`,
    body: "Issues a new key now. The old one keeps working for 7 days. Copy the new key from the next screen.",
    cta: "Replace key",
  }),
};

export default function MerchantIntegrationsTab({ id }: { id: string }) {
  const router = useRouter();
  const { getApiToken } = useAdminAuth();
  const { profile } = useAdminProfile();
  const role = profile?.role?.toLowerCase() || "";
  const canMutate = canMutateIntegrations(role);
  const canElevate = canElevateIntegrations(role);
  const canImpersonate = role === "super_admin";
  const portal =
    getSystemLinks().find((l) => l.id === "merchant")?.href ?? "https://merchant.porterchain.com";

  const [version, setVersion] = useState(0);
  const { data, error } = useApiData((t) => merchants.api(t, id), [id, version], {
    key: `merchant-api-${id}`,
  });
  const { data: watch } = useApiData((t) => merchantOps.connections(t, id), [id, version], {
    key: `merchant-connections-${id}`,
  });
  const { data: team } = useApiData((t) => merchants.team(t, id), [id], {
    key: `merchant-team-integrations-${id}`,
  });
  const seat = useMemo(() => pickSeat(team), [team]);

  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; bad?: boolean } | null>(null);
  const [reasoned, setReasoned] = useState<Reasoned | null>(null);
  const [confirm, setConfirm] = useState<Confirm | null>(null);
  const [secret, setSecret] = useState<string | null>(null);
  const [rate, setRate] = useState<{ keyId: string; value: string } | null>(null);
  const [policy, setPolicy] = useState<{
    shopId: string;
    domain: string;
    vehicle: string;
    pkg: string;
    current: { vehicle: string | null | undefined; pkg: string | null | undefined };
  } | null>(null);
  const [policyReason, setPolicyReason] = useState("");
  const [install, setInstall] = useState<{ shop: string } | null>(null);
  const [impersonate, setImpersonate] = useState(false);
  const [dlq, setDlq] = useState<
    Awaited<ReturnType<typeof merchants.shopifyIngressDlq>>["items"] | null
  >(null);
  const [log, setLog] = useState<{ hookId: string; rows: MerchantWebhookDeliveryRow[] } | null>(
    null
  );

  const watchById = useMemo(() => {
    const m = new Map<string, ConnectionItem>();
    (watch?.items ?? []).forEach((i) => m.set(`${i.kind}:${i.id}`, i));
    return m;
  }, [watch]);

  async function run(fn: (t: string) => Promise<string | void>, after?: () => void) {
    setBusy(true);
    setToast(null);
    try {
      const t = await getApiToken();
      const msg = await fn(t);
      if (msg) setToast({ text: msg });
      setVersion((v) => v + 1);
      after?.();
    } catch (e) {
      setToast({
        text: merchantActionMessage(e instanceof Error ? e.message : "That didn't work"),
        bad: true,
      });
    } finally {
      setBusy(false);
    }
  }

  const copy = (text: string, label: string) =>
    navigator.clipboard.writeText(text).then(
      () => setToast({ text: `${label} copied` }),
      () => setToast({ text: "Could not copy to clipboard", bad: true })
    );

  const sendInstallLink = (shop: string) =>
    run(async (t) => {
      const res = await merchants.shopifyInstallUrl(t, id, shop.trim());
      await copy(res.install_url, `Reconnect link for ${res.shop_domain}`);
      setInstall(null);
    });

  const loadDlq = () =>
    run(async (t) => {
      setDlq((await merchants.shopifyIngressDlq(t, id)).items);
    });

  const openLog = (hookId: string) =>
    run(async (t) => {
      setLog({ hookId, rows: await merchants.webhookDeliveries(t, id, hookId) });
    });

  function doFix(
    s: Status,
    ctx: {
      shopId?: string;
      domain?: string;
      paused?: boolean;
      keyId?: string;
      name?: string;
      hookId?: string;
    }
  ) {
    if (!s.fix) return;
    switch (s.fix.kind) {
      case "reconnect":
        return void sendInstallLink(ctx.domain!);
      case "resume_orders":
        return setReasoned({
          kind: "pause",
          shopId: ctx.shopId!,
          domain: ctx.domain!,
          paused: true,
        });
      case "repair_setup":
        return setReasoned({ kind: "repair", shopId: ctx.shopId!, domain: ctx.domain! });
      case "add_pickup":
        return router.push(`/merchants/${id}?tab=people&panel=locations`);
      case "review_failed_orders":
        return void loadDlq();
      case "backfill":
        return void run(async (t) => {
          const r = await merchantOps.backfill(t, id, ctx.shopId!);
          return `Pulled recent orders · ${r.accepted ?? 0} booked, ${r.rejected ?? 0} skipped`;
        });
      case "retry_failed":
        return void run(async (t) => {
          const r = await merchantOps.replayFailed(t, id, 24, ctx.hookId);
          return `Resent ${r.replayed} · ${r.succeeded} delivered, ${r.failed} still failing`;
        });
      case "turn_on":
        return void run(async (t) => {
          await merchants.enableWebhook(t, id, ctx.hookId!);
          return "Webhook turned back on";
        });
      case "rotate":
        return setReasoned({ kind: "rotate", keyId: ctx.keyId!, name: ctx.name! });
      case "retry_tracking":
        return void run(async (t) => {
          const ids =
            data?.shopify_shops?.find((x) => x.id === ctx.shopId)?.health
              ?.tracking_failing_orders ?? [];
          let ok = 0;
          for (const oid of ids) {
            const r = await ordersApi.shopifyRepushFulfillment(t, oid);
            if (r.ok) ok += 1;
          }
          return `Tracking resent for ${ok} of ${ids.length} orders`;
        });
    }
  }

  async function submitReasoned(reason: string) {
    const r = reasoned;
    if (!r) return;
    await run(async (t) => {
      switch (r.kind) {
        case "pause":
          const out = await merchants.shopifyIngressPause(t, id, r.shopId, !r.paused, reason);
          if (!r.paused) return "Orders paused";
          return out.released || out.release_failed
            ? `Orders resumed · ${out.released ?? 0} held orders booked, ${out.release_failed ?? 0} need review`
            : "Orders resumed";
        case "auto":
          await merchants.shopifyAutoDispatch(t, id, r.shopId, !r.on, reason);
          return r.on ? "Auto-dispatch off" : "Auto-dispatch on";
        case "repair": {
          const out = await merchants.shopifyReregisterHooks(t, id, r.shopId, reason);
          if (!out.ok) throw new Error(out.errors?.[0] || "repair_failed");
          return "Store setup repaired";
        }
        case "disconnect":
          await merchants.forceDisconnectShopify(t, id, r.shopId, reason);
          return `${r.domain} disconnected`;
        case "freeze": {
          const out = await merchants.freezePartnerApi(t, id, reason);
          return `Frozen · ${out.keys_revoked} keys revoked, ${out.webhooks_disabled} webhooks off`;
        }
        case "rotate": {
          const out = await merchantOps.rotateKey(t, id, r.keyId, 7, reason);
          setSecret(out.secret);
          return "New key issued";
        }
      }
    });
    setReasoned(null);
  }

  if (error) {
    return (
      <Panel>
        <Empty
          title="Couldn't load connections"
          hint={error}
          action={<QuietButton onClick={() => setVersion((v) => v + 1)}>Try again</QuietButton>}
        />
      </Panel>
    );
  }
  if (!data) {
    return (
      <Panel title="Connections">
        <SkeletonRows rows={4} label="Checking connections" />
      </Panel>
    );
  }

  const shops = data.shopify_shops ?? [];
  const keys = data.api_keys ?? [];
  const hooks = data.webhooks ?? [];
  const recent = data.recent_webhook_deliveries ?? [];
  const partner = data.shopify_partner;
  const throttled = new Set(
    (data.rate_limits ?? []).filter((r) => r.throttled).map((r) => r.api_key_id)
  );

  const shopRows = shops.map((s) => ({
    s,
    st: shopStatus(s, partner, watchById.get(`shopify:${s.id}`)),
  }));
  const keyRows = keys.map((k) => ({
    k,
    st: keyStatus(k, throttled.has(k.id), watchById.get(`api_key:${k.id}`)),
  }));
  const hookRows = hooks.map((h) => ({
    h,
    st: hookStatus(h, recent, watchById.get(`webhook:${h.id}`)),
  }));
  const all = [...shopRows, ...keyRows, ...hookRows]
    .map((r) => r.st)
    .filter((s) => s.light !== "off");
  const sum = summarize(all);

  const pageMenu: MenuItem[] = [
    ...(canMutate
      ? [{ label: "Copy install link for a new store", onSelect: () => setInstall({ shop: "" }) }]
      : []),
    ...(canImpersonate && seat
      ? [
          {
            label: `Open their portal as ${seat.role_label || "owner"}`,
            onSelect: () => setImpersonate(true),
          },
        ]
      : []),
    {
      label: "Merchant API docs",
      onSelect: () => window.open(`${portal}/api?tab=docs`, "_blank", "noopener"),
    },
    ...(canElevate && keys.some((k) => k.is_active)
      ? [
          {
            label: "Freeze all API access",
            tone: "danger" as const,
            onSelect: () => setReasoned({ kind: "freeze" }),
          },
        ]
      : []),
  ];
  const fixable = (s: Status) => !!s.fix && canMutate && (!s.fix.elevated || canElevate);
  // One accent button per screen: the first fixable problem, red before amber.
  const candidates = [
    ...shopRows.map((r) => ({ k: `shop:${r.s.id}`, st: r.st })),
    ...keyRows.map((r) => ({ k: `key:${r.k.id}`, st: r.st })),
    ...hookRows.map((r) => ({ k: `hook:${r.h.id}`, st: r.st })),
  ].filter((c) => fixable(c.st));
  const primaryKey = (candidates.find((c) => c.st.light === "red") ?? candidates[0])?.k;

  const reasonedCopy = reasoned ? REASONED_COPY[reasoned.kind](reasoned) : null;

  return (
    <div className="space-y-6">
      <Panel>
        <div className="flex flex-wrap items-center gap-4">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold tracking-[0.18em] text-secondary uppercase">
              Connections
            </p>
            <p className="mt-1 flex items-center gap-2.5 text-2xl font-extrabold tracking-tight text-primary sm:text-3xl">
              <span className={cn("h-3 w-3 rounded-full", DOT[sum.light])} aria-hidden />
              {sum.line}
            </p>
            <p className="mt-1 text-sm text-slate-600 tabular-nums">
              {[
                plural(shops.length, "Shopify store"),
                plural(keys.filter((k) => k.is_active).length, "API key"),
                plural(hooks.filter((h) => h.is_active).length, "webhook"),
              ].join(" · ")}
            </p>
          </div>
          <QuietButton square aria-label="Re-check" onClick={() => setVersion((v) => v + 1)}>
            <RefreshCw className="h-4 w-4" aria-hidden />
          </QuietButton>
          <ActionMenu label="Connection actions" items={pageMenu} />
        </div>
        {toast ? (
          <p
            role="status"
            className={cn(
              "mt-4 text-sm font-semibold",
              toast.bad ? "text-red-700" : "text-emerald-700"
            )}
          >
            {toast.text}
          </p>
        ) : null}
      </Panel>

      {!shops.length && !keys.length && !hooks.length ? (
        <Panel>
          <Empty
            icon={<PlugZap className="h-6 w-6" aria-hidden />}
            title="Nothing connected yet"
            hint="The merchant connects Shopify or creates API keys from their portal. You can send them a Shopify install link."
            action={
              canMutate ? (
                <PrimaryAction onClick={() => setInstall({ shop: "" })}>
                  Send Shopify install link
                </PrimaryAction>
              ) : undefined
            }
          />
        </Panel>
      ) : null}

      {shops.length > 0 && (
        <Group icon={<ShoppingBag className="h-4 w-4" aria-hidden />} title="Shopify">
          {shopRows.map(({ s, st }) => (
            <Row
              key={s.id}
              name={s.shop_domain}
              st={st}
              fix={
                fixable(st) ? (
                  <FixButton
                    primary={primaryKey === `shop:${s.id}`}
                    disabled={busy}
                    onClick={() =>
                      doFix(st, { shopId: s.id, domain: s.shop_domain, paused: s.ingress_paused })
                    }
                  >
                    {st.fix!.label}
                  </FixButton>
                ) : null
              }
              menu={[
                ...(canMutate && s.installed
                  ? [
                      {
                        label: "Pull recent orders",
                        onSelect: () =>
                          doFix({ ...st, fix: { kind: "backfill", label: "" } }, { shopId: s.id }),
                      },
                    ]
                  : []),
                ...(canMutate
                  ? [
                      {
                        label: "Copy reconnect link",
                        onSelect: () => void sendInstallLink(s.shop_domain),
                      },
                    ]
                  : []),
                ...(canElevate && s.installed
                  ? [
                      {
                        label: "Booking defaults…",
                        onSelect: () =>
                          setPolicy({
                            shopId: s.id,
                            domain: s.shop_domain,
                            vehicle: "",
                            pkg: "",
                            current: {
                              vehicle: s.default_vehicle_class,
                              pkg: s.default_package_type,
                            },
                          }),
                      },
                      {
                        label: s.auto_dispatch ? "Turn off auto-dispatch" : "Turn on auto-dispatch",
                        onSelect: () =>
                          setReasoned({
                            kind: "auto",
                            shopId: s.id,
                            domain: s.shop_domain,
                            on: !!s.auto_dispatch,
                          }),
                      },
                      {
                        label: "Repair store setup",
                        onSelect: () =>
                          setReasoned({ kind: "repair", shopId: s.id, domain: s.shop_domain }),
                      },
                      {
                        label: s.ingress_paused ? "Resume orders" : "Pause orders",
                        onSelect: () =>
                          setReasoned({
                            kind: "pause",
                            shopId: s.id,
                            domain: s.shop_domain,
                            paused: !!s.ingress_paused,
                          }),
                      },
                      {
                        label: "Disconnect store",
                        tone: "danger" as const,
                        onSelect: () =>
                          setReasoned({ kind: "disconnect", shopId: s.id, domain: s.shop_domain }),
                      },
                    ]
                  : []),
              ]}
              details={
                <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                  <Fact
                    label="Connected"
                    value={
                      s.installed
                        ? s.installed_at
                          ? new Date(s.installed_at).toLocaleDateString("en-CA")
                          : "Yes"
                        : "No"
                    }
                  />
                  <Fact label="Last order from Shopify" value={ago(s.last_webhook_at)} />
                  <Fact
                    label="Pickup address"
                    value={s.default_pickup ?? "Missing"}
                    bad={!s.default_pickup && s.installed}
                  />
                  <Fact
                    label="Checkout shipping rates"
                    value={
                      s.carrier_registered
                        ? `On · ${partner?.rate_quotes_24h ?? 0} quotes in 24 h`
                        : "Not set up"
                    }
                    bad={!s.carrier_registered && s.installed}
                  />
                  <Fact
                    label="Last checkout quote"
                    value={
                      partner?.last_rate_quote_at
                        ? `${cad(partner.last_rate_quote_cents)} · ${ago(partner.last_rate_quote_at)}`
                        : "None yet"
                    }
                  />
                  <Fact
                    label="Tracking sent to Shopify"
                    value={
                      partner?.mid_flight_tracking
                        ? `Yes · ${ago(partner.last_fulfillment?.last_tracking_push_at)}`
                        : "Not yet"
                    }
                  />
                  <Fact
                    label="Fulfilment service"
                    value={
                      s.fulfillment_service_registered
                        ? "On"
                        : partner?.fulfillment_service_enabled
                          ? "Not set up"
                          : "Not used"
                    }
                  />
                  <Fact
                    label="New orders"
                    value={s.ingress_paused ? "Paused" : "Flowing"}
                    bad={!!s.ingress_paused}
                  />
                  <Fact
                    label="Auto-dispatch"
                    value={s.auto_dispatch ? "On" : "Off — staff release orders"}
                  />
                  <Fact
                    label="Booking defaults"
                    value={
                      [
                        s.default_vehicle_class ? vehicleClassLabel(s.default_vehicle_class) : null,
                        s.default_package_type === "ltlPallet"
                          ? "Pallets"
                          : s.default_package_type
                            ? "Parcels"
                            : null,
                      ]
                        .filter(Boolean)
                        .join(" · ") || "Merchant settings"
                    }
                  />
                </dl>
              }
            />
          ))}
        </Group>
      )}

      {dlq ? (
        <Panel
          title="Orders that couldn't be booked"
          aside={<QuietButton onClick={() => setDlq(null)}>Close</QuietButton>}
        >
          {dlq.filter((r) => r.status !== "resolved").length === 0 ? (
            <Empty title="None waiting" hint="Every Shopify order made it through." />
          ) : (
            <ul className="-my-2 divide-y divide-primary/5">
              {dlq
                .filter((r) => r.status !== "resolved")
                .map((r) => (
                  <li key={r.id} className="flex items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-bold text-primary">
                        Shopify order {r.shopify_order_id ?? "—"}
                      </p>
                      <p className="truncate text-sm text-red-700">
                        {merchantActionMessage(r.detail || r.reason_code)}
                      </p>
                      <p className="text-xs text-slate-600">
                        {ago(r.created_at)} · tried {r.attempts}×
                      </p>
                    </div>
                    {canMutate ? (
                      <QuietButton
                        disabled={busy}
                        onClick={() =>
                          void run(async (t) => {
                            const out = (await merchants.shopifyIngressDlqReplay(t, id, r.id)) as {
                              ok?: boolean;
                              detail?: string;
                            };
                            setDlq((await merchants.shopifyIngressDlq(t, id)).items);
                            if (out.ok === false)
                              throw new Error(out.detail || "Still can't book it");
                            return "Order booked";
                          })
                        }
                      >
                        Try again
                      </QuietButton>
                    ) : null}
                  </li>
                ))}
            </ul>
          )}
        </Panel>
      ) : null}

      {keys.length > 0 && (
        <Group icon={<KeyRound className="h-4 w-4" aria-hidden />} title="API keys">
          {keyRows.map(({ k, st }) => (
            <Row
              key={k.id}
              name={`${k.name} · ${k.environment === "sandbox" ? "Test" : "Live"}`}
              st={st}
              fix={
                fixable(st) ? (
                  <FixButton
                    primary={primaryKey === `key:${k.id}`}
                    disabled={busy}
                    onClick={() => doFix(st, { keyId: k.id, name: k.name })}
                  >
                    {st.fix!.label}
                  </FixButton>
                ) : null
              }
              menu={
                st.light === "off"
                  ? []
                  : [
                      ...(canMutate
                        ? [
                            {
                              label: "Change rate limit…",
                              onSelect: () =>
                                setRate({ keyId: k.id, value: String(k.rate_limit_per_minute) }),
                            },
                          ]
                        : []),
                      ...(canElevate
                        ? [
                            {
                              label: "Replace key",
                              onSelect: () =>
                                setReasoned({ kind: "rotate", keyId: k.id, name: k.name }),
                            },
                          ]
                        : []),
                      ...(canMutate
                        ? [
                            {
                              label: "Revoke",
                              tone: "danger" as const,
                              onSelect: () =>
                                setConfirm({ kind: "revoke", keyId: k.id, name: k.name }),
                            },
                          ]
                        : []),
                    ]
              }
              details={
                <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                  <Fact label="Starts with" value={`${k.key_prefix}…`} />
                  <Fact label="Last call" value={ago(k.last_used_at)} />
                  <Fact label="Rate limit" value={`${k.rate_limit_per_minute} / min`} />
                  <Fact
                    label="Created"
                    value={k.created_at ? new Date(k.created_at).toLocaleDateString("en-CA") : "—"}
                  />
                  <Fact
                    label="Can do"
                    value={k.scopes.length ? k.scopes.join(", ") : "Everything"}
                  />
                </dl>
              }
            />
          ))}
        </Group>
      )}

      {hooks.length > 0 && (
        <Group
          icon={<Webhook className="h-4 w-4" aria-hidden />}
          title="Order updates to their system"
        >
          {hookRows.map(({ h, st }) => (
            <Row
              key={h.id}
              name={h.url.replace(/^https?:\/\//, "")}
              st={st}
              fix={
                fixable(st) ? (
                  <FixButton
                    primary={primaryKey === `hook:${h.id}`}
                    disabled={busy}
                    onClick={() => doFix(st, { hookId: h.id })}
                  >
                    {st.fix!.label}
                  </FixButton>
                ) : null
              }
              menu={[
                { label: "Delivery log", onSelect: () => void openLog(h.id) },
                ...(canMutate && h.is_active
                  ? [
                      {
                        label: "Send a test",
                        onSelect: () =>
                          void run(async (t) => {
                            const r = await merchants.testWebhook(t, id, h.id);
                            if (r && r.success === false)
                              throw new Error(
                                typeof r.error_message === "string"
                                  ? r.error_message
                                  : "Test didn't arrive"
                              );
                            return "Test delivered";
                          }),
                      },
                      {
                        label: "Turn off",
                        tone: "danger" as const,
                        onSelect: () => setConfirm({ kind: "hook_off", hookId: h.id, url: h.url }),
                      },
                    ]
                  : []),
              ]}
              details={
                <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                  <Fact label="Address" value={h.url} />
                  <Fact
                    label="Sends"
                    value={h.events.length ? h.events.join(", ") : "All events"}
                  />
                  <Fact label="Mode" value={h.environment === "sandbox" ? "Test" : "Live"} />
                  <Fact
                    label="Last attempt"
                    value={ago(recent.find((d) => d.webhook_id === h.id)?.created_at)}
                  />
                </dl>
              }
            />
          ))}
        </Group>
      )}

      {(data.audit_events ?? []).length > 0 && (
        <details className="group rounded-3xl border border-primary/10 bg-white">
          <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between px-5 text-base font-bold text-primary sm:px-6">
            Connection history
            <ChevronDown className="h-4 w-4 transition group-open:rotate-180" aria-hidden />
          </summary>
          <ol className="divide-y divide-primary/5 border-t border-primary/10 px-5 sm:px-6">
            {(data.audit_events ?? []).map((e) => (
              <li
                key={e.id}
                className="flex flex-wrap items-baseline justify-between gap-2 py-3 text-sm"
              >
                <span className="font-medium text-primary">{humanAction(e.action)}</span>
                <span className="text-xs text-slate-600">
                  {(e.payload?.admin_email as string) || e.actor_user_id || "system"} ·{" "}
                  {ago(e.created_at)}
                </span>
              </li>
            ))}
          </ol>
        </details>
      )}

      {/* Dialogs */}
      <ReasonDialog
        open={!!reasoned}
        title={reasonedCopy?.title ?? ""}
        description={reasonedCopy?.body}
        confirm={reasonedCopy?.cta ?? ""}
        tone={reasonedCopy?.danger ? "danger" : "default"}
        busy={busy}
        onCancel={() => setReasoned(null)}
        onConfirm={(r) => void submitReasoned(r)}
      />
      <Dialog
        open={!!confirm}
        onClose={() => setConfirm(null)}
        title={confirm?.kind === "revoke" ? `Revoke ${confirm.name}?` : "Turn off this webhook?"}
        description={
          confirm?.kind === "revoke"
            ? "Their system stops working with this key right away."
            : "We stop sending order updates to this address."
        }
        footer={
          <>
            <QuietButton onClick={() => setConfirm(null)}>Cancel</QuietButton>
            <PrimaryAction
              tone="danger"
              disabled={busy}
              onClick={() =>
                confirm &&
                void run(
                  async (t) => {
                    if (confirm.kind === "revoke") {
                      await merchants.revokeApiKey(t, id, confirm.keyId);
                      return "Key revoked";
                    }
                    await merchants.disableWebhook(t, id, confirm.hookId);
                    return "Webhook turned off";
                  },
                  () => setConfirm(null)
                )
              }
            >
              {confirm?.kind === "revoke" ? "Revoke" : "Turn off"}
            </PrimaryAction>
          </>
        }
      />
      <Dialog
        open={!!rate}
        onClose={() => setRate(null)}
        title="Rate limit"
        description="Calls per minute this key may make. 10 to 600."
        footer={
          <>
            <QuietButton onClick={() => setRate(null)}>Cancel</QuietButton>
            <PrimaryAction
              disabled={busy || !rate || !(Number(rate.value) >= 10 && Number(rate.value) <= 600)}
              onClick={() =>
                rate &&
                void run(
                  async (t) => {
                    await merchants.updateApiKeyRateLimit(
                      t,
                      id,
                      rate.keyId,
                      Math.round(Number(rate.value))
                    );
                    return "Rate limit saved";
                  },
                  () => setRate(null)
                )
              }
            >
              Save
            </PrimaryAction>
          </>
        }
      >
        <FieldLabel label="Per minute">
          <input
            className={inputClass}
            inputMode="numeric"
            value={rate?.value ?? ""}
            onChange={(e) =>
              rate && setRate({ ...rate, value: e.target.value.replace(/\D/g, "").slice(0, 3) })
            }
          />
        </FieldLabel>
      </Dialog>
      <Dialog
        open={!!policy}
        onClose={() => setPolicy(null)}
        title="Booking defaults"
        description={`Used when a ${policy?.domain ?? ""} order doesn't say which vehicle or package.`}
        footer={
          <>
            <QuietButton onClick={() => setPolicy(null)}>Cancel</QuietButton>
            <PrimaryAction
              disabled={busy || !policyReason.trim()}
              onClick={() =>
                policy &&
                void run(
                  async (t) => {
                    await merchants.shopifyBookingPolicy(
                      t,
                      id,
                      policy.shopId,
                      policyPayload(
                        policy.current,
                        { vehicle: policy.vehicle, pkg: policy.pkg },
                        policyReason.trim()
                      )
                    );
                    return "Booking defaults saved";
                  },
                  () => {
                    setPolicy(null);
                    setPolicyReason("");
                  }
                )
              }
            >
              Save
            </PrimaryAction>
          </>
        }
      >
        <FieldLabel label="Vehicle">
          <select
            className={inputClass}
            value={policy?.vehicle ?? ""}
            onChange={(e) => policy && setPolicy({ ...policy, vehicle: e.target.value })}
          >
            <option value="">
              Keep ·{" "}
              {policy?.current.vehicle
                ? vehicleClassLabel(policy.current.vehicle)
                : "merchant settings"}
            </option>
            {RETAIL_VEHICLE_OPTIONS.map((v) => (
              <option key={v} value={v}>
                {vehicleClassLabel(v)}
              </option>
            ))}
            <option value="none">Use merchant settings</option>
          </select>
        </FieldLabel>
        <FieldLabel label="Package">
          <select
            className={inputClass}
            value={policy?.pkg ?? ""}
            onChange={(e) => policy && setPolicy({ ...policy, pkg: e.target.value })}
          >
            <option value="">
              Keep ·{" "}
              {policy?.current.pkg === "ltlPallet"
                ? "Pallets"
                : policy?.current.pkg
                  ? "Parcels"
                  : "merchant settings"}
            </option>
            <option value="looseParcel">Parcels</option>
            <option value="ltlPallet">Pallets</option>
            <option value="none">Use merchant settings</option>
          </select>
        </FieldLabel>
        <FieldLabel label="Reason" hint="Saved to the change history.">
          <input
            className={inputClass}
            value={policyReason}
            maxLength={255}
            onChange={(e) => setPolicyReason(e.target.value)}
          />
        </FieldLabel>
      </Dialog>
      <Dialog
        open={!!install}
        onClose={() => setInstall(null)}
        title="Shopify install link"
        description="We copy a one-time link. Send it to the store owner; it connects their store to this merchant."
        footer={
          <>
            <QuietButton onClick={() => setInstall(null)}>Cancel</QuietButton>
            <PrimaryAction
              disabled={busy || !install?.shop.trim()}
              onClick={() => install && void sendInstallLink(install.shop)}
            >
              Copy link
            </PrimaryAction>
          </>
        }
      >
        <FieldLabel label="Store address" hint="Like their-store.myshopify.com">
          <input
            className={inputClass}
            value={install?.shop ?? ""}
            onChange={(e) => setInstall({ shop: e.target.value })}
            placeholder="their-store.myshopify.com"
          />
        </FieldLabel>
      </Dialog>
      <Dialog
        open={!!secret}
        onClose={() => setSecret(null)}
        title="New key — copy it now"
        description="Shown once and never stored. Send it to the merchant over a secure channel."
        footer={<PrimaryAction onClick={() => setSecret(null)}>Done</PrimaryAction>}
      >
        <code className="block rounded-2xl bg-primary px-4 py-3 font-mono text-xs break-all text-white">
          {secret}
        </code>
        <QuietButton onClick={() => secret && void copy(secret, "Key")}>Copy key</QuietButton>
      </Dialog>
      <Dialog
        open={!!log}
        onClose={() => setLog(null)}
        title="Delivery log"
        description="Last deliveries to this address."
      >
        {log && log.rows.length === 0 ? (
          <p className="text-sm text-slate-600">Nothing sent yet.</p>
        ) : (
          <ul className="-my-2 divide-y divide-primary/5">
            {(log?.rows ?? []).map((d) => (
              <li key={d.id} className="flex items-center gap-3 py-2.5 text-sm">
                <span
                  className={cn(
                    "h-2 w-2 shrink-0 rounded-full",
                    deliveryFailed(d) ? "bg-red-600" : "bg-emerald-600"
                  )}
                  aria-hidden
                />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium text-primary">
                    {d.event_type ?? "event"}
                  </span>
                  <span className="block truncate text-xs text-slate-600">
                    {deliveryFailed(d)
                      ? d.error_message ||
                        d.error ||
                        `Failed${d.response_status ? ` (${d.response_status})` : ""}`
                      : "Delivered"}{" "}
                    · {ago(d.created_at)}
                  </span>
                </span>
                {deliveryFailed(d) && canMutate ? (
                  <QuietButton
                    disabled={busy}
                    onClick={() =>
                      void run(async (t) => {
                        await merchants.retryWebhookDelivery(t, id, d.id);
                        setLog({
                          hookId: log!.hookId,
                          rows: await merchants.webhookDeliveries(t, id, log!.hookId),
                        });
                        return "Resent";
                      })
                    }
                  >
                    Resend
                  </QuietButton>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Dialog>
      {impersonate && seat ? (
        <ImpersonateModal
          open
          targetType="merchant"
          targetId={seat.id}
          targetLabel={seat.email}
          getApiToken={getApiToken}
          nextPath="/api?tab=keys"
          onClose={() => setImpersonate(false)}
        />
      ) : null}
    </div>
  );
}

function Group({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-primary/10 bg-white">
      <h3 className="flex items-center gap-2 px-5 pt-5 text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase sm:px-6">
        {icon}
        {title}
      </h3>
      <ul className="divide-y divide-primary/5 px-5 pb-2 sm:px-6">{children}</ul>
    </section>
  );
}

function Row({
  name,
  st,
  fix,
  menu,
  details,
}: {
  name: string;
  st: Status;
  fix: ReactNode;
  menu: MenuItem[];
  details: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <li className="py-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", DOT[st.light])} aria-hidden />
        <div className="min-w-0 flex-1 basis-48">
          <p className="truncate text-[15px] font-bold text-primary">{name}</p>
          <p
            className={cn(
              "text-sm",
              st.light === "red"
                ? "text-red-700"
                : st.light === "amber"
                  ? "text-amber-800"
                  : "text-slate-600"
            )}
          >
            <span className="sr-only">{WORD[st.light]}: </span>
            {st.reason}
            {st.more.length ? (
              <span className="text-slate-600"> · +{st.more.length} more</span>
            ) : null}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {fix}
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="inline-flex min-h-11 items-center gap-1 rounded-full px-3 text-sm font-semibold text-slate-600 hover:bg-slate-50 hover:text-primary"
          >
            Details{" "}
            <ChevronDown className={cn("h-4 w-4 transition", open && "rotate-180")} aria-hidden />
          </button>
          <ActionMenu label={`More for ${name}`} items={menu} />
        </div>
      </div>
      {open ? (
        <div className="mt-4 ml-5 space-y-3 rounded-2xl bg-slate-50 px-4 py-4">
          {st.more.length ? (
            <ul className="space-y-1 text-sm text-red-700">
              {st.more.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          ) : null}
          {details}
        </div>
      ) : null}
    </li>
  );
}

function FixButton({
  primary,
  children,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { primary: boolean }) {
  return primary ? (
    <PrimaryAction {...rest}>{children}</PrimaryAction>
  ) : (
    <QuietButton {...rest}>{children}</QuietButton>
  );
}

function Fact({ label, value, bad }: { label: string; value: string; bad?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-slate-600">{label}</dt>
      <dd className={cn("font-medium break-words", bad ? "text-red-700" : "text-primary")}>
        {value}
      </dd>
    </div>
  );
}

const ACTION_WORDS: Record<string, string> = {
  "api_key.revoked": "API key revoked",
  "api_key.rotated": "API key replaced",
  "api_key.rate_limit_changed": "API key rate limit changed",
  "webhook.disabled": "Webhook turned off",
  "webhook.enabled": "Webhook turned on",
  "webhook.test": "Webhook test sent",
  "partner_api.frozen": "All API access frozen",
  "shopify.force_disconnected": "Shopify store disconnected",
  "shopify.install_url_copied": "Shopify install link copied",
  "shopify.webhook_replayed": "Shopify order retried",
  "shopify.disconnected": "Merchant disconnected their store",
  "shopify.ingress_paused": "Shopify orders paused",
  "shopify.ingress_resumed": "Shopify orders resumed",
};
function humanAction(a: string): string {
  return ACTION_WORDS[a] ?? a.replace(/[._]/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}
