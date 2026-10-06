"use client";

import { usePathname } from "next/navigation";
import DriverShell from "@/components/DriverShell";

const BARE = ["/login", "/onboarding", "/impersonate"];

export default function DriverFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "";
  if (BARE.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) {
    return children;
  }
  return <DriverShell>{children}</DriverShell>;
}
