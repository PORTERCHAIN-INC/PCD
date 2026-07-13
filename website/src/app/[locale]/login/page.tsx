"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import LoginShell from "@/components/portal/LoginShell";
import LoginBrandPanel from "@/components/portal/LoginBrandPanel";
import LoginStatusCard from "@/components/portal/LoginStatusCard";
import UnifiedSignIn from "@/components/portal/UnifiedSignIn";
import { fetchAuthMe, portalHomeUrl } from "@/lib/auth";
import { isClerkConfigured } from "@/lib/env";

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginPageFallback />}>
      <LoginContent />
    </Suspense>
  );
}

function LoginPageFallback() {
  const t = useTranslations("login");
  return (
    <LoginShell>
      <div className="min-h-[calc(100dvh-var(--nav-height))] grid lg:grid-cols-2 bg-gray-bg">
        <LoginBrandPanel />
        <div className="flex items-center justify-center px-5 py-10">
          <LoginStatusCard title={t("title")} loading />
        </div>
      </div>
    </LoginShell>
  );
}

function LoginContent() {
  const t = useTranslations("login");
  const searchParams = useSearchParams();
  const intent = searchParams.get("intent");
  const merchantIntent = intent === "merchant";
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
  }, [isLoaded, isSignedIn, t]);

  if (!isClerkConfigured()) {
    return (
      <LoginShell>
        <div className="min-h-[calc(100dvh-var(--nav-height))] flex items-center justify-center px-5 py-12 bg-gray-bg">
          <LoginStatusCard title={t("title")} description={t("devModeNote")}>
            <Link
              href="/"
              className="inline-flex justify-center rounded-xl bg-secondary px-5 py-3 text-white font-semibold text-sm hover:bg-[#1d4ed8] transition-colors"
            >
              {t("backHome")}
            </Link>
          </LoginStatusCard>
        </div>
      </LoginShell>
    );
  }

  if (!isLoaded) {
    return <LoginPageFallback />;
  }

  if (isSignedIn && redirecting && !error) {
    return (
      <LoginShell>
        <div className="min-h-[calc(100dvh-var(--nav-height))] grid lg:grid-cols-2 bg-gray-bg">
          <LoginBrandPanel />
          <div className="flex items-center justify-center px-5 py-10">
            <LoginStatusCard title={t("redirecting")} loading />
          </div>
        </div>
      </LoginShell>
    );
  }

  if (isSignedIn && error) {
    return (
      <LoginShell>
        <div className="min-h-[calc(100dvh-var(--nav-height))] grid lg:grid-cols-2 bg-gray-bg">
          <LoginBrandPanel />
          <div className="flex items-center justify-center px-5 py-10">
            <LoginStatusCard title={t("title")} description={error} variant="error">
              <Link
                href="/contact"
                className="inline-flex justify-center rounded-xl bg-secondary px-5 py-3 text-white font-semibold text-sm hover:bg-[#1d4ed8] transition-colors"
              >
                {t("contactSupport")}
              </Link>
              <SignOutButton redirectUrl="/login">
                <button
                  type="button"
                  className="w-full rounded-xl border border-primary/10 px-5 py-3 text-sm font-medium text-primary hover:bg-gray-bg transition-colors"
                >
                  {t("signOut")}
                </button>
              </SignOutButton>
            </LoginStatusCard>
          </div>
        </div>
      </LoginShell>
    );
  }

  return (
    <LoginShell>
      <UnifiedSignIn redirectUrl="/login" intent={merchantIntent ? "merchant" : undefined} />
    </LoginShell>
  );
}
