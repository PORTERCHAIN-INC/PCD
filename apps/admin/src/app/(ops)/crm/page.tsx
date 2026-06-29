"use client";

import Link from "next/link";
import {
  AlarmClock,
  CalendarClock,
  CheckCircle2,
  FileSignature,
  FileText,
  Gauge,
  TrendingUp,
  Trophy,
  UserPlus,
} from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { crm } from "@/lib/crm";
import { SectionCard, Spinner } from "@/components/crm/primitives";
import { STAGE_ACCENT, STAGE_LABELS, money, titleCase, relativeTime } from "@/lib/crmFormat";

function Tile({
  label,
  value,
  icon: Icon,
  href,
  accent = "text-secondary",
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  href?: string;
  accent?: string;
}) {
  const body = (
    <div className="rounded-2xl border border-primary/10 bg-white p-4 transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted">{label}</p>
        <Icon className={`h-4 w-4 ${accent}`} />
      </div>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
    </div>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

export default function CrmDashboardPage() {
  const { data, error } = useApiData((t) => crm.dashboard(t));

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <Spinner label="Loading CRM dashboard…" />;

  const maxStage = Math.max(1, ...data.pipeline_by_stage.map((s) => s.value_cents));

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="New Leads" value={String(data.new_leads)} icon={UserPlus} href="/crm/leads" />
        <Tile
          label="Today's Follow-ups"
          value={String(data.todays_follow_ups)}
          icon={CalendarClock}
          href="/crm/tasks"
        />
        <Tile
          label="Overdue Tasks"
          value={String(data.overdue_tasks)}
          icon={AlarmClock}
          accent="text-red-500"
          href="/crm/tasks"
        />
        <Tile
          label="Meetings Today"
          value={String(data.meetings_today)}
          icon={CalendarClock}
          href="/crm/calendar"
        />
        <Tile
          label="Quotes Pending"
          value={String(data.quotes_pending)}
          icon={FileText}
          href="/crm/quotations"
        />
        <Tile
          label="Contracts Pending"
          value={String(data.contracts_pending)}
          icon={FileSignature}
          href="/crm/contracts"
        />
        <Tile
          label="Merchant Conversions"
          value={String(data.merchant_conversions)}
          icon={CheckCircle2}
          accent="text-green-600"
          href="/crm/companies"
        />
        <Tile
          label="Won This Month"
          value={String(data.won_deals_this_month)}
          icon={Trophy}
          accent="text-green-600"
          href="/crm/deals"
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Tile label="Pipeline Value" value={money(data.pipeline_value_cents)} icon={Gauge} />
        <Tile
          label="Monthly Revenue Forecast"
          value={money(data.monthly_revenue_forecast_cents)}
          icon={TrendingUp}
          accent="text-green-600"
        />
        <Tile
          label="Open Deals"
          value={String(data.open_deals)}
          icon={TrendingUp}
          href="/crm/deals"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <SectionCard title="Pipeline by stage" className="lg:col-span-2">
          <div className="space-y-3 p-5">
            {data.pipeline_by_stage.map((s) => (
              <div key={s.stage}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="font-medium text-primary">
                    {STAGE_LABELS[s.stage] ?? titleCase(s.stage)}{" "}
                    <span className="text-muted">· {s.count}</span>
                  </span>
                  <span className="font-semibold text-primary">{money(s.value_cents)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-gray-bg">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(s.value_cents / maxStage) * 100}%`,
                      background: STAGE_ACCENT[s.stage] ?? "#2563eb",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Recent activity">
          <div className="divide-y divide-primary/5">
            {data.recent_activities.length === 0 && (
              <p className="px-5 py-8 text-center text-sm text-muted">No activity yet</p>
            )}
            {data.recent_activities.map((a) => (
              <div key={String(a.id)} className="px-5 py-3">
                <p className="text-sm text-primary">
                  {String(a.subject ?? titleCase(String(a.activity_type)))}
                </p>
                <p className="text-xs text-muted">
                  {titleCase(String(a.entity_type))} · {relativeTime(String(a.occurred_at))}
                </p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Lead sources">
          <div className="divide-y divide-primary/5">
            {data.lead_sources.length === 0 && (
              <p className="px-5 py-8 text-center text-sm text-muted">No leads yet</p>
            )}
            {data.lead_sources.map((s) => (
              <div key={s.source} className="flex items-center justify-between px-5 py-3 text-sm">
                <span className="text-primary">{titleCase(s.source)}</span>
                <span className="font-semibold text-primary">{s.count}</span>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Top sales representatives">
          <div className="divide-y divide-primary/5">
            {data.top_sales_reps.length === 0 && (
              <p className="px-5 py-8 text-center text-sm text-muted">No closed deals yet</p>
            )}
            {data.top_sales_reps.map((rep) => (
              <div
                key={rep.owner_id}
                className="flex items-center justify-between px-5 py-3 text-sm"
              >
                <span className="text-primary">
                  {rep.owner_id === "unassigned" ? "Unassigned" : rep.owner_id.slice(0, 8)}
                </span>
                <span className="text-muted">
                  {rep.won_deals} won ·{" "}
                  <span className="font-semibold text-primary">{money(rep.revenue_cents)}</span>
                </span>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
