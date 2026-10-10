import CustomerAccessGate from "@/components/CustomerAccessGate";

export default function SendLayout({ children }: { children: React.ReactNode }) {
  return <CustomerAccessGate>{children}</CustomerAccessGate>;
}
