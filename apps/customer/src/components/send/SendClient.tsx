"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  BOOKING_VEHICLES,
  MAX_DROPS,
  bookingText,
  buildQuoteInput,
  canAddDrop,
  formatPrice,
  isPhone,
  type BookingCopyKey,
  type VehicleId,
} from "@porterchain/types/booking";
import { AddressAutocompleteInput, GoogleMapsProvider } from "@porterchain/maps";
import CustomerShell from "@/components/CustomerShell";
import { publicEnv } from "@/lib/env";
import PortalAuth, { type PortalAuthValue } from "@/components/auth/PortalAuth";
import { accountApi, type SavedAddress } from "@/lib/account";
import { createQuote, getQuote, mockCompleteCheckout, previewQuote, startBooking } from "@/lib/booking";

const tx = (key: BookingCopyKey, vars?: Record<string, string | number>) => bookingText("en", key, vars);
const field =
  "mt-1.5 block w-full rounded-2xl border border-primary/15 bg-white px-4 py-3.5 text-base text-primary placeholder:text-primary/45 outline-none focus:border-primary focus:ring-2 focus:ring-primary/15";
const labelCls = "block text-[13px] font-semibold uppercase tracking-wide text-primary/70";
const PHONE_KEY = "pc_customer_phone";

export default function SendClient() {
  return (
    <CustomerShell>
      <GoogleMapsProvider apiKey={publicEnv.googleMapsApiKey}>
        <PortalAuth>{(auth) => <SendBody auth={auth} />}</PortalAuth>
      </GoogleMapsProvider>
    </CustomerShell>
  );
}

