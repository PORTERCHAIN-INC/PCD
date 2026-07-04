"use client";

import { useState } from "react";
import {
  Activity as ActivityIcon,
  Mail,
  MessageSquare,
  Phone,
  RefreshCw,
  Users,
  FileText,
} from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { crm } from "@/lib/crm";
import { SectionCard, Select, Spinner } from "@/components/crm/primitives";
import { dateTime, titleCase } from "@/lib/crmFormat";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  note: MessageSquare,
  call: Phone,
  email: Mail,
  meeting: Users,
  site_visit: Users,
  demo: Users,
  document: FileText,
  status_change: RefreshCw,
  system: ActivityIcon,
};

export default function ActivitiesPage() {
  const [type, setType] = useState("");
  const { data, error } = useApiData((t) => crm.activities(t, { limit: "200" }), [], { key: "crm-activities" });

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <Spinner label="Loading activity…" />;

  const filtered = type ? data.filter((a) => a.activity_type === type) : data;

  return (
    <SectionCard
      title="Activity feed"
      action={
        <Select value={type} onChange={(e) => setType(e.target.value)} className="w-40">
          <option value="">All types</option>
          {[
            "note",
            "call",
            "email",
            "meeting",
            "site_visit",
            "demo",
            "status_change",
            "system",
          ].map((t) => (
            <option key={t} value={t}>
              {titleCase(t)}
            </option>
          ))}
        </Select>
      }
    >
      <div className="divide-y divide-primary/5">
        {filtered.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-muted">No activity recorded.</p>
        )}
        {filtered.map((a) => {
          const Icon = ICONS[a.activity_type] ?? ActivityIcon;
          return (
            <div key={a.id} className="flex gap-3 px-5 py-3.5">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary/10 text-secondary">
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-primary">
                  {a.subject ?? a.body ?? titleCase(a.activity_type)}
                </p>
                {a.subject && a.body && <p className="text-sm text-muted">{a.body}</p>}
                <p className="text-xs text-muted">
                  {titleCase(a.entity_type)} · {titleCase(a.activity_type)} ·{" "}
                  {dateTime(a.occurred_at)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}
