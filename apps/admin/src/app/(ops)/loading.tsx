import { PageSkeleton, RouteLoading, StatCardsSkeleton } from "@porterchain/ui/loading";

export default function OpsLoading() {
  return (
    <RouteLoading label="Loading page">
      <StatCardsSkeleton />
      <PageSkeleton rows={4} />
    </RouteLoading>
  );
}
