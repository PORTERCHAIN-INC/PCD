import { Suspense } from "react";
import IntegrationsClient from "@/components/integrations/IntegrationsClient";

export default function ApiPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading integrations…</p>}>
      <IntegrationsClient />
    </Suspense>
  );
}
