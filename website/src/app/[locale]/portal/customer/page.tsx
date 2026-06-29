"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import { getCustomerDashboard, type CustomerDashboard } from "@/lib/api";
import { isClerkConfigured } from "@/lib/env";

export default function CustomerPortalPage() {
  if (isClerkConfigured()) {
    return <CustomerPortalClerk />;
  }
  return <CustomerPortalContent isLoaded isSignedIn getToken={async () => "dev"} />;
}

function CustomerPortalClerk() {
  const { isSignedIn, isLoaded, getToken } = useAuth();
  return (
    <CustomerPortalContent
      isLoaded={isLoaded}
      isSignedIn={Boolean(isSignedIn)}
      getToken={getToken}
    />
  );
}

function CustomerPortalContent({
  isLoaded,
  isSignedIn,
  getToken,
}: {
  isLoaded: boolean;
  isSignedIn: boolean;
  getToken: () => Promise<string | null>;
}) {
  const t = useTranslations("portal.customer");
  const [dashboard, setDashboard] = useState<CustomerDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const needsSignIn = isClerkConfigured() && isLoaded && !isSignedIn;

  useEffect(() => {
    if (!isLoaded || needsSignIn) return;
    let cancelled = false;
    async function load() {
      try {
        const token = (await getToken()) ?? "dev";
        const data = await getCustomerDashboard(token);
        if (!cancelled) setDashboard(data);
      } catch {
        if (!cancelled) setError(t("loadError"));
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load dashboard once auth ready
  }, [isLoaded, needsSignIn]);

  const displayError = needsSignIn ? t("signInRequired") : error;

  return (
    <SiteShell>
      <Container className="py-16 md:py-24 max-w-3xl">
        <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
        <p className="type-small text-muted mb-8">{t("subtitle")}</p>

        {displayError && <p className="text-red-600 type-small mb-6">{displayError}</p>}

        {dashboard?.active_order && (
          <section className="rounded-2xl bg-secondary/5 border border-secondary/20 p-6 mb-8">
            <h2 className="type-h3 font-bold text-primary mb-2">{t("activeShipment")}</h2>
            <p className="type-caption font-mono text-muted mb-4">
              {dashboard.active_order.tracking_number}
            </p>
            <p className="type-small mb-4">
              {t("status")}: <strong>{dashboard.active_order.state}</strong>
            </p>
            <Link
              href={`/track/${dashboard.active_order.tracking_number}`}
              className="text-secondary font-semibold type-small hover:underline"
            >
              {t("track")}
            </Link>
          </section>
        )}

        <div className="grid gap-8 md:grid-cols-2">
          <section>
            <h2 className="type-body font-bold text-primary mb-4">{t("history")}</h2>
            {dashboard?.orders.length ? (
              <ul className="space-y-3">
                {dashboard.orders.slice(0, 5).map((o) => (
                  <li key={o.order_id} className="rounded-xl bg-gray-bg p-4">
                    <p className="type-caption font-mono">{o.tracking_number}</p>
                    <p className="type-small text-muted">{o.state}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="type-small text-muted">{t("noOrders")}</p>
            )}
          </section>

          <section>
            <h2 className="type-body font-bold text-primary mb-4">{t("invoices")}</h2>
            {dashboard?.invoices.length ? (
              <ul className="space-y-3">
                {dashboard.invoices.slice(0, 5).map((inv) => (
                  <li key={inv.invoice_id} className="rounded-xl bg-gray-bg p-4">
                    <p className="type-caption font-mono">{inv.invoice_number}</p>
                    <p className="type-small text-muted">
                      ${(inv.amount_cents / 100).toFixed(2)} {inv.currency.toUpperCase()}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="type-small text-muted">{t("noInvoices")}</p>
            )}
          </section>
        </div>

        <div className="mt-10 flex flex-wrap gap-4">
          <Link href="/#book" className="text-secondary font-semibold type-small hover:underline">
            {t("rebook")}
          </Link>
          <Link href="/contact" className="text-secondary font-semibold type-small hover:underline">
            {t("support")}
          </Link>
        </div>
      </Container>
    </SiteShell>
  );
}
