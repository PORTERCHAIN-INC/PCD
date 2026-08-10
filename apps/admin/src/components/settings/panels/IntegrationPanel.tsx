"use client";

import { ExternalLink, Lock, Settings2 } from "lucide-react";
import OpenFleetbaseButton from "@/components/nav/OpenFleetbaseButton";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import {
  BindingBadge,
  SettingsCard,
  SettingsPageHeader,
  StatusPill,
} from "../ui/SettingsPrimitives";

const INTEGRATION_DOCS: Record<string, string[]> = {
  fleetbase: [
    "Sign in once on PorterChain Admin (staff IdP) — open Fleetbase via SSO (no second password).",
    "All Fleetbase calls go through the adapter — never direct HTTP from UI or routers.",
    "Fleetbase is execution only: GPS, routes, POD — not CRM, billing, or staff identity.",
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
    "SMS phone verification is handled by Clerk.",
    "Push uses Firebase when configured. Template ops live under Notifications.",
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

type Action = { label: string; href?: string; external?: boolean; fleetbase?: boolean };

const ACTIONS: Record<string, Action[]> = {
  fleetbase: [
    { label: "Open Fleetbase console", fleetbase: true },
    { label: "Operations control tower", href: "/operations" },
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
    { label: "Notification templates", href: "/notifications" },
    { label: "Mailpit (local email)", href: "http://localhost:8025", external: true },
  ],
  storage: [{ label: "System health", href: "/system" }],
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

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title={title}
        description={description}
        actions={<BindingBadge effect="env" />}
      />

      <div className="flex flex-wrap items-center gap-3">
        <StatusPill status={status} />
        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          <Lock className="h-3.5 w-3.5" />
          Secrets in Doppler / env — not editable here
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

      {actions.length > 0 && (
        <SettingsCard title="Actions" description="Configure or operate this connection">
          <div className="flex flex-wrap gap-3">
            {actions.map((a) =>
              a.fleetbase ? (
                <OpenFleetbaseButton key={a.label} variant="toolbar" />
              ) : (
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
              )
            )}
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
