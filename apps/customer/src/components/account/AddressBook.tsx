"use client";

import { useEffect, useState } from "react";
import { accountApi, type SavedAddress } from "@/lib/account";

/** Saved places (Home, Office…) plus addresses learned from past deliveries. */
export default function AddressBook({ getToken }: { getToken: () => Promise<string | null> }) {
  const [items, setItems] = useState<SavedAddress[]>([]);
  const [formatted, setFormatted] = useState("");
  const [label, setLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [prefsUrl, setPrefsUrl] = useState<string | null>(null);

  async function load() {
    const t = await getToken();
    if (!t) return;
    setItems(await accountApi.addresses(t).catch(() => []));
    accountApi.preferencesLink(t).then((r) => setPrefsUrl(r.url)).catch(() => undefined);
  }
  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const t = (await getToken()) ?? "";
      await accountApi.saveAddress(t, { formatted, label: label || null });
      setFormatted("");
      setLabel("");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    const t = (await getToken()) ?? "";
    await accountApi.deleteAddress(t, id).catch((err: Error) => setError(err.message));
    await load();
  }

  return (
    <>
      <section className="rounded-3xl border border-primary/10 bg-white p-5" data-testid="address-book">
        <h2 className="text-lg font-bold text-primary">Addresses</h2>
        <p className="mt-1 text-sm text-primary/70">Saved places fill in automatically when you send.</p>
        <ul className="mt-4 divide-y divide-primary/10">
          {items.map((a) => (
            <li key={a.id} className="flex items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-primary">
                  {a.label ? <span className="mr-2 text-secondary">{a.label}</span> : null}
                  {a.formatted}
                </p>
                <p className="text-xs text-primary/65">{a.saved ? "Saved" : `Used ${a.use_count}×`}</p>
              </div>
              {a.saved ? (
                <button type="button" onClick={() => void remove(a.id)} className="text-sm font-semibold text-primary/70 underline underline-offset-4">
                  Remove
                </button>
              ) : null}
            </li>
          ))}
          {items.length === 0 ? <li className="py-3 text-sm text-primary/70">No addresses yet.</li> : null}
        </ul>
        <form onSubmit={save} className="mt-4 grid gap-2 sm:grid-cols-[8rem_1fr_auto]">
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Label"
            aria-label="Label"
            maxLength={64}
            className="rounded-2xl border border-primary/15 px-4 py-3 text-sm text-primary outline-none focus:border-primary"
          />
          <input
            value={formatted}
            onChange={(e) => setFormatted(e.target.value)}
            placeholder="Street, city, postal code"
            aria-label="Address"
            className="rounded-2xl border border-primary/15 px-4 py-3 text-sm text-primary outline-none focus:border-primary"
          />
          <button type="submit" disabled={busy || formatted.trim().length < 5} className="rounded-2xl border border-primary/20 px-4 py-3 text-sm font-bold text-primary disabled:opacity-50">
            Save
          </button>
        </form>
        {error ? <p role="alert" className="mt-2 text-sm text-red-800">{error}</p> : null}
      </section>
      <section className="rounded-3xl border border-primary/10 bg-white p-5">
        <h2 className="text-lg font-bold text-primary">Email</h2>
        <p className="mt-1 text-sm text-primary/70">Choose which emails you get. Delivery updates stay on by default.</p>
        {prefsUrl ? (
          <a href={prefsUrl} className="mt-3 inline-flex text-sm font-bold text-primary underline underline-offset-4">
            Email preferences
          </a>
        ) : null}
      </section>
    </>
  );
}
