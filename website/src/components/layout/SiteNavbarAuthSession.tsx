"use client";

/** Website Keycloak session (pc-website); signed-in CTA → customer dashboard. */

import { UserButton, useAuth } from "@porterchain/auth/oidc/client";
import { useTranslations } from "next-intl";
import { customerPortalDashboardUrl, unifiedSignInPath } from "@/data/portal-links";
import { cn } from "@/lib/utils";
import LoginLink from "@/components/layout/SiteNavbarLoginLink";

type NavbarAuthProps = {
  navLight: boolean;
  linkClass: (href: string, active?: boolean) => string;
  onNavigate?: () => void;
};

export default function SiteNavbarAuthSession(props: NavbarAuthProps) {
  const t = useTranslations("corporate.nav");
  const { navLight, linkClass, onNavigate } = props;
  const { isLoaded, isSignedIn } = useAuth();

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
        className={linkClass(customerPortalDashboardUrl)}
        onClick={onNavigate}
      >
        {t("myOrders")}
      </a>
    );

    return (
      <div className={onNavigate ? "flex flex-col gap-2" : "contents"}>
        {ordersLink}
        <UserButton returnTo="/en/login" />
      </div>
    );
  }

  return <LoginLink href={unifiedSignInPath} {...props} />;
}
