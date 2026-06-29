"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";

export default function BookSuccessPage() {
  return (
    <Suspense
      fallback={
        <SiteShell>
          <Container className="py-16 md:py-24 max-w-lg text-center">
            <p className="type-small text-muted">Loading…</p>
          </Container>
        </SiteShell>
      }
    >
      <BookSuccessContent />
    </Suspense>
  );
}

function BookSuccessContent() {
  const t = useTranslations("booking.success");
  const searchParams = useSearchParams();
  const tracking = searchParams.get("tracking") ?? "";
  const orderNumber = searchParams.get("order") ?? "";
  const bookingNumber = searchParams.get("booking") ?? "";
  const invoiceNumber = searchParams.get("invoice") ?? "";

  const refs = [
    { label: t("trackingLabel"), value: tracking },
    { label: t("orderLabel"), value: orderNumber },
    { label: t("bookingLabel"), value: bookingNumber },
    { label: t("invoiceLabel"), value: invoiceNumber },
  ].filter((r) => r.value);

  return (
    <SiteShell>
      <Container className="py-16 md:py-24 max-w-lg text-center">
        <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
        <p className="type-small text-muted mb-6">{t("subtitle")}</p>
        {refs.length > 0 && (
          <dl className="text-left rounded-2xl bg-gray-bg p-4 mb-8 space-y-2">
            {refs.map((r) => (
              <div key={r.label} className="flex justify-between gap-4">
                <dt className="type-caption text-muted">{r.label}</dt>
                <dd className="type-caption font-mono font-semibold text-primary">{r.value}</dd>
              </div>
            ))}
          </dl>
        )}
        <div className="flex flex-col gap-3">
          {tracking && (
            <Link
              href={`/track/${tracking}`}
              className="inline-flex items-center justify-center w-full min-h-[3rem] rounded-full bg-secondary text-white font-bold type-button hover:bg-[#1d4ed8] transition-colors"
            >
              {t("track")}
            </Link>
          )}
          <Link
            href="/portal/customer"
            className="inline-flex items-center justify-center w-full min-h-[3rem] rounded-full border-2 border-secondary text-secondary font-bold type-button hover:bg-secondary/5 transition-colors"
          >
            {t("dashboard")}
          </Link>
          <Link
            href="/"
            className="inline-flex items-center justify-center w-full py-3 rounded-full text-primary font-semibold type-button hover:bg-gray-bg transition-colors"
          >
            {t("home")}
          </Link>
        </div>
      </Container>
    </SiteShell>
  );
}
