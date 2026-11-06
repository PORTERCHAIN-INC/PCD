"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  MAX_DROPS,
  bookingText,
  buildQuoteInput,
  canAddDrop,
  formatPrice,
  isPhone,
  type BookingCopyKey,
  type VehicleId,
} from "@porterchain/types/booking";
import { AddressAutocompleteInput, useAddressIQ } from "@porterchain/maps";
import {
  normalizeDeliveryOptions,
  type DeliveryOptions,
} from "@porterchain/types/delivery-options";
import { DeliveryOptionsFields } from "@porterchain/ui/delivery-options-fields";
import CustomerShell from "@/components/CustomerShell";
import PortalAuth, { type PortalAuthValue } from "@/components/auth/PortalAuth";
import { accountApi, type SavedAddress } from "@/lib/account";
import { ACCEPT, attachAll, stashFiles, type PendingFile } from "@/lib/attachments";
import {
  createQuote,
  getQuote,
  mockCompleteCheckout,
  previewQuote,
  startBooking,
} from "@/lib/booking";

const tx = (key: BookingCopyKey, vars?: Record<string, string | number>) =>
  bookingText("en", key, vars);
const field =
  "mt-1.5 block w-full rounded-2xl border border-primary/15 bg-white px-4 py-3.5 text-base text-primary placeholder:text-primary/45 outline-none focus:border-primary focus:ring-2 focus:ring-primary/15";
const labelCls = "block text-[13px] font-semibold uppercase tracking-wide text-primary/70";
const PHONE_KEY = "pc_customer_phone";

export default function SendClient() {
  return (
    <CustomerShell>
      <>
        <PortalAuth>{(auth) => <SendBody auth={auth} />}</PortalAuth>
      </>
    </CustomerShell>
  );
}

type ParcelRow = { qty: string; l: string; w: string; h: string; lb: string };
const emptyRow = (): ParcelRow => ({ qty: "1", l: "", w: "", h: "", lb: "" });

function parcelsPayload(rows: ParcelRow[]) {
  const out = rows
    .map((r) => ({
      preset_id: "other",
      quantity: Math.max(1, Math.floor(Number(r.qty) || 1)),
      length_in: Number(r.l),
      width_in: Number(r.w),
      height_in: Number(r.h),
      weight_lb: Number(r.lb),
    }))
    .filter((p) => p.length_in > 0 && p.width_in > 0 && p.height_in > 0 && p.weight_lb > 0);
  return out.length ? out : null;
}

