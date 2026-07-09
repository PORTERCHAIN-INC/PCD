"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton, Spinner } from "@porterchain/ui/loading";
import CustomerShell from "@/components/CustomerShell";
import { customerApi, type CustomerDashboard } from "@/lib/api";
import { isClerkConfigured } from "@/lib/env";

export default function DashboardPage() {
  const router = useRouter();
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const [dashboard, setDashboard] = useState<CustomerDashboard | null>(null);
  const [error, setError] = useState("");
  const [supportSubject, setSupportSubject] = useState("");
  const [supportMessage, setSupportMessage] = useState("");
  const [supportSent, setSupportSent] = useState(false);

  useEffect(() => {
    if (isLoaded && !isSignedIn && isClerkConfigured()) {
      router.replace("/sign-in?redirect_url=/dashboard");
    }
  }, [isLoaded, isSignedIn, router]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      try {
        const token = await getToken();
        if (!token) return;
        setDashboard(await customerApi.dashboard(token));
        setError("");
      } catch {
        setError("Failed to load dashboard");
      }
    })();
  }, [isLoaded, isSignedIn, getToken]);

  const submitSupport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = await getToken();
      if (!token) return;
      await customerApi.createSupport(token, {
        subject: supportSubject,
        description: supportMessage,
      });
      setSupportSent(true);
      setSupportSubject("");
      setSupportMessage("");
    } catch {
      setError("Could not submit support ticket");
    }
  };

  if (isClerkConfigured() && (!isLoaded || !isSignedIn)) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-bg">
        <Spinner label="Loading your account…" />
      </main>
    );
  }

  const loadingDashboard = isSignedIn && !dashboard && !error;

  return (
    <CustomerShell>
      {loadingDashboard && <PageSkeleton rows={3} />}

      {!loadingDashboard && (
        <>
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-primary">Your deliveries</h1>
            <p className="mt-1 text-sm text-muted">
              Track shipments, view invoices, and contact support
            </p>
          </div>

          {error && (
            <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}
          {supportSent && (
            <div className="mb-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
              Support ticket submitted.
            </div>
          )}

          {!dashboard?.orders.length && !dashboard?.active_order && (
            <EmptyState
              title="No deliveries yet"
              hint="Book your first delivery and it will appear here."
              action={
                <Link
                  href="/book"
                  className="inline-flex rounded-xl bg-secondary px-5 py-3 text-sm font-semibold text-white hover:bg-secondary/90"
                >
                  Book now
                </Link>
              }
            />
          )}

          {dashboard?.active_order && (
            <section className="mb-8 rounded-2xl border border-secondary/20 bg-secondary/5 p-6 shadow-sm">
              <h2 className="text-lg font-bold text-primary">Active shipment</h2>
              <p className="mt-2 font-mono text-sm text-muted">
                {dashboard.active_order.tracking_number}
              </p>
              <p className="mt-2 text-sm text-primary">
                Status: <span className="font-semibold">{dashboard.active_order.state}</span>
              </p>
              <Link
                href={`/track/${dashboard.active_order.tracking_number}`}
                className="mt-4 inline-block text-sm font-semibold text-secondary hover:underline"
              >
                View tracking details →
              </Link>
            </section>
          )}

          <div className="grid gap-6 md:grid-cols-2">
            <section className="rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
              <h2 className="mb-4 font-semibold text-primary">Order history</h2>
              {(dashboard?.orders ?? []).length === 0 ? (
                <EmptyState title="No orders yet" className="border-0 py-6" />
              ) : (
                <ul className="space-y-3">
                  {(dashboard?.orders ?? []).map((o) => (
                    <li key={o.order_id} className="rounded-xl bg-gray-bg p-4 text-sm">
                      <Link
                        href={`/track/${o.tracking_number}`}
                        className="font-mono text-secondary hover:underline"
                      >
                        {o.tracking_number}
                      </Link>
                      <p className="mt-1 text-muted">{o.state}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
              <h2 className="mb-4 font-semibold text-primary">Invoices</h2>
              {(dashboard?.invoices ?? []).length === 0 ? (
                <EmptyState title="No invoices yet" className="border-0 py-6" />
              ) : (
                <ul className="space-y-3">
                  {(dashboard?.invoices ?? []).map((inv) => (
                    <li key={inv.invoice_id} className="rounded-xl bg-gray-bg p-4 text-sm">
                      <p className="font-mono text-primary">{inv.invoice_number}</p>
                      <p className="mt-1 text-muted">
                        ${(inv.amount_cents / 100).toFixed(2)} {inv.currency.toUpperCase()}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="mt-6 rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
            <h2 className="mb-4 font-semibold text-primary">Contact support</h2>
            <form onSubmit={submitSupport} className="space-y-4">
              <input
                required
                value={supportSubject}
                onChange={(e) => setSupportSubject(e.target.value)}
                placeholder="Subject"
                className="w-full rounded-xl border border-primary/10 px-4 py-3 text-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20"
              />
              <textarea
                value={supportMessage}
                onChange={(e) => setSupportMessage(e.target.value)}
                placeholder="How can we help?"
                rows={4}
                className="w-full rounded-xl border border-primary/10 px-4 py-3 text-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20"
              />
              <button
                type="submit"
                className="rounded-xl bg-secondary px-5 py-3 text-sm font-semibold text-white hover:bg-secondary/90"
              >
                Submit ticket
              </button>
            </form>
          </section>
        </>
      )}
    </CustomerShell>
  );
}
