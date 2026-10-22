"use client";

import { useEffect, useState } from "react";
import { AUTH_STALL_TIMEOUT_MS, isPrimaryButtonBusy, nextStallState } from "./authStall";
import { reportAuthEvent } from "./authTelemetry";

export type AuthStallNoticeCopy = { title: string; body: string; retry: string };

const DEFAULT_COPY: AuthStallNoticeCopy = {
  title: "Still verifying?",
  body:
    "The security check did not finish, so your account was not created yet. Refresh and try again. " +
    "If it keeps spinning, allow challenges.cloudflare.com (turn off strict tracking protection or " +
    "ad blockers for this page) or use Continue with Google. Need help? support@porterchain.com",
  retry: "Refresh and try again",
};

function readPrimaryButton(): { disabled: boolean; loading: boolean } | null {
  const btn = document.querySelector<HTMLButtonElement>(".cl-formButtonPrimary");
  if (!btn) return null;
  return {
    disabled: btn.disabled,
    loading: btn.hasAttribute("data-loading") || btn.getAttribute("aria-busy") === "true",
  };
}

/** Shows a recovery notice when Clerk's Continue button spins for too long (CAPTCHA hang). */
export function AuthStallNotice({
  copy = DEFAULT_COPY,
  timeoutMs = AUTH_STALL_TIMEOUT_MS,
}: {
  copy?: AuthStallNoticeCopy;
  timeoutMs?: number;
}) {
  const [stalled, setStalled] = useState(false);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let busySince: number | null = null;
    let armed = false;
    const onClick = (e: Event) => {
      const t = e.target as Element | null;
      if (t?.closest?.(".cl-formButtonPrimary")) armed = true;
    };
    document.addEventListener("click", onClick, true);
    const goOffline = () => {
      setOffline(true);
      reportAuthEvent("offline");
    };
    const goOnline = () => setOffline(false);
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    if (navigator.onLine === false) goOffline();
    const id = window.setInterval(() => {
      // Clerk's own inline errors (wrong password, no account, rate limit): log them server-side.
      const err = document.querySelector(".cl-formFieldErrorText, .cl-alertText");
      if (err?.textContent) reportAuthEvent("clerk_form_error", err.textContent);
      // Only count after the user pressed Continue (the button is disabled while fields are empty).
      const busy = armed && isPrimaryButtonBusy(readPrimaryButton());
      const next = nextStallState(busy, busySince, Date.now(), timeoutMs);
      busySince = next.busySince;
      if (next.stalled) reportAuthEvent("bot_check_stall");
      setStalled(next.stalled);
    }, 1000);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("click", onClick, true);
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, [timeoutMs]);

  if (offline) {
    return (
      <div
        role="alert"
        data-testid="auth-offline"
        className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
      >
        <p className="font-semibold">You are offline</p>
        <p className="mt-1 leading-relaxed">
          Reconnect to the internet, then press Continue again.
        </p>
      </div>
    );
  }
  if (!stalled) return null;
  const challengeVisible =
    typeof document !== "undefined" &&
    Boolean(document.querySelector('iframe[src*="challenges.cloudflare.com"]'));
  if (challengeVisible) {
    return (
      <div
        role="alert"
        data-testid="auth-human-check"
        className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900"
      >
        <p className="font-semibold">One more step</p>
        <p className="mt-1 leading-relaxed">
          Tick &ldquo;Verify you are human&rdquo; above to finish creating your account. If the box
          does not appear or keeps failing, refresh the page or use Continue with Google.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-3 rounded-lg bg-sky-700 px-3 py-2 text-xs font-semibold text-white hover:bg-sky-800"
        >
          Refresh and try again
        </button>
      </div>
    );
  }
  return (
    <div
      role="alert"
      data-testid="auth-stall"
      className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
    >
      <p className="font-semibold">{copy.title}</p>
      <p className="mt-1 leading-relaxed">{copy.body}</p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="mt-3 rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-700"
      >
        {copy.retry}
      </button>
    </div>
  );
}
