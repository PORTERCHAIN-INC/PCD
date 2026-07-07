"use client";

import { SignIn } from "@clerk/nextjs";
import { useTranslations } from "next-intl";
import GuestTrackLookup from "@/components/portal/GuestTrackLookup";

export default function UnifiedSignIn({ redirectUrl = "/login" }: { redirectUrl?: string }) {
  const t = useTranslations("login");

  return (
    <div className="grid gap-10 lg:grid-cols-[1fr,minmax(0,22rem)] lg:items-start">
      <div>
        <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
        <p className="type-small text-muted mb-6 max-w-md">{t("subtitle")}</p>
        <p className="type-caption text-muted max-w-md">{t("roleNote")}</p>
      </div>

      <div className="space-y-6">
        <div className="rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
          <SignIn
            routing="hash"
            forceRedirectUrl={redirectUrl}
            signUpForceRedirectUrl={redirectUrl}
            fallbackRedirectUrl={redirectUrl}
            appearance={{
              elements: {
                footerAction: { display: "none" },
              },
            }}
          />
        </div>
        <GuestTrackLookup compact />
      </div>
    </div>
  );
}
