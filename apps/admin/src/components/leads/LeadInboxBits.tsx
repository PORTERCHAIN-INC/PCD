"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/crm/primitives";
import { formatSla, slaMinutesLeft } from "@/lib/leads";
import type { Lead } from "@/lib/crm";

/** Channel → short label + tone for the inbox badge. */
export const CHANNEL_BADGES: Record<string, { label: string; tone: string }> = {
  website: { label: "Web form", tone: "blue" },
  capacity_guide: { label: "Guide chat", tone: "sky" },
  website_booking: { label: "Booking", tone: "violet" },
  whatsapp: { label: "WhatsApp", tone: "green" },
  email: { label: "Email", tone: "sky" },
  phone_call: { label: "Call", tone: "amber" },
  sms: { label: "SMS", tone: "amber" },
  facebook: { label: "Facebook", tone: "blue" },
  instagram: { label: "Instagram", tone: "violet" },
  linkedin: { label: "LinkedIn", tone: "blue" },
  google_ads: { label: "Google Ads", tone: "teal" },
  google_business_profile: { label: "Google Profile", tone: "teal" },
  app_install: { label: "Store app install", tone: "green" },
  merchant_signup: { label: "Portal sign-up", tone: "teal" },
  driver_signup: { label: "Driver sign-up", tone: "amber" },
  merchant_referral: { label: "Referral", tone: "teal" },
  manual: { label: "Manual", tone: "slate" },
};

export function ChannelBadge({ channel }: { channel?: string | null }) {
  const key = channel || "other";
  const spec = CHANNEL_BADGES[key] ?? { label: key.replace(/_/g, " "), tone: "slate" };
  return (
    <Badge tone={spec.tone} className="whitespace-nowrap">
      {spec.label}
    </Badge>
  );
}

/** Re-render every 30 s so countdowns stay honest without refetching. */
export function useNow(intervalMs = 30_000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

/** SLA first-response countdown — only while nobody has replied yet. */
export function SlaCountdown({ lead, now }: { lead: Lead; now: number }) {
  if (lead.first_response_at || ["won", "archived", "lost"].includes(lead.status)) {
    return null;
  }
  const mins = slaMinutesLeft(lead, now);
  if (mins == null) return null;
  const tone = mins < 0 ? "red" : mins <= 15 ? "amber" : "slate";
  return (
    <Badge tone={tone} className="whitespace-nowrap tabular-nums">
      SLA {formatSla(mins)}
    </Badge>
  );
}

export function AwaitingReplyBadge({ lead }: { lead: Lead }) {
  if (!lead.awaiting_reply) return null;
  return (
    <Badge tone="red" className="whitespace-nowrap">
      Awaiting reply
    </Badge>
  );
}
