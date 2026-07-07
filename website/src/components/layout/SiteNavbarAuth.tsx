"use client";

import { UserButton, useAuth } from "@clerk/nextjs";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { customerPortalDashboardUrl, unifiedSignInPath } from "@/data/portal-links";
import { isClerkConfigured } from "@/lib/env";
import { cn } from "@/lib/utils";

export default function SiteNavbarAuth({
  navLight,
  linkClass,
  onNavigate,
}: {
  navLight: boolean;
  linkClass: (href: string, active?: boolean) => string;
  onNavigate?: () => void;
}) {
  const t = useTranslations("corporate.nav");
  const clerkConfigured = isClerkConfigured();
  const { isLoaded, isSignedIn } = useAuth();

  if (!clerkConfigured) {
    return (
      <Link href={unifiedSignInPath} className={linkClass(unifiedSignInPath)} onClick={onNavigate}>
        {t("login")}
      </Link>
    );
  }

  if (!isLoaded) {
    return (
      <span
        className={cn("inline-block h-9 w-9 rounded-full", navLight ? "bg-gray-bg" : "bg-white/10")}
        aria-hidden
      />
    );
  }

  if (isSignedIn) {
    const ordersLink = (
      <a
        href={customerPortalDashboardUrl}
        className={
          onNavigate
            ? "text-center py-3 text-sm font-medium text-primary"
            : linkClass(customerPortalDashboardUrl)
        }
        onClick={onNavigate}
      >
        {t("myOrders")}
      </a>
    );

    return (
      <div className={onNavigate ? "flex flex-col items-center gap-3" : "contents"}>
        {ordersLink}
        <UserButton
          appearance={{
            elements: {
              avatarBox: "h-9 w-9",
            },
          }}
        />
      </div>
    );
  }

  return (
    <Link
      href={unifiedSignInPath}
      className={
        onNavigate
          ? "text-center py-3 text-sm font-medium text-primary"
          : linkClass(unifiedSignInPath)
      }
      onClick={onNavigate}
    >
      {t("login")}
    </Link>
  );
}
