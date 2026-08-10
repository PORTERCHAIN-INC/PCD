"use client";

import { ExternalLink, Lock } from "lucide-react";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { BindingBadge, SettingsCard, SettingsPageHeader } from "../ui/SettingsPrimitives";

const COPY: Record<
  string,
  { title: string; bullets: string[]; href?: string; hrefLabel?: string }
> = {
  authentication: {
    title: "Authentication",
    bullets: [
      "Staff MFA, sessions, and allowed domains are managed in Clerk (staff IdP).",
      "PorterChain does not store parallel MFA toggles in SystemConfig.",
      "Driver / merchant / customer portals each use their Clerk application.",
    ],
    href: "https://dashboard.clerk.com",
    hrefLabel: "Open Clerk Dashboard",
  },
  security: {
    title: "Security",
    bullets: [
      "API rate limits use environment settings (Doppler), not this form.",
      "Password and lockout policy are enforced by Clerk.",
      "IP allow lists for production belong in the reverse proxy / WAF.",
    ],
  },
};

export default function EnvOwnedPanel({ sectionId }: { sectionId: string }) {
  const meta = COPY[sectionId] ?? {
    title: sectionId,
    bullets: [SECTION_DESCRIPTIONS[sectionId] ?? "Managed outside Settings."],
  };

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title={meta.title}
        description={SECTION_DESCRIPTIONS[sectionId]}
        actions={<BindingBadge effect="env" />}
      />
      <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
        <Lock className="h-3.5 w-3.5" />
        Not editable here — avoids false compliance controls
      </div>
      <SettingsCard title="Where to configure">
        <ul className="space-y-2 text-sm text-primary/80">
          {meta.bullets.map((b) => (
            <li key={b} className="flex gap-2">
              <span className="text-secondary">•</span>
              {b}
            </li>
          ))}
        </ul>
        {meta.href && (
          <a
            href={meta.href}
            target="_blank"
            rel="noreferrer"
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-secondary"
          >
            {meta.hrefLabel} <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </SettingsCard>
    </div>
  );
}
