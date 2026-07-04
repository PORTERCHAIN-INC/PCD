import CustomerAccessGate from "@/components/CustomerAccessGate";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <CustomerAccessGate>{children}</CustomerAccessGate>;
}
