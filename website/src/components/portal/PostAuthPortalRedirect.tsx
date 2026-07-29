"use client";

import { useEffect, useRef, useState } from "react";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import LoginShell from "@/components/portal/LoginShell";
import LoginStatusCard from "@/components/portal/LoginStatusCard";
import {
  fetchAuthMe,
  fetchSessionContext,
  portalChoicesFromSession,
  portalHomeUrlFromAuthMe,
  portalHomeUrlFromPermissions,
  portalHomeUrlFromSession,
} from "@/lib/auth";

type PortalChoice = { portal: string; url: string; label: string };

/**
 * After Platform Clerk session exists, resolve PorterChain roles and leave the website
 * for the correct portal. Multi-persona accounts see a workspace picker.
 */
export default function PostAuthPortalRedirect() {
  const t = useTranslations("login");
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [error, setError] = useState("");
  const [choices, setChoices] = useState<PortalChoice[] | null>(null);
  const getTokenRef = useRef(getToken);
  getTokenRef.current = getToken;

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hash) {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
  }, []);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    let cancelled = false;

    void (async () => {
      setError("");
      setChoices(null);
      try {
        const token = await getTokenRef.current();
        if (!token) throw new Error("missing_token");

        try {
          const ctx = await fetchSessionContext(token);
          const options = portalChoicesFromSession(ctx);
          if (cancelled) return;
          if (options.length > 1) {
            setChoices(options);
            return;
          }
          const destination = options[0]?.url ?? portalHomeUrlFromSession(ctx);
          if (!destination) throw new Error("user_not_provisioned");
          window.location.replace(destination);
          return;
        } catch {
          const me = await fetchAuthMe(token);
          const destination =
            (me.permissions?.length ? portalHomeUrlFromPermissions(me.permissions) : null) ??
            portalHomeUrlFromAuthMe(me);
          if (cancelled) return;
          if (!destination) throw new Error("user_not_provisioned");
          window.location.replace(destination);
        }
      } catch (err) {
        if (cancelled) return;
        const detail = err instanceof Error ? err.message : "auth_failed";
        if (detail === "user_not_provisioned" || detail === "wrong_portal") {
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

  if (!isLoaded || (isSignedIn && !error && !choices)) {
    return (
      <LoginShell>
        <div className="min-h-[calc(100dvh-var(--nav-height))] flex items-center justify-center px-5 py-10 bg-gray-bg">
          <LoginStatusCard title={t("redirecting")} loading />
        </div>
      </LoginShell>
    );
  }

  if (!isSignedIn) {
    return (
      <LoginShell>
        <div className="min-h-[calc(100dvh-var(--nav-height))] flex items-center justify-center px-5 py-10 bg-gray-bg">
          <LoginStatusCard title={t("title")} description={t("missingToken")}>
            <Link
              href="/login"
              className="inline-flex justify-center rounded-xl bg-secondary px-5 py-3 text-white font-semibold text-sm hover:bg-[#1d4ed8] transition-colors"
            >
              {t("title")}
            </Link>
          </LoginStatusCard>
        </div>
      </LoginShell>
    );
  }

  if (choices && choices.length > 1) {
    return (
      <LoginShell>
        <div className="min-h-[calc(100dvh-var(--nav-height))] flex items-center justify-center px-5 py-10 bg-gray-bg">
          <LoginStatusCard title={t("choosePortal")} description={t("choosePortalHint")}>
            <div className="flex w-full flex-col gap-2">
              {choices.map((c) => (
                <a
                  key={c.portal}
                  href={c.url}
                  className="inline-flex justify-center rounded-xl bg-secondary px-5 py-3 text-white font-semibold text-sm hover:bg-[#1d4ed8] transition-colors"
                >
                  {c.label}
                </a>
              ))}
            </div>
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
      </LoginShell>
    );
  }

  return (
    <LoginShell>
      <div className="min-h-[calc(100dvh-var(--nav-height))] flex items-center justify-center px-5 py-10 bg-gray-bg">
        <LoginStatusCard title={t("title")} description={error} variant="error">
          <Link
            href="/contact"
            className="inline-flex justify-center rounded-xl border border-primary/10 px-5 py-3 text-sm font-medium text-primary hover:bg-gray-bg transition-colors"
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
    </LoginShell>
  );
}
