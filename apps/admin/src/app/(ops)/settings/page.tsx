"use client";

import { DataTable } from "@/components/DataTable";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const { data: staff } = useApiData((t) => api.staff(t));
  const { data: config } = useApiData((t) => api.systemConfig(t));

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-primary">Settings</h1>
      <section>
        <h2 className="mb-3 font-semibold">Staff & Roles</h2>
        <DataTable
          columns={["Email", "Name", "Role"]}
          rows={(staff || []).map((u) => [String(u.email), String(u.name || "—"), String(u.role)])}
        />
      </section>
      <section>
        <h2 className="mb-3 font-semibold">System Configuration</h2>
        <pre className="overflow-auto rounded-2xl border border-primary/10 bg-white p-4 text-xs">
          {JSON.stringify(config || {}, null, 2)}
        </pre>
      </section>
    </div>
  );
}
