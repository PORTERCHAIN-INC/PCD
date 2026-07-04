"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import type { CustomerDashboard } from "@/lib/api";

export default function CustomerDashboardView({
  dashboard,
  error,
  supportSent,
  supportSubject,
  supportMessage,
  onSupportSubjectChange,
  onSupportMessageChange,
  onSubmitSupport,
  onRebook,
}: {
  dashboard: CustomerDashboard | null;
  error: string | null;
  supportSent: boolean;
  supportSubject: string;
  supportMessage: string;
  onSupportSubjectChange: (value: string) => void;
  onSupportMessageChange: (value: string) => void;
  onSubmitSupport: (e: React.FormEvent) => void;
  onRebook: (orderId: string) => void;
}) {
  const t = useTranslations("portal.customer");

  return (
    <>
      {error && <p className="text-red-600 type-small mb-6">{error}</p>}
      {supportSent && <p className="text-green-700 type-small mb-6">{t("supportSent")}</p>}

      {!dashboard?.orders.length && !dashboard?.active_order && (
        <section className="rounded-2xl border border-dashed border-primary/15 bg-gray-bg/60 p-8 mb-8 text-center">
          <p className="type-body font-semibold text-primary mb-2">{t("emptyTitle")}</p>
          <p className="type-small text-muted mb-6 max-w-md mx-auto">{t("emptySubtitle")}</p>
          <Link
            href="/#book"
            className="inline-flex rounded-xl bg-secondary px-5 py-3 text-white font-semibold type-small hover:bg-[#1d4ed8]"
          >
            {t("emptyCta")}
          </Link>
        </section>
      )}

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
              {dashboard.orders.map((o) => (
                <li key={o.order_id} className="rounded-xl bg-gray-bg p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Link
                        href={`/track/${o.tracking_number}`}
                        className="type-caption font-mono text-secondary hover:underline"
                      >
                        {o.tracking_number}
                      </Link>
                      <p className="type-small text-muted mt-1">{o.state}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => onRebook(o.order_id)}
                      className="text-secondary font-semibold type-small hover:underline shrink-0"
                    >
                      {t("rebook")}
                    </button>
                  </div>
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
              {dashboard.invoices.map((inv) => (
                <li key={inv.invoice_id} className="rounded-xl bg-gray-bg p-4">
                  <p className="type-caption font-mono">{inv.invoice_number}</p>
                  <p className="type-small text-muted">
                    ${(inv.amount_cents / 100).toFixed(2)} {inv.currency.toUpperCase()}
                  </p>
                  {inv.stripe_receipt_url && (
                    <a
                      href={inv.stripe_receipt_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-secondary font-semibold type-small hover:underline"
                    >
                      {t("receipt")}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="type-small text-muted">{t("noInvoices")}</p>
          )}
        </section>
      </div>

      <section className="mt-10">
        <h2 className="type-body font-bold text-primary mb-4">{t("payments")}</h2>
        {dashboard?.payments.length ? (
          <ul className="space-y-3">
            {dashboard.payments.map((p) => (
              <li key={p.payment_id} className="rounded-xl bg-gray-bg p-4">
                <p className="type-small">
                  ${(p.amount_cents / 100).toFixed(2)} {p.currency.toUpperCase()} — {p.status}
                </p>
                {p.failure_reason && (
                  <p className="type-caption text-red-600">{p.failure_reason}</p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="type-small text-muted">{t("noPayments")}</p>
        )}
      </section>

      <section className="mt-10 rounded-2xl border border-primary/10 p-6">
        <h2 className="type-body font-bold text-primary mb-4">{t("support")}</h2>
        <form onSubmit={onSubmitSupport} className="space-y-4">
          <input
            required
            value={supportSubject}
            onChange={(e) => onSupportSubjectChange(e.target.value)}
            placeholder={t("supportSubject")}
            className="w-full rounded-xl border px-4 py-3 type-small"
          />
          <textarea
            value={supportMessage}
            onChange={(e) => onSupportMessageChange(e.target.value)}
            placeholder={t("supportMessage")}
            rows={4}
            className="w-full rounded-xl border px-4 py-3 type-small"
          />
          <button
            type="submit"
            className="rounded-xl bg-secondary px-5 py-3 text-white font-semibold type-small"
          >
            {t("submitSupport")}
          </button>
        </form>
      </section>
    </>
  );
}
