"use client";

import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { quoteSignUpPath, unifiedSignInPath } from "@/data/portal-links";

type Props = {
  id?: string;
  variant?: "hero" | "inline" | "final";
  className?: string;
  from?: string;
};

/**
 * Replaces the old lead-capture inquiry form.
 * Primary path: Platform Clerk sign-up → customer portal quote / book.
 */
export default function QuoteSignupPanel({
  id = "inquiry",
  variant = "hero",
  className,
  from = "business-inquiry",
}: Props) {
  const t = useTranslations("businessPage.inquiry");
  const signUpHref = quoteSignUpPath({ from });
  const isCompact = variant === "inline";

  return (
    <div
      id={id}
      className={cn(
        "rounded-2xl border border-[#0b1220]/5 bg-white p-6 sm:p-8 biz-shadow-lg",
        variant === "hero" && "lg:p-9",
        variant === "final" && "mx-auto max-w-xl",
        className
      )}
    >
      {!isCompact && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold tracking-tight text-[#0b1220] sm:text-2xl">
            {t("title")}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-[#5b6779]">{t("subtitle")}</p>
        </div>
      )}

      <Link
        href={signUpHref}
        onClick={() => {
          track(ANALYTICS_EVENTS.CTA_CLICK, {
            source_section: variant,
            path: "clerk_signup",
            cta_label: "quote_signup",
          });
          track(ANALYTICS_EVENTS.QUOTE_REQUEST, {
            source_section: variant,
            path: "clerk_signup",
          });
          track(ANALYTICS_EVENTS.BUSINESS_INQUIRY_SUBMIT, {
            source_section: variant,
            path: "clerk_signup",
          });
        }}
        className="inline-flex w-full min-h-[2.75rem] items-center justify-center gap-2 rounded-xl bg-[#2563eb] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
      >
        {t("submit")}
        <ArrowRight className="h-4 w-4" aria-hidden />
      </Link>

      <p className="mt-4 text-center text-xs leading-relaxed text-[#5b6779]">
        {t("haveAccount")}{" "}
        <Link
          href={unifiedSignInPath}
          className="font-semibold text-[#2563eb] underline-offset-2 hover:underline"
        >
          {t("signIn")}
        </Link>
      </p>

      <ul className="mt-6 flex flex-wrap justify-center gap-x-4 gap-y-2 text-[0.7rem] font-medium uppercase tracking-wide text-[#5b6779]/90">
        <li>{t("assurances.noObligation")}</li>
        <li aria-hidden>·</li>
        <li>{t("assurances.noLongForms")}</li>
        <li aria-hidden>·</li>
        <li>{t("assurances.responseTime")}</li>
      </ul>
    </div>
  );
}
