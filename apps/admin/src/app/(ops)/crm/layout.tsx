import CrmNav from "@/components/crm/CrmNav";

export default function CrmLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Merchant CRM</h1>
        <p className="text-sm text-muted">
          Turn every logistics inquiry into an active Porterchain merchant.
        </p>
      </div>
      <div className="sticky top-0 z-10 -mx-1 rounded-2xl bg-gray-bg/80 px-1 py-1 backdrop-blur">
        <CrmNav />
      </div>
      {children}
    </div>
  );
}
