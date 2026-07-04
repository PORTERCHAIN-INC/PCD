"use client";

import { useState } from "react";
import { Copy } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { routeCenter, type RouteTemplate } from "@/lib/route-center";
import { Button, Spinner } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";
import {
  RouteEmptyState,
  RouteErrorState,
  RouteSectionCard,
} from "@/components/routes/RouteCenterPrimitives";

export default function RouteTemplatesPage() {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState<string | null>(null);
  const { data, error, refetch } = useApiData((t) => routeCenter.templates(t), [], { key: "route-templates" });

  const createPlan = async (tpl: RouteTemplate) => {
    setBusy(tpl.id);
    try {
      const token = await getApiToken();
      await routeCenter.createFromTemplate(token, tpl.id);
      refetch();
    } finally {
      setBusy(null);
    }
  };

  if (error) return <RouteErrorState message={error} />;
  if (!data) return <Spinner label="Loading templates…" />;

  return (
    <RouteSectionCard
      title="Route Templates"
      description="Daily, weekly, merchant, and recurring templates. Save from Route 360 after building a plan."
    >
      {data.length === 0 ? (
        <RouteEmptyState title="No templates yet" hint="Build a route in Route Builder and save it as a template from Route 360." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {data.map((tpl) => (
            <div
              key={tpl.id}
              className="flex flex-col justify-between gap-4 rounded-xl border border-primary/10 bg-gray-bg/30 p-4 transition-colors hover:border-secondary/20 hover:bg-white"
            >
              <div>
                <p className="font-semibold text-primary">{tpl.name}</p>
                <p className="mt-1 text-xs text-muted">
                  {titleCase(tpl.template_type)} · {tpl.stops.length} stops
                  {tpl.zone ? ` · ${tpl.zone}` : ""}
                </p>
              </div>
              <Button
                variant="outline"
                className="w-full gap-2"
                disabled={busy === tpl.id}
                onClick={() => createPlan(tpl)}
              >
                <Copy className="h-4 w-4" />
                {busy === tpl.id ? "Creating plan…" : "Create plan from template"}
              </Button>
            </div>
          ))}
        </div>
      )}
    </RouteSectionCard>
  );
}
