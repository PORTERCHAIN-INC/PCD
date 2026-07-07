"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { useTranslations } from "next-intl";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import UnifiedSignIn from "@/components/portal/UnifiedSignIn";
import { fetchAuthMe, portalHomeUrl } from "@/lib/auth";
import { isClerkConfigured } from "@/lib/env";
import { Link } from "@/i18n/navigation";

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <SiteShell>
          <Container className="py-16 md:py-24 max-w-4xl">
            <p className="type-small text-muted">Loading…</p>
          </Container>
        </SiteShell>
      }
    >
      <LoginContent />
    </Suspense>
  );
}

function LoginContent() {
  const t = useTranslations("login");
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [error, setError] = useState("");
  const [redirecting, setRedirecting] = useState(false);
  const redirectStarted = useRef(false);
  const getTokenRef = useRef(getToken);
  getTokenRef.current = getToken;

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      redirectStarted.current = false;
      setRedirecting(false);
      setError("");
    }
  }, [isLoaded, isSignedIn]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || redirectStarted.current) return;

    redirectStarted.current = true;
    let cancelled = false;

    void (async () => {
      setRedirecting(true);
      setError("");
      try {
        const token = await getTokenRef.current();
        if (!token) throw new Error("missing_token");
        const me = await fetchAuthMe(token);
        if (cancelled) {
          redirectStarted.current = false;
          setRedirecting(false);
          return;
        }
        window.location.assign(portalHomeUrl(me.user_type));
      } catch (err) {
        if (cancelled) {
          redirectStarted.current = false;
          setRedirecting(false);
          return;
        }
        redirectStarted.current = false;
        setRedirecting(false);
        const detail = err instanceof Error ? err.message : "auth_failed";
        if (detail === "user_not_provisioned") {
          setError(t("notProvisioned"));
        } else if (detail.startsWith("identity_conflict:")) {
          setError(t("identityConflict"));
        } else if (detail === "missing_token") {
          setError(t("missingToken"));
        } else if (detail === "Failed to fetch" || detail.includes("NetworkError")) {
          setError(t("apiUnreachable"));
        } else {
          setError(`${t("error")} (${detail})`);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn]);

  if (!isClerkConfigured()) {
    return (
      <SiteShell>
        <Container className="py-16 md:py-24 max-w-lg">
          <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
          <p className="type-small text-muted mb-6">{t("devModeNote")}</p>
          <Link
            href="/"
            className="inline-flex rounded-xl bg-secondary px-5 py-3 text-white font-semibold type-small"
          >
            {t("backHome")}
          </Link>
        </Container>
      </SiteShell>
    );
  }

  if (!isLoaded) {
    return (
      <SiteShell>
        <Container className="py-16 md:py-24 max-w-4xl">
          <p className="type-small text-muted">Loading…</p>
        </Container>
      </SiteShell>
    );
  }

  if (isSignedIn && redirecting && !error) {
    return (
      <SiteShell>
        <Container className="py-16 md:py-24 max-w-4xl">
          <p className="type-small text-muted">{t("redirecting")}</p>
        </Container>
      </SiteShell>
    );
  }

  if (isSignedIn && error) {
    return (
      <SiteShell>
        <Container className="py-16 md:py-24 max-w-lg">
          <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
          <p className="type-small text-red-700 mb-6">{error}</p>
          <div className="flex flex-col gap-3">
            <Link
              href="/contact"
              className="inline-flex justify-center rounded-xl bg-secondary px-5 py-3 text-white font-semibold type-small"
            >
              {t("contactSupport")}
            </Link>
            <SignOutButton redirectUrl="/login">
              <button
                type="button"
                className="w-full rounded-xl border border-primary/10 px-5 py-3 text-sm font-medium text-primary"
              >
                {t("signOut")}
              </button>
            </SignOutButton>
          </div>
        </Container>
      </SiteShell>
    );
  }

  return (
    <SiteShell>
      <Container className="py-16 md:py-24 max-w-4xl">
        <UnifiedSignIn redirectUrl="/login" />
      </Container>
    </SiteShell>
  );
}
