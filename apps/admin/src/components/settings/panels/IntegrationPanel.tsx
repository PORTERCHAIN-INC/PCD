"use client";

import { ExternalLink, Lock } from "lucide-react";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { SettingsCard, SettingsPageHeader, StatusPill } from "../ui/SettingsPrimitives";

const INTEGRATION_DOCS: Record<string, string[]> = {
  fleetbase: [
    "All Fleetbase calls go through the adapter — never direct HTTP from UI or routers.",
    "Dispatch bridge must be enabled with a valid API key in production.",
    "Fleetbase handles execution only: GPS, routes, POD — not CRM or billing.",
  ],
  stripe: [
    "Stripe Checkout for retail; invoicing for merchants per masterrule §14.",
    "Webhook secrets verified server-side — never exposed in admin UI.",
    "Mock mode available for local development only.",
  ],
  google_maps: [
    "Server-side geocoding and distance matrix.",
    "Routing engine selection (OSRM / Valhalla) configured via env.",
  ],
  clerk: [
    "Clerk authenticates only — Porterchain owns RBAC.",
    "Staff, merchant, and driver access require DB provisioning.",
    "Never rely on Clerk Organizations for authorization.",
  ],
};

export default function IntegrationPanel({
  sectionId,
  data,
}: {
  sectionId: string;
  data: unknown;
}) {
  const title = sectionId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const description = SECTION_DESCRIPTIONS[sectionId] ?? "Integration status — credentials in environment.";
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

  return (
    <div className="space-y-6">
      <SettingsPageHeader title={title} description={description} />

      <div className="flex flex-wrap items-center gap-3">
        <StatusPill status={status} />
        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          <Lock className="h-3.5 w-3.5" />
          Env-managed credentials
        </span>
      </div>

      <SettingsCard title="Connection details" description="Non-sensitive configuration visible to operators">
        {details.length ? (
          <dl className="grid gap-3 sm:grid-cols-2">
            {details.map(([key, val]) => (
              <div key={key} className="rounded-xl bg-gray-bg/50 px-3 py-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-muted">{key.replace(/_/g, " ")}</dt>
                <dd className="mt-0.5 font-mono text-sm text-primary">{String(val ?? "—")}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-sm text-muted">No additional metadata available.</p>
        )}
      </SettingsCard>

      <SettingsCard title="Architecture notes" description="masterrule compliance">
        <ul className="space-y-2 text-sm text-primary/80">
          {bullets.map((b) => (
            <li key={b} className="flex gap-2">
              <span className="text-secondary">•</span>
              {b}
            </li>
          ))}
        </ul>
      </SettingsCard>

      {sectionId === "fleetbase" && (
        <a
          href="/operations"
          className="inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline"
        >
          Open Operations control tower <ExternalLink className="h-4 w-4" />
        </a>
      )}
    </div>
  );
}
