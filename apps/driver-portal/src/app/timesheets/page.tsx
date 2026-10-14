import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import TimeClient from "@/components/time/TimeClient";
import { driverServerGet } from "@/lib/server-api";
import type { ScheduleResponse, Timesheets } from "@/lib/api";

export const metadata = { title: "Time · Porterchain Driver" };

export default async function TimesheetsPage() {
  const client = new QueryClient();
  const [sheets, schedule] = await Promise.all([
    driverServerGet<Timesheets>("/v1/timesheets?weeks=8"),
    driverServerGet<ScheduleResponse>("/v1/availability/schedule"),
  ]);
  if (sheets) client.setQueryData(["driver-timesheets"], sheets);
  if (schedule) client.setQueryData(["driver-schedule"], schedule);
  return (
    <HydrationBoundary state={dehydrate(client)}>
      <TimeClient />
    </HydrationBoundary>
  );
}
