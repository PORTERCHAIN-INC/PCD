"use client";

import { useState } from "react";
import {
  MessageSquarePlus,
  Phone,
  Mail,
  Users,
  FileText,
  Activity as ActivityIcon,
  RefreshCw,
} from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm } from "@/lib/crm";
import { Button, Input, Select } from "@/components/crm/primitives";
import { relativeTime, titleCase } from "@/lib/crmFormat";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  note: MessageSquarePlus,
  call: Phone,
  email: Mail,
  meeting: Users,
  site_visit: Users,
  demo: Users,
  document: FileText,
  status_change: RefreshCw,
  system: ActivityIcon,
};

const TYPES = ["note", "call", "email", "meeting", "site_visit", "demo"];

export function ActivityTimeline({
  entityType,
  entityId,
}: {
  entityType: string;
  entityId: string;
}) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const [type, setType] = useState("note");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);

  const { data } = useApiData(
    (t) => crm.activities(t, { entity_type: entityType, entity_id: entityId }),
    [entityType, entityId, version],
    { key: `${entityType}-${entityId}-activities` }
  );

  const activities = Array.isArray(data) ? data : [];

  async function add() {
    if (!body.trim()) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createActivity(token, {
        entity_type: entityType,
        entity_id: entityId,
        activity_type: type,
        body,
      });
      setBody("");
      setVersion((v) => v + 1);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">Activity</p>
      <div className="flex gap-2">
        <Select value={type} onChange={(e) => setType(e.target.value)} className="w-28">
          {TYPES.map((t) => (
            <option key={t} value={t}>
              {titleCase(t)}
            </option>
          ))}
        </Select>
        <Input
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Log a call, email, note…"
          onKeyDown={(e) => e.key === "Enter" && add()}
        />
        <Button onClick={add} disabled={busy || !body.trim()}>
          Log
        </Button>
      </div>
      <div className="space-y-3">
        {activities.map((a) => {
          const Icon = ICONS[a.activity_type] ?? ActivityIcon;
          return (
            <div key={a.id} className="flex gap-3">
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary/10 text-secondary">
                <Icon className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-primary">
                  {a.subject ?? a.body ?? titleCase(a.activity_type)}
                </p>
                {a.subject && a.body && <p className="text-sm text-muted">{a.body}</p>}
                <p className="text-xs text-muted">
                  {titleCase(a.activity_type)} · {relativeTime(a.occurred_at)}
                </p>
              </div>
            </div>
          );
        })}
        {activities.length === 0 && <p className="text-sm text-muted">No activity logged yet.</p>}
      </div>
    </div>
  );
}
