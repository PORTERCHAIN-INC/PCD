"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { SignIn, SignOutButton, useAuth, useUser } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import Button from "@/components/ui/Button";
import { getAnonymousSessionId } from "@/lib/anonymous-session";
import { clearBookingDraftHint } from "@/lib/booking-draft-hint";
import { isClerkConfigured } from "@/lib/env";
import {
  cancelBookingDraft,
  getActiveBookingDraft,
  getQuote,
  mockCompleteCheckout,
  startBooking,
  type QuoteResult,
} from "@/lib/api";
import { fetchAuthMe } from "@/lib/auth";

export default function BookContinuePage() {
  return (
    <Suspense
      fallback={
        <SiteShell>
          <Container className="py-16 md:py-24 max-w-lg">
            <p className="type-small text-muted">Loading…</p>
          </Container>
        </SiteShell>
      }
    >
      <BookContinueContent />
    </Suspense>
  );
}

function BookContinueContent() {
  const t = useTranslations("booking.checkout");
  const router = useRouter();
  const searchParams = useSearchParams();
  const quoteId = searchParams.get("quote_id") ?? "";
  const draftId = searchParams.get("draft_id") ?? "";
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const { user } = useUser();
  const [loading, setLoading] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [quote, setQuote] = useState<QuoteResult | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);

  const [terms, setTerms] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  const [dangerous, setDangerous] = useState(false);
  const [staffPortal, setStaffPortal] = useState<string | null>(null);

  const clerkConfigured = isClerkConfigured();

  // Preserve the exact URL (locale + quote_id) so Clerk returns the customer
  // straight back into checkout instead of dropping them on the home page.
  const returnUrl = useMemo(() => {
    if (typeof window === "undefined") return undefined;
    return window.location.pathname + window.location.search;
  }, []);

  // Restore booking draft from quote_id or recover the latest active server draft.
  useEffect(() => {
    let cancelled = false;

    async function restore() {
      if (quoteId) {
        try {
          const q = await getQuote(quoteId);
          if (!cancelled) setQuote(q);
        } catch (err) {
          if (!cancelled) setQuoteError(err instanceof Error ? err.message : "Quote not found");
        }
        return;
      }

      try {
        const token = clerkConfigured && isLoaded && isSignedIn ? await getToken() : undefined;
        const draft = await getActiveBookingDraft(getAnonymousSessionId(), token ?? undefined);
        if (cancelled) return;
        if (!draft) {
          clearBookingDraftHint();
          if (!cancelled) setQuoteError("No active booking draft found");
          return;
        }
        if (draft.quote_id) {
          const q = await getQuote(draft.quote_id);
          if (!cancelled) setQuote(q);
          if (!cancelled && !draftId) {
            router.replace(`/book/continue?quote_id=${draft.quote_id}&draft_id=${draft.draft_id}`);
          }
        }
      } catch {
        if (!cancelled) setQuoteError("No active booking draft found");
      }
    }

    restore();
    return () => {
      cancelled = true;
    };
  }, [quoteId, draftId, clerkConfigured, isLoaded, isSignedIn, getToken, router]);

  // Retail checkout requires a customer Clerk identity — block staff/merchant/driver accounts.
  useEffect(() => {
    if (!clerkConfigured || !isLoaded || !isSignedIn) {
      setStaffPortal(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const token = await getToken();
        if (!token || cancelled) return;
        const me = await fetchAuthMe(token);
        if (cancelled) return;
        const type = me.user_type.toLowerCase();
        if (type !== "customer") {
          setStaffPortal(type);
        } else {
          setStaffPortal(null);
        }
      } catch {
        if (!cancelled) setStaffPortal(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [clerkConfigured, getToken, isLoaded, isSignedIn]);

  function resolveContact(): { email: string; phone: string } {
    if (!clerkConfigured) {
      return { email: "dev@porterchain.com", phone: "+10000000000" };
    }
    const email =
      user?.primaryEmailAddress?.emailAddress ?? user?.emailAddresses?.[0]?.emailAddress ?? "";
    const phone =
      user?.primaryPhoneNumber?.phoneNumber ?? user?.phoneNumbers?.[0]?.phoneNumber ?? "";
    return { email, phone };
  }

  const consentComplete = terms && privacy && dangerous;

  async function proceedToPayment() {
    if (!quoteId) {
      setError(t("noQuote"));
      return;
    }
    if (!consentComplete) {
      setError(
        "Please accept the Terms, Privacy Policy and dangerous-goods declaration to continue."
      );
      return;
    }
    if (clerkConfigured && staffPortal) {
      setError(t("staffAccountBlocked", { portal: staffPortal }));
      return;
    }
    const { email, phone } = resolveContact();
    if (clerkConfigured && !email) {
      setError(t("missingEmail"));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const clerkUserId = clerkConfigured ? (user?.id ?? "") : "dev_clerk_user";
      const token = clerkConfigured ? ((await getToken()) ?? undefined) : "dev";

      const booking = await startBooking(
        {
          quote_id: quoteId,
          email,
          phone,
          clerk_user_id: clerkUserId,
          anonymous_session_id: getAnonymousSessionId(),
          terms_accepted: terms,
          privacy_accepted: privacy,
          dangerous_goods_confirmed: dangerous,
          consent_at: new Date().toISOString(),
        },
        token
      );

      if (booking.checkout_url) {
        window.location.href = booking.checkout_url;
        return;
      }

      if (booking.mock_checkout) {
        try {
          await mockCompleteCheckout(quoteId);
        } catch {
          // Server rejected mock (STRIPE_MOCK=false) — should not happen without checkout_url.
        }
        router.push(`/book/success?quote_id=${quoteId}`);
      }
    } catch (err) {
      const detail = err instanceof Error ? err.message : t("error");
      if (detail.includes("identity_conflict:clerk_user_is_")) {
        const portal = detail.split("identity_conflict:clerk_user_is_")[1] ?? "staff";
        setStaffPortal(portal);
        setError(t("staffAccountBlocked", { portal }));
      } else {
        setError(detail);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleCancelBooking() {
    if (!window.confirm(t("cancelConfirm"))) return;
    setCancelling(true);
    setError(null);
    try {
      if (draftId) {
        const token =
          clerkConfigured && isLoaded && isSignedIn ? ((await getToken()) ?? undefined) : undefined;
        await cancelBookingDraft(draftId, getAnonymousSessionId(), token);
      }
      clearBookingDraftHint();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("cancelError"));
    } finally {
      setCancelling(false);
    }
  }

  const needsSignIn = clerkConfigured && isLoaded && !isSignedIn;
  const ready = !clerkConfigured || (isLoaded && isSignedIn);

  return (
    <SiteShell>
      <Container className="py-16 md:py-24 max-w-lg">
        <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
        <p className="type-small text-muted mb-8">{t("subtitle")}</p>
        {!quoteId && <p className="text-red-600 type-small mb-4">{t("noQuote")}</p>}
        {quoteError && <p className="text-red-600 type-small mb-4">{quoteError}</p>}
        {staffPortal && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 mb-6 space-y-3">
            <p className="type-small text-amber-900">
              {t("staffAccountBlocked", { portal: staffPortal })}
            </p>
            <p className="type-caption text-amber-800">{t("staffAccountHint")}</p>
            {returnUrl && (
              <SignOutButton redirectUrl={returnUrl}>
                <button
                  type="button"
                  className="w-full rounded-xl border border-amber-300 bg-white px-4 py-2.5 text-sm font-semibold text-amber-900 hover:bg-amber-100"
                >
                  {t("staffSignOut")}
                </button>
              </SignOutButton>
            )}
          </div>
        )}

        {/* Restored booking draft / review */}
        {quote && (
          <div className="rounded-2xl border border-gray-200 p-4 mb-6 space-y-2">
            <p className="type-caption font-semibold text-primary uppercase tracking-wide">
              Review your booking
            </p>
            <ReviewRow label="Pickup" value={quote.pickup?.formatted} />
            <ReviewRow label="Dropoff" value={quote.dropoff?.formatted} />
            {(quote.additional_stops ?? []).map((s, i) => (
              <ReviewRow key={i} label={`Stop ${i + 1}`} value={s.formatted} />
            ))}
            <ReviewRow label="Vehicle" value={quote.vehicle_class} />
            <ReviewRow label="Package" value={quote.package_type ?? undefined} />
            {quote.weight_kg ? <ReviewRow label="Weight" value={`${quote.weight_kg} kg`} /> : null}
            <ReviewRow label="Dimensions" value={quote.dimensions ?? undefined} />
            <ReviewRow label="Instructions" value={quote.special_instructions ?? undefined} />
            <div className="flex justify-between gap-4 border-t border-gray-100 pt-2 mt-2">
              <span className="type-small font-semibold text-primary">Total</span>
              <span className="type-small font-bold text-primary">{quote.amount_display}</span>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {clerkConfigured && !isLoaded && (
            <p className="type-small text-muted text-center">{t("processing")}</p>
          )}

          {needsSignIn && (
            <div className="rounded-2xl border border-gray-200 p-4">
              <p className="type-small text-muted mb-4 text-center">{t("signInPrompt")}</p>
              <SignIn
                routing="hash"
                forceRedirectUrl={returnUrl}
                signUpForceRedirectUrl={returnUrl}
                fallbackRedirectUrl={returnUrl}
              />
            </div>
          )}

          {ready && (
            <>
              {/* Compliance consent */}
              <div className="rounded-2xl border border-gray-200 p-4 space-y-3">
                <ConsentCheckbox checked={terms} onChange={setTerms}>
                  I agree to the{" "}
                  <a
                    href="/terms"
                    target="_blank"
                    className="text-secondary underline"
                    rel="noreferrer"
                  >
                    Terms of Service
                  </a>
                  .
                </ConsentCheckbox>
                <ConsentCheckbox checked={privacy} onChange={setPrivacy}>
                  I accept the{" "}
                  <a
                    href="/privacy"
                    target="_blank"
                    className="text-secondary underline"
                    rel="noreferrer"
                  >
                    Privacy Policy
                  </a>{" "}
                  (PIPEDA).
                </ConsentCheckbox>
                <ConsentCheckbox checked={dangerous} onChange={setDangerous}>
                  I confirm this shipment contains no prohibited or dangerous goods.
                </ConsentCheckbox>
              </div>

              {error && <p className="text-red-600 type-small">{error}</p>}
              <Button
                shape="pill"
                size="lg"
                className="w-full font-bold"
                disabled={loading || !quoteId || !consentComplete || Boolean(staffPortal)}
                onClick={proceedToPayment}
              >
                {loading ? t("processing") : t("continuePayment")}
              </Button>
              {!clerkConfigured && (
                <p className="type-caption text-muted text-center">{t("clerkNote")}</p>
              )}
            </>
          )}
        </div>

        {quoteId && (
          <Button
            variant="ghost"
            shape="pill"
            size="lg"
            className="mt-6 w-full border border-gray-200 text-muted hover:text-primary"
            disabled={loading || cancelling}
            onClick={handleCancelBooking}
          >
            {cancelling ? t("processing") : t("cancelBooking")}
          </Button>
        )}
      </Container>
    </SiteShell>
  );
}

function ReviewRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex justify-between gap-4">
      <span className="type-caption text-muted">{label}</span>
      <span className="type-caption text-primary text-right">{value}</span>
    </div>
  );
}

function ConsentCheckbox({
  checked,
  onChange,
  children,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="flex items-start gap-3 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 shrink-0 accent-[#2563eb]"
      />
      <span className="type-caption text-primary">{children}</span>
    </label>
  );
}
