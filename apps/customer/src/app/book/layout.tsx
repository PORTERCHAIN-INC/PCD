import CustomerAccessGate from "@/components/CustomerAccessGate";

export default function BookLayout({ children }: { children: React.ReactNode }) {
  return <CustomerAccessGate>{children}</CustomerAccessGate>;
}
