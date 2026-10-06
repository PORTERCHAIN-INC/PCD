"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { forbiddenModuleMessage } from "@/lib/catalog";
import { requiredNavModule } from "@/lib/merchant-nav";

export default function ModuleGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { modules, isLoaded } = useMerchantAuth();
  const moduleKey = requiredNavModule(pathname);

  if (!isLoaded) {
    return <PageSkeleton rows={4} />;
  }
  if (!moduleKey || modules.includes(moduleKey)) {
    return <>{children}</>;
  }

  return (
    <div
      data-testid="module-gate-forbidden"
      data-module={moduleKey}
      className="mx-auto flex min-h-[40vh] max-w-md flex-col items-center justify-center gap-3 p-6 text-center"
    >
      <h1 className="text-lg font-semibold text-primary">You don’t have access</h1>
      <p className="text-sm text-muted">{forbiddenModuleMessage(moduleKey)}</p>
    </div>
  );
}
