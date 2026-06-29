"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import { getOrderByTracking, type OrderResult } from "@/lib/api";

export default function TrackPage() {
  const t = useTranslations("booking.track");
  const params = useParams();
  const tracking = typeof params.tracking === "string" ? params.tracking : "";
  const [order, setOrder] = useState<OrderResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tracking) return;
    getOrderByTracking(tracking)
      .then(setOrder)
      .catch(() => setError(t("notFound")));
  }, [tracking, t]);

  return (
    <SiteShell>
      <Container className="py-16 md:py-24 max-w-lg">
        <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
        <p className="type-caption text-muted font-mono mb-8">{tracking}</p>
        {error && <p className="text-red-600">{error}</p>}
        {order && (
          <dl className="space-y-3 rounded-2xl bg-gray-bg p-6">
            <div className="flex justify-between">
              <dt className="text-muted type-small">{t("status")}</dt>
              <dd className="font-semibold type-small">{order.state}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted type-small">{t("pickup")}</dt>
              <dd className="type-small text-right max-w-[60%]">
                {(order.pickup as { formatted?: string }).formatted}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted type-small">{t("dropoff")}</dt>
              <dd className="type-small text-right max-w-[60%]">
                {(order.dropoff as { formatted?: string }).formatted}
              </dd>
            </div>
          </dl>
        )}
      </Container>
    </SiteShell>
  );
}
