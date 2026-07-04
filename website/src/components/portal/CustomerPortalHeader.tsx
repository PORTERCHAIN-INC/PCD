"use client";

import { UserButton, useUser } from "@clerk/nextjs";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { isClerkConfigured } from "@/lib/env";

export default function CustomerPortalHeader() {
  const t = useTranslations("portal.customer");
  const { user } = useUser();
  const email = user?.primaryEmailAddress?.emailAddress ?? user?.emailAddresses?.[0]?.emailAddress;

  return (
    <div className="mb-8 flex flex-col gap-4 border-b border-primary/10 pb-6 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="type-h2 font-bold text-primary">{t("title")}</h1>
        <p className="type-small text-muted mt-1">
          {email ? t("signedInAs", { email }) : t("subtitle")}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/#book"
          className="rounded-xl bg-secondary px-4 py-2.5 text-white font-semibold type-small hover:bg-[#1d4ed8]"
        >
          {t("newBooking")}
        </Link>
        {isClerkConfigured() && <UserButton />}
      </div>
    </div>
  );
}
