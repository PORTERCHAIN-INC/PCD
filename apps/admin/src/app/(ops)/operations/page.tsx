"use client";

import { Suspense } from "react";
import { OpsTowerShell } from "@/components/operations/OpsTowerShell";
import { Spinner } from "@/components/crm/primitives";

export default function OperationsPage() {
  return (
    <Suspense fallback={<Spinner label="Loading Control Tower…" />}>
      <OpsTowerShell />
    </Suspense>
  );
}
