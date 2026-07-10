import type { ReactNode } from "react";
import SiteNavbar from "@/components/layout/SiteNavbar";

/** Auth pages — navbar only; no footer for a focused sign-in flow. */
export default function LoginShell({ children }: { children: ReactNode }) {
  return (
    <>
      <SiteNavbar />
      <main className="overflow-x-hidden pc-nav-offset min-w-0">{children}</main>
    </>
  );
}
