import MonitoringPolicyView from "@/components/compliance/MonitoringPolicyView";

export const metadata = { title: "Electronic Monitoring Policy · Porterchain Driver" };

export default function MonitoringPolicyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <MonitoringPolicyView />
    </div>
  );
}
