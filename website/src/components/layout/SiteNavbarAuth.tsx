"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { isClerkClientShellPath } from "@/lib/clerk-shell";
import { isClerkConfigured } from "@/lib/env";
import LoginLink from "@/components/layout/SiteNavbarLoginLink";

const SiteNavbarAuthClerk = dynamic(() => import("@/components/layout/SiteNavbarAuthClerk"), {
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
  const clerkShell = isClerkConfigured() && isClerkClientShellPath(pathname);

  if (!clerkShell) {
    return <LoginLink {...props} />;
  }

  return <SiteNavbarAuthClerk {...props} />;
}
