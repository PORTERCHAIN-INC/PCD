"use client";

import Link from "next/link";
import {
  Building2,
  Globe,
  Mail,
  Megaphone,
  MessageCircle,
  Phone,
  ShoppingBag,
  Truck,
  UserPlus,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import type { Lead } from "@/lib/crm";
import { CHANNEL_BADGES } from "@/components/leads/LeadInboxBits";

const CHANNEL_ICONS: Record<string, LucideIcon> = {
  website: Globe,
  capacity_guide: Globe,
  website_booking: Globe,
  whatsapp: MessageCircle,
  sms: MessageCircle,
  email: Mail,
  phone_call: Phone,
  app_install: ShoppingBag,
  merchant_signup: Building2,
  driver_signup: Truck,
  merchant_referral: UserPlus,
  google_ads: Megaphone,
  facebook: Megaphone,
  instagram: Megaphone,
  linkedin: Megaphone,
};

export const TARGET_MINUTES = 5;

/** Minutes the lead has been waiting on us (null when nobody is waiting). */
export function waitingMinutes(lead: Lead, now: number): number | null {
  if (["won", "lost", "archived"].includes(lead.status)) return null;
  const since = lead.awaiting_reply
    ? (lead.last_inbound_at ?? lead.created_at)
    : !lead.first_response_at && lead.status === "new"
      ? lead.created_at
      : null;
  if (!since) return null;
  const t = Date.parse(since);
  return Number.isFinite(t) ? Math.max(0, Math.floor((now - t) / 60_000)) : null;
}

export function formatDuration(mins: number): string {
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  if (h < 48) return `${h}h ${mins % 60}m`;
  return `${Math.floor(h / 24)}d`;
}

function ago(iso: string, now: number): string {
  const m = Math.max(0, Math.floor((now - Date.parse(iso)) / 60_000));
  return m < 60 ? `${m}m ago` : m < 2880 ? `${Math.floor(m / 60)}h ago` : `${Math.floor(m / 1440)}d ago`;
}

export function scoreTone(score: number): string {
  return score >= 70 ? "text-emerald-700" : score >= 40 ? "text-secondary" : "text-slate-500";
}

const STATUS_STYLE: Record<string, string> = {
  new: "bg-sky-50 text-sky-800",
  replied: "bg-slate-100 text-slate-700",
  quoted: "bg-violet-50 text-violet-800",
  won: "bg-emerald-50 text-emerald-800",
  lost: "bg-slate-100 text-slate-600",
  archived: "bg-slate-100 text-slate-600",
};

export function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize",
        STATUS_STYLE[status] ?? STATUS_STYLE.replied
      )}
    >
      {status}
    </span>
  );
}

export function ChannelIcon({ channel }: { channel?: string | null }) {
  const key = channel || "other";
  const Icon = CHANNEL_ICONS[key] ?? Globe;
  const label = CHANNEL_BADGES[key]?.label ?? key.replace(/_/g, " ");
  return (
    <span
      className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-primary"
      title={label}
    >
      <Icon className="h-4 w-4" aria-hidden />
      <span className="sr-only">{label}</span>
    </span>
  );
}

/** One inbox row — identical on desktop and phone. */
export default function LeadRow({
  lead,
  now,
  active,
  selected,
  onToggle,
}: {
  lead: Lead;
  now: number;
  active: boolean;
  selected: boolean;
  onToggle: () => void;
}) {
  const wait = waitingMinutes(lead, now);
  const late = wait != null && wait > TARGET_MINUTES;
  const person = lead.primary_contact_name?.trim();
  return (
    <li
      className={cn(
        "flex items-center gap-3 py-3.5 sm:gap-4",
        active && "-mx-3 rounded-2xl bg-secondary/5 px-3",
        selected && "-mx-3 rounded-2xl bg-secondary/10 px-3"
      )}
    >
      <input
        type="checkbox"
        className="hidden h-4 w-4 shrink-0 md:block"
        aria-label={`Select ${lead.company_name}`}
        checked={selected}
        onChange={onToggle}
      />
      <ChannelIcon channel={lead.channel ?? lead.source} />
      <Link href={`/leads/${lead.id}`} className="group min-w-0 flex-1">
        <span className="block truncate text-[15px] font-bold text-primary group-hover:text-secondary">
          {person || lead.company_name}
        </span>
        <span className="block truncate text-sm text-slate-600">
          {person && lead.company_name && lead.company_name.trim() !== person
            ? lead.company_name
            : (lead.email ?? lead.phone ?? "")}
        </span>
      </Link>
      <div className="hidden w-20 shrink-0 sm:block">
        <StatusPill status={lead.status} />
      </div>
      <div className="w-16 shrink-0 text-right sm:w-24">
        {wait != null ? (
          <span
            className={cn("text-sm font-semibold tabular-nums", late ? "text-red-700" : "text-slate-600")}
            title={late ? "Over the 5-minute reply target" : "Waiting on us"}
          >
            {formatDuration(wait)}
          </span>
        ) : (
          <span className="text-xs text-slate-500">{ago(lead.created_at, now)}</span>
        )}
      </div>
      <span
        className={cn("w-10 shrink-0 text-right text-2xl font-extrabold tabular-nums", scoreTone(lead.lead_score))}
        title="Fit score"
      >
        {lead.lead_score}
      </span>
    </li>
  );
}