/** Send: the signed-in booking screen. Same shared rules as the website, plus the address book. */
function SendBody({ auth }: { auth: PortalAuthValue }) {
  const router = useRouter();
  const params = useSearchParams();
  const resumeId = params.get("quote_id");
  const [pickup, setPickup] = useState("");
  const [drops, setDrops] = useState<string[]>([""]);
  const [vehicle, setVehicle] = useState<VehicleId>("sedan_suv");
  const [phone, setPhone] = useState("");
  const [book, setBook] = useState<SavedAddress[]>([]);
  const [focus, setFocus] = useState<number | null>(null);
  const [amount, setAmount] = useState<number | null>(null);
  const [resumed, setResumed] = useState<string | null>(null);
  const [pricing, setPricing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loaded = useRef(false);

  useEffect(() => {
    setPhone(auth.phone || localStorage.getItem(PHONE_KEY) || "");
  }, [auth.phone]);

  // Address book + history autofill (saved first, then most used).
  useEffect(() => {
    if (!auth.ready || loaded.current) return;
    loaded.current = true;
    void (async () => {
      const token = await auth.getToken();
      if (!token) return;
      const items = await accountApi.suggestions(token).catch(() => []);
      setBook(items);
      if (!resumeId && items[0]) setPickup((p) => p || items[0].formatted);
    })();
  }, [auth, resumeId]);

  // Stripe "back" → resume the same quote.
  useEffect(() => {
    if (!resumeId) return;
    getQuote(resumeId)
      .then((q) => {
        setPickup(q.pickup?.formatted ?? "");
        setDrops([q.dropoff?.formatted ?? ""]);
        setResumed(resumeId);
        setAmount(q.amount_cents);
      })
      .catch(() => setError(tx("expired")));
  }, [resumeId]);

  const input = useMemo(() => buildQuoteInput({ pickup, drops, vehicle }), [pickup, drops, vehicle]);

  useEffect(() => {
    if (!input) {
      if (!resumed) setAmount(null);
      return;
    }
    setResumed(null);
    setPricing(true);
    const timer = window.setTimeout(() => {
      previewQuote({ ...input, booking_mode: "vehicle", schedule_mode: "now" })
        .then((p) => {
          setAmount(p.amount_cents);
          setError(null);
        })
        .catch(() => setAmount(null))
        .finally(() => setPricing(false));
    }, 350);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input]);

  async function pay(e: React.FormEvent) {
    e.preventDefault();
    if (amount === null || (!input && !resumed)) return setError(tx("needTrip"));
    if (!isPhone(phone)) return setError("Add a phone number so the driver can reach you.");
    setBusy(true);
    setError(null);
    try {
      const token = await auth.getToken();
      if (!token) throw new Error("Sign in again to continue.");
      const quoteId = resumed ?? (await createQuote({ ...input!, booking_mode: "vehicle", schedule_mode: "now" })).quote_id;
      localStorage.setItem(PHONE_KEY, phone.trim());
      const booking = await startBooking(token, {
        quote_id: quoteId,
        email: auth.email,
        phone: phone.trim(),
        clerk_user_id: auth.userId ?? "",
        terms_accepted: true,
        privacy_accepted: true,
        dangerous_goods_confirmed: true,
        consent_at: new Date().toISOString(),
      });
      if (booking.checkout_url) {
        window.location.href = booking.checkout_url;
        return;
      }
      if (booking.mock_checkout) {
        const done = await mockCompleteCheckout(quoteId);
        router.push(`/orders?booked=${encodeURIComponent(done.tracking_number)}`);
        return;
      }
      throw new Error(tx("payFailed"));
    } catch (err) {
      setError(err instanceof Error && err.message.length < 140 ? err.message : tx("payFailed"));
    } finally {
      setBusy(false);
    }
  }

  const chips = (slot: number, value: string, set: (v: string) => void) =>
    focus === slot && book.length > 0 && value.trim().length < 4 ? (
      <div className="mt-2 flex flex-wrap gap-2" data-testid={`autofill-${slot}`}>
        {book.slice(0, 4).map((a) => (
          <button
            key={a.id}
            type="button"
            onMouseDown={(ev) => ev.preventDefault()}
            onClick={() => set(a.formatted)}
            className="max-w-full truncate rounded-full border border-primary/15 bg-white px-3 py-1.5 text-xs font-semibold text-primary hover:border-primary/40"
          >
            {a.label ? <span className="mr-1 text-secondary">{a.label}</span> : null}
            {a.formatted}
          </button>
        ))}
      </div>
    ) : null;

  return (
    <form onSubmit={pay} noValidate className="mx-auto w-full max-w-xl pb-44 md:pb-10" aria-labelledby="send-title">
      <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary/65">Send</p>
      <h1 id="send-title" className="mt-2 text-4xl font-extrabold tracking-tight text-primary">
        Where to?
      </h1>

      <div className="mt-8 space-y-5">
        <div className={labelCls} onFocus={() => setFocus(-1)} onBlur={() => setFocus(null)}>
          <label htmlFor="send-pickup">{tx("pickup")}</label>
          <AddressAutocompleteInput
            id="send-pickup"
            value={pickup}
            onChange={setPickup}
            onPlaceSelect={(a) => setPickup(a.formatted)}
            placeholder={tx("placeholder")}
            apiKey={publicEnv.googleMapsApiKey}
            className={field}
            fallbackClassName={field}
          />
        </div>
        {chips(-1, pickup, setPickup)}
        {drops.map((d, i) => (
          <div key={i}>
            <div className="flex items-end">
              <div className={`${labelCls} w-full`} onFocus={() => setFocus(i)} onBlur={() => setFocus(null)}>
                <label htmlFor={`send-drop-${i}`}>{drops.length > 1 ? tx("dropN", { n: i + 1 }) : tx("drop")}</label>
                <AddressAutocompleteInput
                  id={`send-drop-${i}`}
                  value={d}
                  onChange={(v) => setDrops((x) => x.map((y, j) => (j === i ? v : y)))}
                  onPlaceSelect={(a) => setDrops((x) => x.map((y, j) => (j === i ? a.formatted : y)))}
                  placeholder={tx("placeholder")}
                  apiKey={publicEnv.googleMapsApiKey}
                  className={field}
                  fallbackClassName={field}
                />
              </div>
              {drops.length > 1 ? (
                <button
                  type="button"
                  onClick={() => setDrops((x) => x.filter((_, j) => j !== i))}
                  className="mb-3 ml-3 text-sm font-semibold text-primary/70 underline underline-offset-4"
                >
                  {tx("removeDrop")}
                </button>
              ) : null}
            </div>
            {chips(i, d, (v) => setDrops((x) => x.map((y, j) => (j === i ? v : y))))}
          </div>
        ))}
        {canAddDrop(drops) ? (
          <button
            type="button"
            onClick={() => setDrops((x) => [...x, ""])}
            data-testid="send-add-drop"
            className="text-sm font-bold text-primary underline underline-offset-4"
          >
            + {tx("addDrop")} <span className="font-medium text-primary/65">({drops.length}/{MAX_DROPS})</span>
          </button>
        ) : (
          <p className="text-sm text-primary/70">{tx("dropsLimit")}</p>
        )}
        <fieldset>
          <legend className={labelCls}>{tx("vehicle")}</legend>
          <div className="mt-1.5 grid grid-cols-3 gap-2">
            {BOOKING_VEHICLES.map((v) => (
              <button
                type="button"
                key={v.id}
                aria-pressed={vehicle === v.id}
                aria-current={vehicle === v.id ? "true" : undefined}
                onClick={() => setVehicle(v.id)}
                className={`rounded-2xl border px-3 py-3 text-center focus-visible:ring-2 focus-visible:ring-secondary ${
                  vehicle === v.id ? "border-primary bg-primary text-white" : "border-primary/15 bg-white text-primary"
                }`}
              >
                <span className="block text-base font-bold">{v.label.en}</span>
                <span className={`block text-xs ${vehicle === v.id ? "text-white/85" : "text-primary/65"}`}>{v.hint.en}</span>
              </button>
            ))}
          </div>
        </fieldset>
        {!auth.phone ? (
          <label className={labelCls}>
            {tx("phone")}
            <input type="tel" inputMode="tel" className={field} value={phone} onChange={(e) => setPhone(e.target.value)} autoComplete="tel" />
          </label>
        ) : null}
      </div>

      {error ? (
        <p role="alert" className="mt-6 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
          {error}
        </p>
      ) : null}

      <div className="fixed inset-x-0 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-30 border-t border-primary/10 bg-white/95 px-4 py-3 backdrop-blur md:static md:mt-8 md:border-0 md:bg-transparent md:p-0">
        <div className="mx-auto max-w-xl">
          <button
            type="submit"
            disabled={busy}
            data-testid="send-pay"
            className="flex w-full items-center justify-between rounded-2xl bg-primary px-6 py-4 text-white shadow-lg shadow-primary/20 focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2 disabled:opacity-60"
          >
            <span className="text-base font-bold">{busy ? tx("paying") : tx("pay")}</span>
            <span className="text-2xl font-extrabold tabular-nums" aria-live="polite" data-testid="send-price">
              {amount !== null ? formatPrice(amount) : pricing ? "…" : "—"}
            </span>
          </button>
          <p className="mt-2 text-center text-xs text-primary/70">Incl. HST. Card, Apple Pay or Google Pay.</p>
        </div>
      </div>
    </form>
  );
}
