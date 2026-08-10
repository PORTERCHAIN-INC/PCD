"use client";

import type { ReactNode } from "react";
import { platformLoginUrl } from "./portal-login";

export type PortalAuthMode = "sign-in" | "sign-up";

type PortalAuthScreenBase = {
  /** Portal label shown under the brand (e.g. Admin, Merchant). */
  portalLabel: string;
  title: string;
  subtitle: string;
  mode?: PortalAuthMode;
  /** Prefer Platform login (invite-only surfaces). */
  websiteUrl?: string;
  showPlatformLogin?: boolean;
  footer?: ReactNode;
};

export type PortalAuthScreenProps =
  | (PortalAuthScreenBase & { unavailable: ReactNode; children?: never })
  | (PortalAuthScreenBase & { unavailable?: undefined; children: ReactNode });

/**
 * Shared full-viewport auth chrome for portal Clerk SignIn / SignUp.
 * Brand-first composition: wordmark → title → subtitle → form → footnotes.
 */
export function PortalAuthScreen(props: PortalAuthScreenProps) {
  const {
    portalLabel,
    title,
    subtitle,
    mode = "sign-in",
    websiteUrl,
    showPlatformLogin = false,
    footer,
  } = props;

  if ("unavailable" in props && props.unavailable != null) {
    return (
      <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-4 py-10">
        <AuthAtmosphere />
        <div className="relative z-10 w-full max-w-md rounded-2xl border border-primary/10 bg-white/95 p-8 backdrop-blur-sm">
          {props.unavailable}
        </div>
      </div>
    );
  }

  const platformUrl = websiteUrl ? platformLoginUrl(websiteUrl) : null;
  const children = "children" in props ? props.children : null;

  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-4 py-10 sm:px-6">
      <AuthAtmosphere />

      <div className="relative z-10 mb-8 flex flex-col items-center text-center">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.22em] text-secondary">
          {portalLabel}
        </p>
        <span className="mt-3 select-none text-2xl font-semibold tracking-[0.04em] text-primary sm:text-[1.65rem]">
          Porterchain
        </span>
        <h1 className="mt-5 text-xl font-semibold tracking-tight text-primary sm:text-2xl">
          {title}
        </h1>
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">{subtitle}</p>
        {showPlatformLogin && platformUrl ? (
          <p className="mt-3 max-w-sm text-xs text-muted">
            Prefer one login for every portal?{" "}
            <a href={platformUrl} className="font-semibold text-secondary hover:underline">
              Use Platform sign-in
            </a>
          </p>
        ) : null}
      </div>

      <div
        className="relative z-10 w-full max-w-md min-w-0 rounded-2xl border border-primary/8 bg-white/95 p-5 shadow-sm backdrop-blur-sm sm:p-6 md:p-8"
        role="main"
      >
        {children}
      </div>

      {footer ? (
        <div className="relative z-10 mt-8 max-w-sm text-center text-xs leading-relaxed text-muted">
          {footer}
        </div>
      ) : null}

      <p className="sr-only">{mode === "sign-up" ? "Create account" : "Secure sign-in"}</p>
    </div>
  );
}

function AuthAtmosphere() {
  return (
    <>
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-[#f0f4f8]" />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-90"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(37, 99, 235, 0.12), transparent 55%), radial-gradient(ellipse 60% 40% at 100% 100%, rgba(10, 22, 40, 0.06), transparent 50%)",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(10, 22, 40, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(10, 22, 40, 0.03) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
    </>
  );
}
