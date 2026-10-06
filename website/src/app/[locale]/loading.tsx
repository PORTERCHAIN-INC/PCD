import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";

export default function LocaleLoading() {
  return (
    <RouteLoading label="Loading page">
      <div className="mx-auto max-w-5xl px-4 py-10">
        <PageSkeleton rows={4} />
      </div>
    </RouteLoading>
  );
}
