"use client";

import { ExternalLink, Lock, Settings2 } from "lucide-react";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import {
  BindingBadge,
  SettingsCard,
  SettingsPageHeader,
  StatusPill,
} from "../ui/SettingsPrimitives";

/** Locked staff-push alert budget — must match notification_engine/event_router.py. */
const STAFF_PUSH_ALERT_BUDGET = [
  { event: "sla_breached", priority: "critical", note: "SLA breach" },
  { event: "driver_alert (emergency)", priority: "critical", note: "Driver emergency / security" },
  { event: "exception_opened", priority: "high", note: "Ops exception opened" },
  { event: "order_delayed", priority: "high", note: "Order delay" },
  { event: "driver_rejected", priority: "high", note: "Driver rejected assignment" },
  { event: "temp_excursion", priority: "high", note: "Cold-chain / temp excursion" },
  { event: "driver_alert (support)", priority: "high", note: "Driver support escalation" },
] as const;

const INTEGRATION_DOCS: Record<string, string[]> = {
  dispatch: [
    "Dispatch is the PorterChain day plan.",
    "Dispatch stays in PorterChain. The browser does not call a second system.",
    "PorterChain runs GPS, routes, and proof. CRM, billing, and staff identity stay separate.",
  ],
  stripe: [
    "Stripe Checkout for retail; invoicing for merchants.",
    "Webhook secrets verified server-side — never exposed in admin UI.",
    "API keys live in Doppler / env — change them there, then restart API.",
  ],
  google_maps: [
    "Browser map tiles and Places autocomplete only — not a routing engine.",
    "Routing runs on Valhalla (primary) with OSRM fallback, configured via env.",
    "Browser key: NEXT_PUBLIC_GOOGLE_MAPS_API_KEY · server key in API env.",
  ],
  channels: [
    "Email uses SMTP from environment (Mailpit in local dev).",
    "Staff push uses FCM with OS priority for critical/high only — see alert budget below.",
    "Quiet hours never mute critical/high or security. Staff cannot mute those categories.",
    "SMS transactional copy still goes through Clerk where applicable; ops SMS remains optional.",
  ],
  firebase: [
    "FCM credentials are env-managed (service account / project id).",
    "Configure in Doppler, then restart worker/API for push delivery.",
  ],
  storage: [
    "Document/media storage is deployment volume or object-store env config.",
    "No secrets are editable from this UI.",
  ],
};

type Action = { label: string; href?: string; external?: boolean };

const ACTIONS: Record<string, Action[]> = {
  dispatch: [
    { label: "Operations control tower", href: "/operations" },
    { label: "System", href: "/system" },
  ],
  stripe: [
    { label: "Stripe Dashboard", href: "https://dashboard.stripe.com", external: true },
    { label: "Env / secrets map", href: "/settings?section=backup" },
  ],
  google_maps: [
    {
      label: "Google Cloud Console",
      href: "https://console.cloud.google.com/google/maps-apis",
      external: true,
    },
  ],
  firebase: [
    { label: "Firebase Console", href: "https://console.firebase.google.com", external: true },
  ],
  channels: [
    { label: "Notification center", href: "/notifications" },
    { label: "Register this browser for push", href: "/notifications" },
    { label: "Mailpit (local email)", href: "http://localhost:8025", external: true },
  ],
  storage: [{ label: "System", href: "/system" }],
};

export default function IntegrationPanel({
  sectionId,
  data,
}: {
  sectionId: string;
  data: unknown;
}) {
  const title = sectionId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const description =
    SECTION_DESCRIPTIONS[sectionId] ?? "Integration status — credentials in environment.";
  const status =
    typeof data === "object" && data !== null && "status" in data
      ? String((data as { status: unknown }).status)
      : String(data ?? "unknown");
  const details =
    typeof data === "object" && data !== null
      ? Object.entries(data as Record<string, unknown>).filter(([k]) => k !== "status")
      : [];
  const bullets = INTEGRATION_DOCS[sectionId] ?? [
    "Credentials configured via environment variables.",
    "Connection status shown here — secrets never displayed.",
  ];
  const actions = ACTIONS[sectionId] ?? [];
  const badgeEffect = sectionId === "channels" ? "status" : "env";

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title={title}
        description={description}
        actions={<BindingBadge effect={badgeEffect} />}
      />

      <div className="flex flex-wrap items-center gap-3">
        <StatusPill status={status} />
        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          <Lock className="h-3.5 w-3.5" />
          {sectionId === "channels"
            ? "Alert budget locked in code — FCM secrets in Doppler"
            : "Secrets in Doppler / env — not editable here"}
        </span>
      </div>

      <SettingsCard
        title="Why can’t I edit keys here?"
        description="Silicon Valley security practice"
      >
        <p className="text-sm text-primary/80">
          API keys, webhook secrets, and SMTP passwords must never live in the admin database or
          browser. They are set in <strong>Doppler / environment variables</strong>, then the API
          reports health on this page. Use the actions below to open the right console or ops
          surface.
        </p>
      </SettingsCard>

      {sectionId === "channels" && (
        <SettingsCard
          title="Staff push alert budget"
          description="Jeff Dean bar — loud only for irreversible ops risk. Inbox for everything else."
        >
          <ul className="divide-y divide-primary/10 rounded-xl border border-primary/10">
            {STAFF_PUSH_ALERT_BUDGET.map((row) => (
              <li
                key={row.event}
                className="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5 text-sm"
              >
                <div>
                  <p className="font-mono text-xs font-semibold text-primary">{row.event}</p>
                  <p className="text-xs text-muted">{row.note}</p>
                </div>
                <span
                  className={
                    row.priority === "critical"
                      ? "rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-red-800 ring-1 ring-inset ring-red-600/20"
                      : "rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-900 ring-1 ring-inset ring-amber-600/20"
                  }
                >
                  {row.priority}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-muted">
            Source of truth: <code className="font-mono">event_router.py</code> staff push routes.
            Changing the budget is a code change, not a Settings form — on purpose.
          </p>
        </SettingsCard>
      )}

      {actions.length > 0 && (
        <SettingsCard title="Actions" description="Configure or operate this connection">
          <div className="flex flex-wrap gap-3">
            {actions.map((a) => (
              <a
                key={a.label}
                href={a.href}
                target={a.external ? "_blank" : undefined}
                rel={a.external ? "noreferrer" : undefined}
                className="inline-flex items-center gap-2 rounded-xl border border-secondary/30 bg-secondary/5 px-4 py-2.5 text-sm font-semibold text-secondary transition-colors hover:bg-secondary/10"
              >
                <Settings2 className="h-4 w-4" />
                {a.label}
                {a.external && <ExternalLink className="h-3.5 w-3.5" />}
              </a>
            ))}
          </div>
        </SettingsCard>
      )}

      <SettingsCard
        title="Connection details"
        description="Non-sensitive configuration visible to operators"
      >
        {details.length ? (
          <dl className="grid gap-3 sm:grid-cols-2">
            {details.map(([key, val]) => (
              <div key={key} className="rounded-xl bg-gray-bg/50 px-3 py-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-muted">
                  {key.replace(/_/g, " ")}
                </dt>
                <dd className="mt-0.5 font-mono text-sm text-primary">{String(val ?? "—")}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-sm text-muted">No additional metadata available.</p>
        )}
      </SettingsCard>

      <SettingsCard title="Architecture notes">
        <ul className="space-y-2 text-sm text-primary/80">
          {bullets.map((b) => (
            <li key={b} className="flex gap-2">
              <span className="text-secondary">•</span>
              {b}
            </li>
          ))}
        </ul>
      </SettingsCard>
    </div>
  );
}
