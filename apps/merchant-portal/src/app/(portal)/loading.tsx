import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";

export default function MerchantLoading() {
  return (
    <RouteLoading label="Loading page">
      <PageSkeleton rows={5} />
    </RouteLoading>
  );
}
