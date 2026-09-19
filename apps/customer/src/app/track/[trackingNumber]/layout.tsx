import CustomerAccessGate from "@/components/CustomerAccessGate";

export default function TrackLayout({ children }: { children: React.ReactNode }) {
  return <CustomerAccessGate>{children}</CustomerAccessGate>;
}
