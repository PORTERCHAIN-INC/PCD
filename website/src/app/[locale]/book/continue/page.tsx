"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { SignIn, useAuth, useUser } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import Button from "@/components/ui/Button";
import { getAnonymousSessionId } from "@/lib/anonymous-session";
import { isClerkConfigured } from "@/lib/env";
import { mockCompleteCheckout, startBooking } from "@/lib/api";

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
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const { user } = useUser();
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSignIn, setShowSignIn] = useState(false);
  const checkoutAfterAuth = useRef(false);

  async function completeCheckout() {
    if (!quoteId || !email || !phone) {
      setError(t("missingFields"));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const clerkConfigured = isClerkConfigured();
      const clerkUserId = clerkConfigured ? (user?.id ?? "") : "dev_clerk_user";
      const token = clerkConfigured ? ((await getToken()) ?? undefined) : "dev";

      const booking = await startBooking(
        {
          quote_id: quoteId,
          email,
          phone,
          clerk_user_id: clerkUserId,
          anonymous_session_id: getAnonymousSessionId(),
        },
        token
      );

      if (booking.checkout_url) {
        window.location.href = booking.checkout_url;
        return;
      }

      if (booking.mock_checkout) {
        const confirmation = await mockCompleteCheckout(quoteId);
        router.push(
          `/book/success?tracking=${confirmation.tracking_number}&order=${confirmation.order_number}&booking=${confirmation.booking_number}&invoice=${confirmation.invoice_number}`
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setLoading(false);
      checkoutAfterAuth.current = false;
    }
  }

  async function handleContinue() {
    if (!quoteId || !email || !phone) {
      setError(t("missingFields"));
      return;
    }

    if (isClerkConfigured()) {
      if (!isLoaded) return;
      if (!isSignedIn) {
        checkoutAfterAuth.current = true;
        setShowSignIn(true);
        return;
      }
    }

    await completeCheckout();
  }

  useEffect(() => {
    if (!showSignIn || !isLoaded || !isSignedIn || !checkoutAfterAuth.current || loading) {
      return;
    }
    checkoutAfterAuth.current = false;
    void completeCheckout();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- resume checkout after Clerk sign-in
  }, [isLoaded, isSignedIn, showSignIn, loading]);

  return (
    <SiteShell>
      <Container className="py-16 md:py-24 max-w-lg">
        <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
        <p className="type-small text-muted mb-8">{t("subtitle")}</p>
        {!quoteId && (
          <p className="text-red-600 type-small mb-4">{t("noQuote")}</p>
        )}
        <div className="space-y-4">
          <div>
            <label className="type-caption font-bold text-muted mb-1.5 block">{t("email")}</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-gray-200 px-4 py-3 type-small"
            />
          </div>
          <div>
            <label className="type-caption font-bold text-muted mb-1.5 block">{t("phone")}</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded-xl border border-gray-200 px-4 py-3 type-small"
            />
          </div>
          {error && <p className="text-red-600 type-small">{error}</p>}
          {!showSignIn && (
            <Button
              shape="pill"
              size="lg"
              className="w-full font-bold"
              disabled={loading || !quoteId}
              onClick={handleContinue}
            >
              {loading ? t("processing") : t("continuePayment")}
            </Button>
          )}
          {showSignIn && isClerkConfigured() && !isSignedIn && (
            <div className="rounded-2xl border border-gray-200 p-4">
              <p className="type-small text-muted mb-4 text-center">{t("signInPrompt")}</p>
              <SignIn routing="hash" />
            </div>
          )}
          {showSignIn && isSignedIn && loading && (
            <p className="type-small text-muted text-center">{t("processing")}</p>
          )}
          {!isClerkConfigured() && (
            <p className="type-caption text-muted text-center">{t("clerkNote")}</p>
          )}
        </div>
      </Container>
    </SiteShell>
  );
}
