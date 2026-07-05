import { adminFetch } from "@/lib/api";
import type { Activity, Task } from "@/lib/crm";

const B = "/v1/admin/collaboration";

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
};

export const collaboration = {
  activities: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Activity[]>(`${B}/activities${qs(params)}`, t),
  createActivity: (
    t: string,
    body: {
      entity_type: string;
      entity_id: string;
      activity_type?: string;
      subject?: string;
      body?: string;
    }
  ) =>
    adminFetch<Activity>(`${B}/activities`, t, { method: "POST", body: JSON.stringify(body) }),
  tasks: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Task[]>(`${B}/tasks${qs(params)}`, t),
  createTask: (t: string, body: Partial<Task>) =>
    adminFetch<Task>(`${B}/tasks`, t, { method: "POST", body: JSON.stringify(body) }),
  updateTask: (t: string, id: string, body: Partial<Task>) =>
    adminFetch<Task>(`${B}/tasks/${id}`, t, { method: "PATCH", body: JSON.stringify(body) }),
};
