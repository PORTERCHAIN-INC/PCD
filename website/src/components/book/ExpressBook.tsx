"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useLocale } from "next-intl";
import {
  BOOKING_VEHICLES,
  MAX_DROPS,
  bookingText,
  buildQuoteInput,
  canAddDrop,
  formatPrice,
  isVehicle,
  payBlocker,
  type BookingLocale,
  type BookingCopyKey,
  type VehicleId,
} from "@porterchain/types/booking";
import { Link, useRouter } from "@/i18n/navigation";
import {
  expressCheckout,
  fastCreateQuote,
  fastGetQuote,
  fastPreview,
  mockCompleteCheckout,
  sendAgain,
  type FastApiError,
  type FastPreview,
  type FastQuote,
} from "@/lib/api";
import { getOrCreateVisitorId } from "@/lib/visitor-tracking";

const field =
  "mt-1.5 block w-full rounded-2xl border border-primary/15 bg-white px-4 py-3.5 text-base text-primary placeholder:text-primary/45 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15";
const labelCls = "block text-[13px] font-semibold uppercase tracking-wide text-primary/70";

/** Address history on this device only (no account needed): powers the "Recent" chips. */
const RECENT_KEY = "pc_recent_addresses";
function readRecent(): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
    return Array.isArray(raw) ? raw.filter((x) => typeof x === "string").slice(0, 6) : [];
  } catch {
    return [];
  }
}
function rememberRecent(addresses: string[]) {
  try {
    const merged = [...addresses, ...readRecent()]
      .filter((v, i, a) => v && a.indexOf(v) === i)
      .slice(0, 6);
    localStorage.setItem(RECENT_KEY, JSON.stringify(merged));
  } catch {
    /* private mode */
  }
}

type Mode = "form" | "locked";

