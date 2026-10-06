import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";

export default function CustomerLoading() {
  return (
    <RouteLoading label="Loading page">
      <PageSkeleton rows={4} />
    </RouteLoading>
  );
}
