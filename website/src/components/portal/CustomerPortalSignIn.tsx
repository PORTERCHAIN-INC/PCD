"use client";

import { SignIn } from "@clerk/nextjs";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Package, Shield } from "lucide-react";
import GuestTrackLookup from "@/components/portal/GuestTrackLookup";

export default function CustomerPortalSignIn({
  redirectUrl = "/portal/customer",
}: {
  redirectUrl?: string;
}) {
  const t = useTranslations("portal.customer");

  return (
    <div className="grid gap-10 lg:grid-cols-[1fr,minmax(0,22rem)] lg:items-start">
      <div>
        <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/10 lg:mx-0">
          <Shield className="h-7 w-7 text-secondary" aria-hidden />
        </div>
        <h1 className="type-h2 font-bold text-primary mb-2">{t("signInTitle")}</h1>
        <p className="type-small text-muted mb-6 max-w-md">{t("signInSubtitle")}</p>
        <ul className="space-y-3 type-small text-primary/80 max-w-md">
          <li className="flex items-start gap-3">
            <Package className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
            {t("signInBenefitHistory")}
          </li>
          <li className="flex items-start gap-3">
            <Package className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
            {t("signInBenefitInvoices")}
          </li>
          <li className="flex items-start gap-3">
            <Package className="mt-0.5 h-4 w-4 shrink-0 text-secondary" aria-hidden />
            {t("signInBenefitSupport")}
          </li>
        </ul>
        <p className="mt-8 type-caption text-muted">
          {t("signInBusinessNote")}{" "}
          <Link href="/business" className="text-secondary font-semibold hover:underline">
            {t("signInBusinessLink")}
          </Link>
        </p>
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
