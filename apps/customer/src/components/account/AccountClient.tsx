"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import CustomerShell from "@/components/CustomerShell";
import AddressBook from "@/components/account/AddressBook";
import { isClerkConfigured } from "@/lib/env";
import { customerApi } from "@/lib/api";

export default function AccountClient() {
  if (!isClerkConfigured()) {
    return <AccountBody ready signedIn getToken={async () => "dev"} />;
  }
  return <AccountWithClerk />;
}

function AccountWithClerk() {
  const router = useRouter();
  const { isSignedIn, isLoaded, getToken } = useAuth();

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace("/sign-in?redirect_url=/account");
    }
  }, [isLoaded, isSignedIn, router]);

  return <AccountBody ready={isLoaded} signedIn={Boolean(isSignedIn)} getToken={getToken} />;
}

function AccountBody({
  ready,
  signedIn,
  getToken,
}: {
  ready: boolean;
  signedIn: boolean;
  getToken: () => Promise<string | null>;
}) {
  const qc = useQueryClient();
  const { data: tickets = [] } = useQuery({
    queryKey: ["customer-support-tickets"],
    enabled: ready && signedIn,
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      return customerApi.listSupport(token);
    },
  });
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refreshTickets() {
    await qc.invalidateQueries({ queryKey: ["customer-support-tickets"] });
  }

  async function submitTicket(e: React.FormEvent) {
    e.preventDefault();
    if (!subject.trim()) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      await customerApi.createSupport(token, {
        subject: subject.trim(),
        description: description.trim() || undefined,
      });
      setSubject("");
      setDescription("");
      setMessage("Support request submitted.");
      await refreshTickets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit ticket");
    } finally {
      setBusy(false);
    }
  }

  async function exportPrivacy() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      const data = await customerApi.privacyExport(token);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "porterchain-privacy-export.json";
      a.click();
      URL.revokeObjectURL(url);
      setMessage("Privacy export downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(false);
    }
  }

  async function requestDelete() {
    if (!window.confirm("Request account deletion? This opens a 30-day hold for review.")) {
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      const res = await customerApi.privacyDeleteRequest(token);
      setMessage(`${res.message} Reference: ${res.reference}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <CustomerShell>
      <div className="mx-auto max-w-3xl space-y-4">
        <header>
          <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary/65">Account</p>
          <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-primary">Your account</h1>
        </header>

        {message ? (
          <p className="rounded-xl border border-secondary/20 bg-secondary/5 px-4 py-3 text-sm text-primary">
            {message}
          </p>
        ) : null}
        {error ? (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        ) : null}

        <AddressBook getToken={getToken} />

        <section className="rounded-3xl border border-primary/10 bg-white p-5">
          <h2 className="text-lg font-bold text-primary">Contact support</h2>
          <form onSubmit={submitTicket} className="mt-4 space-y-3">
            <label className="block text-sm">
              <span className="text-muted">Subject</span>
              <input
                className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              <span className="text-muted">Details</span>
              <textarea
                className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={busy}
              className="rounded-2xl border border-primary/20 px-4 py-2.5 text-sm font-bold text-primary disabled:opacity-60"
            >
              Submit ticket
            </button>
          </form>
          {tickets.length > 0 ? (
            <ul className="mt-5 space-y-2 border-t border-primary/8 pt-4">
              {tickets.map((t) => (
                <li
                  key={t.ticket_id}
                  className="flex items-center justify-between rounded-xl bg-gray-bg px-3 py-2 text-sm"
                >
                  <span className="font-medium text-primary">{t.subject}</span>
                  <span className="text-xs text-muted">{t.status}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </section>

        <section className="rounded-3xl border border-primary/10 bg-white p-5">
          <h2 className="text-lg font-bold text-primary">Privacy</h2>
          <p className="mt-1 text-sm text-primary/70">
            Download your data, or ask us to delete it. A person reviews each request, then it runs automatically.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => void exportPrivacy()}
              className="rounded-xl border border-primary/15 bg-white px-4 py-2.5 text-sm font-semibold text-primary hover:bg-gray-bg disabled:opacity-60"
            >
              Export my data
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void requestDelete()}
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700 disabled:opacity-60"
            >
              Request deletion
            </button>
          </div>
        </section>
      </div>
    </CustomerShell>
  );
}
