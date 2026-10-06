import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import JobsListClient from "@/components/jobs/JobsListClient";
import { loadDriverJobs, loadDriverJobsHistory } from "@/lib/server-api";

export default async function JobsPage() {
  const client = new QueryClient();
  const [jobs, history] = await Promise.all([loadDriverJobs(), loadDriverJobsHistory()]);
  if (jobs) client.setQueryData(["driver-jobs"], jobs);
  if (history) client.setQueryData(["driver-jobs-history"], history);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <JobsListClient />
    </HydrationBoundary>
  );
}
