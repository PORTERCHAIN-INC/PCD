"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Spinner } from "@porterchain/ui/loading";
import CustomerShell from "@/components/CustomerShell";
import { customerApi } from "@/lib/api";
import { formatCents } from "@/lib/booking";
import { isClerkConfigured } from "@/lib/env";

export default function InvoicesClient() {
  if (!isClerkConfigured()) {
    return <InvoicesBody getToken={async () => "dev"} />;
  }
  return <InvoicesWithClerk />;
}

function InvoicesWithClerk() {
  const router = useRouter();
  const { isSignedIn, isLoaded, getToken } = useAuth();

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace("/sign-in?redirect_url=/invoices");
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || !isSignedIn) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-gray-bg">
        <Spinner label="Loading invoices…" />
      </main>
    );
  }

  return <InvoicesBody getToken={getToken} />;
}

function InvoicesBody({ getToken }: { getToken: () => Promise<string | null> }) {
  const {
    data: rows,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["customer-invoices"],
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      return customerApi.invoices(token);
    },
  });

  return (
    <CustomerShell>
      <header>
        <h1 className="text-xl font-semibold text-primary sm:text-2xl">Invoices</h1>
        <p className="mt-1 text-sm text-muted">Receipts for deliveries booked on your account.</p>
      </header>
      {error ? (
        <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load invoices.
        </p>
      ) : null}
      {isLoading ? (
        <div className="mt-8 flex justify-center">
          <Spinner label="Loading invoices…" />
        </div>
      ) : null}
      {rows && rows.length === 0 ? (
        <p className="mt-6 text-sm text-muted">
          No invoices yet. They appear after a delivery is booked.
        </p>
      ) : null}
      {rows && rows.length > 0 ? (
        <ul className="mt-6 divide-y divide-primary/8 overflow-hidden rounded-2xl border border-primary/8 bg-white">
          {rows.map((inv) => (
            <li key={inv.invoice_id}>
              <Link
                href={`/invoices/${inv.invoice_id}`}
                className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-gray-bg"
              >
                <span>
                  <span className="block font-mono text-sm font-semibold text-primary">
                    {inv.invoice_number}
                  </span>
                  <span className="text-xs capitalize text-muted">{inv.status || "open"}</span>
                </span>
                <span className="text-sm font-medium text-primary">
                  {formatCents(inv.amount_cents, (inv.currency || "cad").toUpperCase())}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </CustomerShell>
  );
}
