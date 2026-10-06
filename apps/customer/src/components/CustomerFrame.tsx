"use client";

import { usePathname } from "next/navigation";
import CustomerShell from "@/components/CustomerShell";

const BARE = ["/sign-in", "/sign-up", "/onboarding", "/impersonate"];

export default function CustomerFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "";
  if (BARE.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) {
    return children;
  }
  return <CustomerShell>{children}</CustomerShell>;
}
