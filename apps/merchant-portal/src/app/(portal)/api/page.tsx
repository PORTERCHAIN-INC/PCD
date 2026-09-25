import dynamic from "next/dynamic";
import { Suspense } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";

const IntegrationsClient = dynamic(() => import("@/components/integrations/IntegrationsClient"), {
  loading: () => <PageSkeleton rows={6} />,
});

export default function ApiPage() {
  return (
    <Suspense fallback={<PageSkeleton rows={6} />}>
      <IntegrationsClient />
    </Suspense>
  );
}
