import { Suspense } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
import { SystemCenter } from "@/components/diagnostics/SystemCenter";

export default function SystemPage() {
  return (
    <Suspense fallback={<PageSkeleton rows={5} />}>
      <SystemCenter />
    </Suspense>
  );
}
