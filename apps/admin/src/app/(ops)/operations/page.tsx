import { Suspense } from "react";
import { OpsTowerFallback } from "@/components/operations/OpsTowerFallback";
import { OpsTowerShell } from "@/components/operations/OpsTowerShell";

export default function OperationsPage() {
  return (
    <Suspense fallback={<OpsTowerFallback />}>
      <OpsTowerShell />
    </Suspense>
  );
}
