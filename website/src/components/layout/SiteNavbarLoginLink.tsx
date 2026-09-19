"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { unifiedSignInPath } from "@/data/portal-links";

type LoginLinkProps = {
  href?: string;
  linkClass: (href: string, active?: boolean) => string;
  onNavigate?: () => void;
};

export default function LoginLink({
  href = unifiedSignInPath,
  linkClass,
  onNavigate,
}: LoginLinkProps) {
  const t = useTranslations("corporate.nav");

  return (
    <Link href={href} className={linkClass(href)} onClick={onNavigate}>
      {t("login")}
    </Link>
  );
}
