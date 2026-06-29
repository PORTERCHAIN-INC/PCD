"use client";

import { useMemo, useState } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { Plus, Check, Circle } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Task } from "@/lib/crm";
import { CrmTable } from "@/components/crm/CrmTable";
import { Badge, Button, Drawer, Field, Input, Select, Textarea } from "@/components/crm/primitives";
import { STATUS_TONE, dateTime, titleCase } from "@/lib/crmFormat";

const TYPES = [
  "call",
  "email",
  "meeting",
  "follow_up",
  "document",
  "contract_review",
  "merchant_visit",
  "demo",
  "todo",
];
const PRIORITIES = ["low", "medium", "high", "urgent"];

const blank = (): Partial<Task> => ({ title: "", task_type: "follow_up", priority: "medium" });

export default function TasksPage() {
  const { getApiToken } = useAdminAuth();
  const [statusFilter, setStatusFilter] = useState("");
  const [version, setVersion] = useState(0);
  const { data, error } = useApiData(
    (t) => crm.tasks(t, { status: statusFilter || undefined }),
    [statusFilter, version]
  );

  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Partial<Task>>(blank());
  const [due, setDue] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = () => setVersion((v) => v + 1);

  async function submitCreate() {
    if (!form.title) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createTask(token, {
        ...form,
        due_at: due ? new Date(due).toISOString() : null,
      });
      setCreating(false);
      setForm(blank());
      setDue("");
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function toggleDone(task: Task) {
    const token = await getApiToken();
    await crm.updateTask(token, task.id, { status: task.status === "done" ? "open" : "done" });
    refresh();
  }

  const columns = useMemo<ColumnDef<Task, unknown>[]>(
    () => [
      {
        id: "done",
        header: "",
        enableSorting: false,
        cell: ({ row }) => {
          const done = row.original.status === "done";
          return (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleDone(row.original);
              }}
              className={
                "flex h-5 w-5 items-center justify-center rounded-full border " +
                (done
                  ? "border-green-600 bg-green-600 text-white"
                  : "border-primary/30 text-transparent hover:border-secondary")
              }
            >
              {done ? <Check className="h-3 w-3" /> : <Circle className="h-3 w-3" />}
            </button>
          );
        },
      },
      {
        accessorKey: "title",
        header: "Task",
        cell: ({ row }) => (
          <div>
            <p
              className={
                "font-medium " +
                (row.original.status === "done" ? "text-muted line-through" : "text-primary")
              }
            >
              {row.original.title}
            </p>
            <p className="text-xs text-muted">{titleCase(row.original.task_type)}</p>
          </div>
        ),
      },
      {
        accessorKey: "priority",
        header: "Priority",
        cell: ({ getValue }) => (
          <Badge tone={STATUS_TONE[String(getValue())]}>{titleCase(String(getValue()))}</Badge>
        ),
      },
      {
        accessorKey: "due_at",
        header: "Due",
        cell: ({ row }) => {
          const due = row.original.due_at;
          if (!due) return "—";
          const overdue = row.original.status !== "done" && new Date(due) < new Date();
          return (
            <span className={overdue ? "font-medium text-red-600" : "text-primary"}>
              {dateTime(due)}
            </span>
          );
        },
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ getValue }) => (
          <Badge tone={STATUS_TONE[String(getValue())]}>{titleCase(String(getValue()))}</Badge>
        ),
      },
    ],
    []
  );

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      <CrmTable
        data={data}
        columns={columns}
        searchPlaceholder="Search tasks…"
        emptyTitle="No tasks yet"
        emptyHint="Track calls, follow-ups, demos, and merchant visits."
        toolbar={
          <>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-36"
            >
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="in_progress">In progress</option>
              <option value="done">Done</option>
            </Select>
            <Button onClick={() => setCreating(true)}>
              <Plus className="h-4 w-4" />
              New Task
            </Button>
          </>
        }
      />

      <Drawer
        open={creating}
        onClose={() => setCreating(false)}
        title="New task"
        footer={
          <>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button onClick={submitCreate} disabled={busy || !form.title}>
              Create task
            </Button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Title *" className="col-span-2">
            <Input
              value={form.title ?? ""}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </Field>
          <Field label="Type">
            <Select
              value={form.task_type ?? "follow_up"}
              onChange={(e) => setForm({ ...form, task_type: e.target.value })}
            >
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {titleCase(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Priority">
            <Select
              value={form.priority ?? "medium"}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {titleCase(p)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Due" className="col-span-2">
            <Input type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} />
          </Field>
          <Field label="Description" className="col-span-2">
            <Textarea
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </Field>
        </div>
      </Drawer>
    </div>
  );
}