export default function ExpressBook({
  initialPickup = "",
  initialDropoff = "",
  initialVehicle,
  quoteId,
  againToken,
}: {
  initialPickup?: string;
  initialDropoff?: string;
  initialVehicle?: string;
  quoteId?: string;
  againToken?: string;
}) {
  const locale = (useLocale() === "fr" ? "fr" : "en") as BookingLocale;
  const tx = (key: BookingCopyKey, vars?: Record<string, string | number>) =>
    bookingText(locale, key, vars);
  const router = useRouter();
  const startedAt = useRef<number>(0);
  const [mode, setMode] = useState<Mode>(quoteId || againToken ? "locked" : "form");
  const [pickup, setPickup] = useState(initialPickup);
  const [drops, setDrops] = useState<string[]>([initialDropoff]);
  const [vehicle, setVehicle] = useState<VehicleId>(
    isVehicle(initialVehicle) ? initialVehicle : "sedan_suv"
  );
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [marketing, setMarketing] = useState(false);
  const [honeypot, setHoneypot] = useState("");
  const [price, setPrice] = useState<FastPreview | null>(null);
  const [locked, setLocked] = useState<FastQuote | null>(null);
  const [pricing, setPricing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [recent, setRecent] = useState<string[]>([]);
  const [focus, setFocus] = useState<number | null>(null); // -1 = pickup, i = drop i

  useEffect(() => {
    startedAt.current = Date.now();
    setRecent(readRecent());
  }, []);

  // Resume a quote (Stripe cancel / calculator handoff) or a "Send again" email link.
  useEffect(() => {
    if (againToken) {
      sendAgain(againToken)
        .then((res) => {
          setLocked(res.quote);
          setName(res.contact.name || "");
          setEmail(res.contact.email || "");
          setPhone(res.contact.phone || "");
          setNotice(bookingText(locale, "sameTrip", { ref: res.source_tracking_number }));
        })
        .catch((e: FastApiError) => {
          setMode("form");
          setError(e.message);
        });
    } else if (quoteId) {
      fastGetQuote(quoteId)
        .then(setLocked)
        .catch(() => {
          setMode("form");
          setError(bookingText(locale, "expired"));
        });
    }
  }, [againToken, quoteId, locale]);

  const quoteInput = useMemo(
    () => buildQuoteInput({ pickup, drops, vehicle }),
    [pickup, drops, vehicle]
  );

  // Live price as they type (debounced). Does not create a quote.
  useEffect(() => {
    if (mode !== "form" || !quoteInput) {
      setPrice(null);
      return;
    }
    setPricing(true);
    const timer = window.setTimeout(() => {
      fastPreview(quoteInput)
        .then((p) => {
          setPrice(p);
          setError(null);
        })
        .catch((e: FastApiError) => {
          setPrice(null);
          setError(e.message);
        })
        .finally(() => setPricing(false));
    }, 350);
    return () => window.clearTimeout(timer);
  }, [mode, quoteInput]);

  const amount = locked?.amount_cents ?? price?.amount_cents ?? null;
  const hasTrip = mode === "locked" ? Boolean(locked) : Boolean(quoteInput);
  const blocker = payBlocker(
    { pickup, drops, vehicle, name, email, phone },
    amount !== null && hasTrip
  );

  async function pay(event: React.FormEvent) {
    event.preventDefault();
    if (blocker || busy) {
      if (blocker) setError(tx(blocker));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const sessionId = getOrCreateVisitorId();
      const quote =
        mode === "locked" && locked
          ? locked
          : await fastCreateQuote({ ...quoteInput!, anonymous_session_id: sessionId });
      const res = await expressCheckout({
        quote_id: quote.quote_id,
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        terms_accepted: true,
        privacy_accepted: true,
        dangerous_goods_confirmed: true,
        marketing_opt_in: marketing,
        anonymous_session_id: sessionId,
        website: honeypot,
        form_elapsed_ms: Date.now() - startedAt.current,
        locale,
      });
      if (mode === "form") rememberRecent([pickup.trim(), ...drops.map((d) => d.trim())]);
      try {
        sessionStorage.setItem("pc_book_started", String(startedAt.current));
      } catch {
        /* private mode */
      }
      if (res.checkout_url) {
        window.location.assign(res.checkout_url);
        return;
      }
      if (res.mock_checkout) {
        await mockCompleteCheckout(res.quote_id);
        router.push({ pathname: "/book/success", query: { quote_id: res.quote_id } });
        return;
      }
      setError(tx("payFailed"));
    } catch (e) {
      setError((e as FastApiError).message || tx("payFailed"));
    } finally {
      setBusy(false);
    }
  }

  const chips = (slot: number, value: string, set: (v: string) => void) =>
    focus === slot && recent.length > 0 && value.trim().length < 4 ? (
      <div className="mt-2 flex flex-wrap gap-2" aria-label={tx("recent")}>
        {recent.slice(0, 3).map((r) => (
          <button
            key={r}
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => set(r)}
            className="max-w-full truncate rounded-full border border-primary/15 bg-white px-3 py-1.5 text-xs font-semibold text-primary hover:border-primary/40"
          >
            {r}
          </button>
        ))}
      </div>
    ) : null;

  return (
    <form
      onSubmit={pay}
      noValidate
      className="mx-auto w-full max-w-xl pb-40 sm:pb-12"
      aria-labelledby="book-title"
    >
      <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary/65">
        {tx("eyebrow")}
      </p>
      <h1
        id="book-title"
        className="mt-2 text-4xl font-extrabold tracking-tight text-primary sm:text-5xl"
      >
        {tx("title")}
      </h1>
      <p className="mt-3 text-base text-primary/75">{tx("lead")}</p>

      {notice ? (
        <p
          role="status"
          className="mt-6 rounded-2xl bg-primary/5 px-4 py-3 text-sm font-medium text-primary"
        >
          {notice}
        </p>
      ) : null}

      {mode === "form" ? (
        <div className="mt-8 space-y-5">
          <label className={labelCls}>
            {tx("pickup")}
            <input
              className={field}
              value={pickup}
              onChange={(e) => setPickup(e.target.value)}
              onFocus={() => setFocus(-1)}
              onBlur={() => setFocus(null)}
              placeholder={tx("placeholder")}
              autoComplete="street-address"
              required
            />
          </label>
          {chips(-1, pickup, setPickup)}

          {drops.map((drop, i) => (
            <div key={i} data-testid={`drop-${i}`}>
              <div className="flex items-end justify-between">
                <label className={`${labelCls} w-full`}>
                  {drops.length > 1 ? tx("dropN", { n: i + 1 }) : tx("drop")}
                  <input
                    className={field}
                    value={drop}
                    onChange={(e) =>
                      setDrops((d) => d.map((x, j) => (j === i ? e.target.value : x)))
                    }
                    onFocus={() => setFocus(i)}
                    onBlur={() => setFocus(null)}
                    placeholder={tx("placeholder")}
                    autoComplete="off"
                    required
                  />
                </label>
                {drops.length > 1 ? (
                  <button
                    type="button"
                    onClick={() => setDrops((d) => d.filter((_, j) => j !== i))}
                    className="mb-3 ml-3 shrink-0 text-sm font-semibold text-primary/70 underline underline-offset-4"
                  >
                    {tx("removeDrop")}
                  </button>
                ) : null}
              </div>
              {chips(i, drop, (v) => setDrops((d) => d.map((x, j) => (j === i ? v : x))))}
            </div>
          ))}
          {canAddDrop(drops) ? (
            <button
              type="button"
              data-testid="add-drop"
              onClick={() => setDrops((d) => [...d, ""])}
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
            <legend className={labelCls}>{tx("vehicle")}</legend>
            <div className="mt-1.5 grid grid-cols-3 gap-2" role="radiogroup">
              {BOOKING_VEHICLES.map((v) => (
                <label
                  key={v.id}
                  className={`cursor-pointer rounded-2xl border px-3 py-3 text-center transition ${
                    vehicle === v.id
                      ? "border-primary bg-primary text-white"
                      : "border-primary/15 bg-white text-primary hover:border-primary/40"
                  }`}
                >
                  <input
                    type="radio"
                    name="vehicle"
                    value={v.id}
                    checked={vehicle === v.id}
                    onChange={() => setVehicle(v.id)}
                    className="sr-only"
                  />
                  <span className="block text-base font-bold">{v.label[locale]}</span>
                  <span
                    className={`block text-xs ${vehicle === v.id ? "text-white/85" : "text-primary/65"}`}
                  >
                    {v.hint[locale]}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      ) : (
        <div className="mt-8 rounded-3xl border border-primary/10 bg-white p-5" aria-busy={!locked}>
          {locked ? (
            <dl className="space-y-2 text-sm text-primary">
              <div className="flex justify-between gap-4">
                <dt className="text-primary/65">{tx("pickup")}</dt>
                <dd className="text-right font-medium">{locked.pickup?.formatted}</dd>
              </div>
              {(locked.additional_stops ?? []).map((s, i) => (
                <div key={i} className="flex justify-between gap-4">
                  <dt className="text-primary/65">{tx("dropN", { n: i + 1 })}</dt>
                  <dd className="text-right font-medium">{s.formatted}</dd>
                </div>
              ))}
              <div className="flex justify-between gap-4">
                <dt className="text-primary/65">{tx("drop")}</dt>
                <dd className="text-right font-medium">{locked.dropoff?.formatted}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-primary/70">{tx("loading")}</p>
          )}
          <button
            type="button"
            onClick={() => {
              setMode("form");
              setPickup(locked?.pickup?.formatted ?? "");
              setDrops([
                ...(locked?.additional_stops ?? []).map((s) => s.formatted ?? ""),
                locked?.dropoff?.formatted ?? "",
              ]);
              setLocked(null);
            }}
            className="mt-3 text-sm font-semibold text-primary underline underline-offset-4"
          >
            {tx("changeTrip")}
          </button>
        </div>
      )}

      <div className="mt-8 space-y-5">
        <label className={labelCls}>
          {tx("name")}
          <input
            className={field}
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            required
          />
        </label>
        <div className="grid gap-5 sm:grid-cols-2">
          <label className={labelCls}>
            {tx("email")}
            <input
              type="email"
              inputMode="email"
              className={field}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label className={labelCls}>
            {tx("phone")}
            <input
              type="tel"
              inputMode="tel"
              className={field}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoComplete="tel"
              required
            />
          </label>
        </div>
        {/* Honeypot: hidden from people and assistive tech; bots fill it. */}
        <div aria-hidden="true" className="absolute -left-[10000px] h-px w-px overflow-hidden">
          <label>
            Website
            <input
              tabIndex={-1}
              autoComplete="off"
              name="website"
              value={honeypot}
              onChange={(e) => setHoneypot(e.target.value)}
            />
          </label>
        </div>
        <label className="flex items-start gap-3 text-sm text-primary/85">
          <input
            type="checkbox"
            className="mt-0.5 h-5 w-5 shrink-0 accent-[var(--primary)]"
            checked={marketing}
            onChange={(e) => setMarketing(e.target.checked)}
          />
          <span>
            {tx("marketing")} <span className="text-primary/65">{tx("optional")}</span>
          </span>
        </label>
      </div>

      {error ? (
        <p
          role="alert"
          className="mt-6 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800"
        >
          {error}
        </p>
      ) : null}

      {/* Sticky pay bar on phones; inline on desktop. The only primary action on the page. */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-primary/10 bg-white/95 px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur sm:static sm:mt-8 sm:border-0 sm:bg-transparent sm:p-0">
        <div className="mx-auto max-w-xl">
          <button
            type="submit"
            disabled={busy}
            data-testid="express-pay"
            className="flex w-full items-center justify-between rounded-2xl bg-primary px-6 py-4 text-left text-white shadow-lg shadow-primary/20 transition hover:bg-primary/90 disabled:opacity-60"
          >
            <span className="text-base font-bold">{busy ? tx("paying") : tx("pay")}</span>
            <span
              className="text-2xl font-extrabold tabular-nums"
              aria-live="polite"
              data-testid="express-price"
            >
              {amount !== null ? formatPrice(amount, locale) : pricing ? "…" : "—"}
            </span>
          </button>
          <p className="mt-2 text-center text-xs text-primary/70">
            {tx("legal")}{" "}
            <Link href="/terms" className="underline">
              {tx("terms")}
            </Link>
            {" · "}
            <Link href="/privacy" className="underline">
              {tx("privacy")}
            </Link>
          </p>
        </div>
      </div>
    </form>
  );
}