/** Send: the signed-in booking screen. Same shared rules as the website, plus the address book. */
function SendBody({ auth }: { auth: PortalAuthValue }) {
  const router = useRouter();
  const params = useSearchParams();
  const resumeId = params.get("quote_id");
  const [docs, setDocs] = useState<PendingFile[]>([]);
  const [pickup, setPickup] = useState("");
  const [drops, setDrops] = useState<string[]>([""]);
  // Ravi 2026-10-31: customers pay per parcel ($6 small / $9 larger + size/weight handling).
  // PorterChain picks the vehicle; there is no vehicle picker.
  const vehicle: VehicleId = "cargo_van" as VehicleId;
  const [items, setItems] = useState<ParcelRow[]>([emptyRow()]);
  const [phone, setPhone] = useState("");
  const [dlv, setDlv] = useState<DeliveryOptions>({});
  const [book, setBook] = useState<SavedAddress[]>([]);
  const [focus, setFocus] = useState<number | null>(null);
  const [amount, setAmount] = useState<number | null>(null);
  const [customQuote, setCustomQuote] = useState<string | null>(null);
  const [resumed, setResumed] = useState<string | null>(null);
  const [pricing, setPricing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loaded = useRef(false);
  // Address IQ: texts picked from suggestions / the review modal are pinned and skip geo_resolve.
  const pinned = useRef<Set<string>>(new Set());
  const iq = useAddressIQ();

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

  const input = useMemo(() => {
    const base = buildQuoteInput({ pickup, drops, vehicle });
    const parcels = parcelsPayload(items);
    return base && parcels ? { ...base, parcels } : null;
  }, [pickup, drops, vehicle, items]);

  useEffect(() => {
    if (!input) {
      if (!resumed) setAmount(null);
      return;
    }
    setResumed(null);
    setPricing(true);
    const timer = window.setTimeout(() => {
      previewQuote({ ...input, booking_mode: "parcels", schedule_mode: "now" })
        .then((p) => {
          setAmount(p.amount_cents);
          setCustomQuote(null);
          setError(null);
        })
        .catch((err: unknown) => {
          setAmount(null);
          const msg = err instanceof Error ? err.message : "";
          // L133: over the size/weight table → tell the customer plainly instead of a bare "—".
          setCustomQuote(
            msg.startsWith("manual_quote_required")
              ? `This parcel needs a custom quote (${msg.split(":").slice(1).join(":").replace(/ x /g, " × ") || "over 150 lb or over 90 × 50 in"}). We can't price it online — contact PorterChain and we'll quote it for you.`
              : null
          );
        })
        .finally(() => setPricing(false));
    }, 350);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input]);

  async function pay(e: React.FormEvent) {
    e.preventDefault();
    if (amount === null || (!input && !resumed)) return setError(tx("needTrip"));
    if (!isPhone(phone)) return setError("Add a phone number so the driver can reach you.");
    setError(null);
    if (!resumed) {
      // Same rule as merchant booking: a typed, unpicked address is resolved first;
      // unclear ones open the review popup instead of being silently guessed.
      const fields = [
        { key: "pickup", label: tx("pickup"), text: pickup },
        ...drops.map((d, i) => ({
          key: `drop-${i}`,
          label: drops.length > 1 ? tx("dropN", { n: i + 1 }) : tx("drop"),
          text: d,
        })),
      ].filter((f) => f.text.trim() && !pinned.current.has(f.text));
      if (fields.length) {
        const res = await iq.check(
          fields.map((f) => ({ key: f.key, label: f.label, address: { formatted: f.text } }))
        );
        if (!res) return setError("Confirm the address to continue.");
        let changed = false;
        const nextDrops = [...drops];
        let nextPickup = pickup;
        for (const f of fields) {
          const a = res[f.key];
          if (!a) continue;
          if (typeof a.lat === "number") pinned.current.add(a.formatted);
          if (a.formatted === f.text) continue;
          changed = true;
          if (f.key === "pickup") nextPickup = a.formatted;
          else nextDrops[Number(f.key.slice(5))] = a.formatted;
        }
        if (changed) {
          // Address text changed -> let the price refresh before paying.
          setPickup(nextPickup);
          setDrops(nextDrops);
          return setError("Address updated — check the price, then tap pay again.");
        }
      }
    }
    setBusy(true);
    try {
      const token = await auth.getToken();
      if (!token) throw new Error("Sign in again to continue.");
      const quoteId =
        resumed ??
        (
          await createQuote({
            ...input!,
            dropoff: { ...input!.dropoff, delivery_options: normalizeDeliveryOptions(dlv) },
            booking_mode: "parcels",
            schedule_mode: "now",
          })
        ).quote_id;
      localStorage.setItem(PHONE_KEY, phone.trim());
      const booking = await startBooking(token, {
        quote_id: quoteId,
        email: auth.email,
        phone: phone.trim(),
        auth_subject: auth.userId ?? "",
        terms_accepted: true,
        privacy_accepted: true,
        dangerous_goods_confirmed: true,
        consent_at: new Date().toISOString(),
      });
      if (docs.length) await stashFiles(quoteId, docs).catch(() => undefined);
      if (booking.checkout_url) {
        window.location.href = booking.checkout_url;
        return;
      }
      if (booking.mock_checkout) {
        const done = await mockCompleteCheckout(quoteId);
        if (docs.length) await attachAll(token, done.tracking_number, docs);
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
    <form
      onSubmit={pay}
      noValidate
      className="mx-auto w-full max-w-xl pb-44 md:pb-10"
      aria-labelledby="send-title"
    >
      {iq.modal}
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
            onPlaceSelect={(a) => {
              pinned.current.add(a.formatted);
              setPickup(a.formatted);
            }}
            placeholder={tx("placeholder")}
            className={field}
            fallbackClassName={field}
          />
        </div>
        {chips(-1, pickup, setPickup)}
        {drops.map((d, i) => (
          <div key={i}>
            <div className="flex items-end">
              <div
                className={`${labelCls} w-full`}
                onFocus={() => setFocus(i)}
                onBlur={() => setFocus(null)}
              >
                <label htmlFor={`send-drop-${i}`}>
                  {drops.length > 1 ? tx("dropN", { n: i + 1 }) : tx("drop")}
                </label>
                <AddressAutocompleteInput
                  id={`send-drop-${i}`}
                  value={d}
                  onChange={(v) => setDrops((x) => x.map((y, j) => (j === i ? v : y)))}
                  onPlaceSelect={(a) => {
                    pinned.current.add(a.formatted);
                    setDrops((x) => x.map((y, j) => (j === i ? a.formatted : y)));
                  }}
                  placeholder={tx("placeholder")}
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
            + {tx("addDrop")}{" "}
            <span className="font-medium text-primary/65">
              ({drops.length}/{MAX_DROPS})
            </span>
          </button>
        ) : (
          <p className="text-sm text-primary/70">{tx("dropsLimit")}</p>
        )}
        <fieldset>
          <legend className={labelCls}>Parcels</legend>
          <p className="mt-0.5 text-xs text-primary/65">
            $6 per small parcel (fits 20 × 14 × 14 in), $9 per larger parcel. Over 100 lb or 70 × 45
            in adds a handling charge; over 150 lb or 90 × 50 in needs a custom quote. Before HST.
          </p>
          {items.map((row, idx) => (
            <div key={idx} className="mt-2 grid grid-cols-5 gap-2">
              {(["qty", "l", "w", "h", "lb"] as const).map((k) => (
                <label key={k} className="text-xs text-primary/70">
                  {
                    { qty: "Qty", l: "Length in", w: "Width in", h: "Height in", lb: "Weight lb" }[
                      k
                    ]
                  }
                  <input
                    aria-label={`Parcel ${idx + 1} ${{ qty: "quantity", l: "length (in)", w: "width (in)", h: "height (in)", lb: "weight (lb)" }[k]}`}
                    type="number"
                    min={k === "qty" ? 1 : 0}
                    step="any"
                    inputMode="decimal"
                    className="mt-0.5 w-full rounded-xl border border-primary/15 px-2 py-2 text-sm"
                    value={row[k]}
                    onChange={(e) =>
                      setItems((cur) =>
                        cur.map((r, i2) => (i2 === idx ? { ...r, [k]: e.target.value } : r))
                      )
                    }
                  />
                </label>
              ))}
            </div>
          ))}
          <button
            type="button"
            className="mt-2 text-sm font-bold text-primary underline underline-offset-4"
            onClick={() => setItems((cur) => [...cur, emptyRow()])}
          >
            + Add another parcel size
          </button>
        </fieldset>
        {!auth.phone ? (
          <label className={labelCls}>
            {tx("phone")}
            <input
              type="tel"
              inputMode="tel"
              className={field}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoComplete="tel"
            />
          </label>
        ) : null}
        <details
          className="rounded-2xl border border-primary/10 p-3"
          data-testid="send-delivery-options"
        >
          <summary className="cursor-pointer text-sm font-semibold text-primary">
            Delivery instructions (optional)
          </summary>
          <DeliveryOptionsFields
            className="mt-3"
            value={dlv}
            onChange={setDlv}
            idPrefix="send-dlv"
            hideFlags={["load_help"]}
          />
        </details>
      </div>

      <div
        className="mt-6 rounded-2xl border border-dashed border-primary/20 p-4 text-sm"
        data-testid="send-docs"
      >
        <p className="font-bold text-primary">Pickup documents (optional)</p>
        <p className="text-primary/65">
          E.g. a pickup authorization the driver must show. Only your driver can open it.
        </p>
        {docs.map((d, i) => (
          <p key={i} className="mt-1 flex items-center gap-3">
            <span className="font-semibold">{d.file.name}</span>
            <button
              type="button"
              className="text-xs text-red-600"
              onClick={() => setDocs(docs.filter((_, j) => j !== i))}
            >
              Remove
            </button>
          </p>
        ))}
        <label className="mt-2 inline-block cursor-pointer font-semibold text-secondary">
          + Attach document or photo
          <input
            type="file"
            accept={ACCEPT}
            multiple
            hidden
            onChange={(e) =>
              setDocs(
                [
                  ...docs,
                  ...Array.from(e.target.files ?? [])
                    .filter((f) => f.size <= 10 * 1024 * 1024)
                    .map((file) => ({ file, required: true })),
                ].slice(0, 10)
              )
            }
          />
        </label>
      </div>

      {customQuote ? (
        <p
          role="status"
          data-testid="send-custom-quote"
          className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900"
        >
          {customQuote}
        </p>
      ) : null}
      {error ? (
        <p
          role="alert"
          className="mt-6 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800"
        >
          {error}
        </p>
      ) : null}

      <div className="fixed inset-x-0 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-30 border-t border-primary/10 bg-white/95 px-4 py-3 backdrop-blur md:static md:mt-8 md:border-0 md:bg-transparent md:p-0">
        <div className="mx-auto max-w-xl">
          <button
            type="submit"
            disabled={busy || Boolean(customQuote)}
            data-testid="send-pay"
            className="flex w-full items-center justify-between rounded-2xl bg-primary px-6 py-4 text-white shadow-lg shadow-primary/20 focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2 disabled:opacity-60"
          >
            <span className="text-base font-bold">{busy ? tx("paying") : tx("pay")}</span>
            <span
              className="text-2xl font-extrabold tabular-nums"
              aria-live="polite"
              data-testid="send-price"
            >
              {amount !== null
                ? formatPrice(amount)
                : pricing
                  ? "…"
                  : customQuote
                    ? "Custom quote"
                    : "—"}
            </span>
          </button>
          <p className="mt-2 text-center text-xs text-primary/70">Card, Apple Pay or Google Pay.</p>
        </div>
      </div>
    </form>
  );
}
