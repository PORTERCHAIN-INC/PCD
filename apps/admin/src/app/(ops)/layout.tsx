import AdminShell from "@/components/AdminShell";
import AdminQueryProvider from "@/components/providers/AdminQueryProvider";
import { AdminProfileProvider } from "@/components/nav/AdminProfileContext";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminQueryProvider>
      <AdminProfileProvider>
        <AdminShell>{children}</AdminShell>
      </AdminProfileProvider>
    </AdminQueryProvider>
  );
}
