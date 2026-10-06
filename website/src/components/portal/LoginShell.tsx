import { Suspense, type ReactNode } from "react";
import SiteNavbar from "@/components/layout/SiteNavbar";

function NavbarFallback() {
  return <div className="h-16 w-full border-b border-primary/5 bg-white" aria-hidden />;
}

/** Auth pages — navbar only; no footer for a focused sign-in flow. */
export default function LoginShell({ children }: { children: ReactNode }) {
  return (
    <>
      <Suspense fallback={<NavbarFallback />}>
        <SiteNavbar />
      </Suspense>
      <main className="overflow-x-hidden pc-nav-offset min-w-0">{children}</main>
    </>
  );
}
