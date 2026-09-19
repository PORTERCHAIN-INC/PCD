"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import { settingsApi, type BillingContact } from "@/lib/settings";

export function BillingContactsPanel({
  contacts,
  onRefresh,
  getToken,
  orgId,
}: {
  contacts: BillingContact[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const add = async () => {
    const token = await getToken();
    await settingsApi.addBillingContact(
      token,
      { name, email, phone: phone.trim() || undefined },
      orgId
    );
    setName("");
    setEmail("");
    setPhone("");
    await onRefresh();
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Billing contacts</h2>
      <p className="mt-1 text-sm text-muted">
        Invoices go to the primary AP contact. A phone number means we can call about a payment
        instead of only emailing.
      </p>
      <ul className="mt-4 space-y-2 text-sm">
        {contacts.map((c) => (
          <li key={c.id} className="flex justify-between gap-2">
            <span>
              {c.name} · {c.email}
              {c.phone ? <span className="text-muted"> · {c.phone}</span> : null}
              {c.is_primary && (
                <span className="ml-2 rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-secondary">
                  Primary AP
                </span>
              )}
            </span>
            <span className="flex gap-2">
              {!c.is_primary && (
                <button
                  type="button"
                  className="text-xs text-secondary"
                  onClick={() =>
                    void getToken().then((t) =>
                      settingsApi
                        .patchBillingContact(t, c.id, { is_primary: true }, orgId)
                        .then(onRefresh)
                    )
                  }
                >
                  Set primary
                </button>
              )}
              <button
                type="button"
                className="text-xs text-red-600"
                onClick={() =>
                  void getToken().then((t) =>
                    settingsApi.deleteBillingContact(t, c.id, orgId).then(onRefresh)
                  )
                }
              >
                Remove
              </button>
            </span>
          </li>
        ))}
        {contacts.length === 0 && <li className="text-muted">No billing contacts yet</li>}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          type="tel"
          placeholder="Phone (optional)"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <Button size="sm" onClick={() => void add()}>
          Add contact
        </Button>
      </div>
    </section>
  );
}
