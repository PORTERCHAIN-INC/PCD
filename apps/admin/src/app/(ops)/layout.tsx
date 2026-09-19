import { Suspense } from "react";
import AdminShell from "@/components/AdminShell";
import AdminQueryProvider from "@/components/providers/AdminQueryProvider";
import { AdminProfileProvider } from "@/components/nav/AdminProfileContext";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminQueryProvider>
      <AdminProfileProvider>
        <Suspense fallback={<div className="min-h-dvh bg-gray-bg" />}>
          <AdminShell>{children}</AdminShell>
        </Suspense>
      </AdminProfileProvider>
    </AdminQueryProvider>
  );
}
