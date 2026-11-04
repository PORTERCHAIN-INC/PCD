"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { isAuthShellPath } from "@/lib/auth-shell";
import { isAuthConfigured } from "@/lib/env";
import LoginLink from "@/components/layout/SiteNavbarLoginLink";

const SiteNavbarAuthSession = dynamic(() => import("@/components/layout/SiteNavbarAuthSession"), {
  ssr: false,
  loading: () => (
    <span className="inline-block h-9 w-9 rounded-full bg-gray-bg animate-pulse" aria-hidden />
  ),
});

type NavbarAuthProps = {
  navLight: boolean;
  linkClass: (href: string, active?: boolean) => string;
  onNavigate?: () => void;
};

export default function SiteNavbarAuth(props: NavbarAuthProps) {
  const pathname = usePathname() ?? "";
  const authShell = isAuthConfigured() && isAuthShellPath(pathname);

  if (!authShell) {
    return <LoginLink {...props} />;
  }

  return <SiteNavbarAuthSession {...props} />;
}
