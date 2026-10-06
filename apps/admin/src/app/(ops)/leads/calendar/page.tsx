import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import LeadsCalendarClient from "@/components/leads/LeadsCalendarClient";
import { adminServerFetch } from "@/lib/server-api";

function startOfWeek(d: Date): Date {
  const x = new Date(d);
  const day = (x.getDay() + 6) % 7;
  x.setHours(0, 0, 0, 0);
  x.setDate(x.getDate() - day);
  return x;
}

export default async function LeadsCalendarPage() {
  const client = new QueryClient();
  const from = startOfWeek(new Date());
  const to = new Date(from);
  to.setDate(to.getDate() + 7);
  const due_after = from.toISOString();
  const due_before = to.toISOString();
  const qs = new URLSearchParams({ due_after, due_before });
  const tasks = await adminServerFetch<unknown>(`/v1/admin/leads/calendar?${qs}`);
  if (tasks) client.setQueryData(["lead-calendar", due_after, due_before], tasks);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <LeadsCalendarClient />
    </HydrationBoundary>
  );
}
