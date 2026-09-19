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
      "Admin staff use PorterChain’s first-party IdP: email magic link + WebAuthn passkeys (HttpOnly session).",
      "Staff MFA toggles and session TTL are not stored in SystemConfig — enroll or manage seats under Users → Staff.",
      "Driver, merchant, and customer portals each use their own Clerk application (Bearer JWT).",
      "Clerk staff JWT is retired for Admin API — do not point ops at Clerk for staff MFA.",
    ],
    href: "/settings?section=users",
    hrefLabel: "Open Users → Staff",
  },
  security: {
    title: "Security",
    bullets: [
      "Project mode (development / testing / production) is boot-time APP_ENV — change with pnpm mode:set or Doppler, then restart. Not editable here.",
      "API rate limits use environment settings (Doppler), not this form.",
      "Staff session lifetime and idle logout are enforced by the staff IdP / Redis session store.",
      "Driver / merchant / customer password and lockout policy are enforced by their Clerk apps.",
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
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-secondary"
          >
            {meta.hrefLabel} <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </SettingsCard>
    </div>
  );
}
