import CustomerAccessGate from "@/components/CustomerAccessGate";

export default function OrdersLayout({ children }: { children: React.ReactNode }) {
  return <CustomerAccessGate>{children}</CustomerAccessGate>;
}
