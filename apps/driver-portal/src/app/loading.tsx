import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";

export default function DriverLoading() {
  return (
    <RouteLoading label="Loading page">
      <PageSkeleton rows={4} />
    </RouteLoading>
  );
}
