"use client";

import { Suspense } from "react";
import { SystemCenter } from "@/components/diagnostics/SystemCenter";
import { Spinner } from "@/components/crm/primitives";

export default function SystemPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      }
    >
      <SystemCenter />
    </Suspense>
  );
}
