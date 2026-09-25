"use client";

import Link from "next/link";
import { useState } from "react";
import Button from "@/components/ui/Button";
import { settingsApi } from "@/lib/settings";

export function RecipientsTab({
  recipients,
  onRefresh,
  getToken,
  orgId,
}: {
  recipients: Array<{ id: string; name: string; email?: string | null; phone?: string | null }>;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const add = async () => {
    if (!name.trim()) return;
    const token = await getToken();
    await settingsApi.addRecipient(
      token,
      { name, email: email || undefined, phone: phone || undefined },
      orgId
    );
    setName("");
    setEmail("");
    setPhone("");
    await onRefresh();
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Delivery contacts</h2>
      <p className="mt-1 text-sm text-muted">
        Saved consignees for booking and CSV import. Portal seats live on{" "}
        <Link href="/team" className="font-medium text-secondary underline">
          Team
        </Link>
        .
      </p>
      <ul className="mt-4 space-y-2 text-sm">
        {recipients.length === 0 && <li className="text-muted">No recipients yet</li>}
        {recipients.map((r) => (
          <li key={r.id} className="flex justify-between border-b border-primary/5 py-2">
            <span>
              <span className="font-medium">{r.name}</span>
              {r.email && <span className="ml-2 text-muted">{r.email}</span>}
            </span>
            {r.phone && <span className="text-muted">{r.phone}</span>}
            <button
              type="button"
              className="text-xs text-red-600"
              onClick={() =>
                void getToken().then((t) =>
                  settingsApi.deleteRecipient(t, r.id, orgId).then(onRefresh)
                )
              }
            >
              Remove
            </button>
          </li>
        ))}
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
          placeholder="Phone"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <Button size="sm" onClick={() => void add()}>
          Add recipient
        </Button>
      </div>
    </section>
  );
}
