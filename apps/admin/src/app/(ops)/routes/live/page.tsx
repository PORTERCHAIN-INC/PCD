"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import LiveMapApp from "@/components/live-map/LiveMapApp";
import { Button } from "@/components/crm/primitives";
import { RouteSectionCard } from "@/components/routes/RouteCenterPrimitives";

export default function LiveExecutionPage() {
  return (
    <RouteSectionCard
      title="Live Execution"
      description="Real-time driver locations, route progress, and ETAs."
      action={
        <Link href="/live-map">
          <Button variant="outline" className="gap-2 text-xs">
            <ExternalLink className="h-3.5 w-3.5" />
            Full-screen map
          </Button>
        </Link>
      }
    >
      <div className="overflow-hidden rounded-2xl border border-primary/10 bg-gray-bg/40">
        <div className="h-[min(70vh,720px)] min-h-[420px]">
          <LiveMapApp />
        </div>
      </div>
    </RouteSectionCard>
  );
}
