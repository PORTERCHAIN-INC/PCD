"use client";

import { useState } from "react";
import { Check, Circle, Plus } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Task } from "@/lib/crm";
import { drivers } from "@/lib/drivers";
import { Badge, Button, Input, Select } from "@/components/crm/primitives";
import { STATUS_TONE, dateTime, titleCase } from "@/lib/crmFormat";

const TYPES = [
  "follow_up",
  "call",
  "email",
  "meeting",
  "demo",
  "merchant_visit",
  "document",
  "contract_review",
  "todo",
];

export function EntityTasks({
  entityType,
  entityId,
  companyId,
  dealId,
  onChanged,
}: {
  entityType: string;
  entityId: string;
  companyId?: string | null;
  dealId?: string | null;
  onChanged?: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data } = useApiData(
    (t) =>
      entityType === "driver"
        ? drivers.tasks(t, entityId)
        : crm.tasks(t, { entity_id: entityId }),
    [entityType, entityId, version],
    { key: `${entityType}-${entityId}-tasks` }
  );

  const tasks = Array.isArray(data) ? data : [];

  const [title, setTitle] = useState("");
  const [type, setType] = useState("follow_up");
  const [due, setDue] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    setVersion((v) => v + 1);
    onChanged?.();
  };

  async function add() {
    if (!title.trim()) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createTask(token, {
        title,
        task_type: type,
        entity_type: entityType,
        entity_id: entityId,
        company_id: companyId ?? undefined,
        deal_id: dealId ?? undefined,
        due_at: due ? new Date(due).toISOString() : null,
      });
      setTitle("");
      setDue("");
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function toggle(task: Task) {
    const token = await getApiToken();
    await crm.updateTask(token, task.id, { status: task.status === "done" ? "open" : "done" });
    refresh();
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-primary/10 bg-gray-bg/40 p-3">
        <div className="flex flex-wrap items-end gap-2">
          <Input
            value={title}
            placeholder="New follow-up / task…"
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
            className="min-w-[180px] flex-1"
          />
          <Select value={type} onChange={(e) => setType(e.target.value)} className="w-36">
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {titleCase(t)}
              </option>
            ))}
          </Select>
          <Input
            type="datetime-local"
            value={due}
            onChange={(e) => setDue(e.target.value)}
            className="w-52"
          />
          <Button onClick={add} disabled={busy || !title.trim()}>
            <Plus className="h-4 w-4" />
            Add
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {tasks.map((task) => {
          const done = task.status === "done";
          const overdue = !done && task.due_at && new Date(task.due_at) < new Date();
          return (
            <div
              key={task.id}
              className="flex items-center gap-3 rounded-xl border border-primary/10 p-3"
            >
              <button
                onClick={() => toggle(task)}
                className={
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border " +
                  (done
                    ? "border-green-600 bg-green-600 text-white"
                    : "border-primary/30 text-transparent hover:border-secondary")
                }
              >
                {done ? <Check className="h-3 w-3" /> : <Circle className="h-3 w-3" />}
              </button>
              <div className="min-w-0 flex-1">
                <p
                  className={
                    "text-sm font-medium " + (done ? "text-muted line-through" : "text-primary")
                  }
                >
                  {task.title}
                </p>
                <p className="text-xs text-muted">
                  {titleCase(task.task_type)}
                  {task.due_at && (
                    <span className={overdue ? " font-medium text-red-600" : ""}>
                      {" "}
                      · {dateTime(task.due_at)}
                    </span>
                  )}
                </p>
              </div>
              <Badge tone={STATUS_TONE[task.status]}>{titleCase(task.status)}</Badge>
            </div>
          );
        })}
        {tasks.length === 0 && (
          <p className="py-6 text-center text-sm text-muted">No follow-ups scheduled yet.</p>
        )}
      </div>
    </div>
  );
}
