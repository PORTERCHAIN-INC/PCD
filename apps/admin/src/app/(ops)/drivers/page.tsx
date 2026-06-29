"use client";

import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import Button from "@porterchain/ui/button";
import { useState } from "react";

export default function DriversPage() {
  const [refresh, setRefresh] = useState(0);
  const { data, getApiToken } = useApiData((t) => api.drivers(t), [refresh]);

  async function approve(id: string) {
    await api.approveDriver(await getApiToken(), id);
    setRefresh((n) => n + 1);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Driver Management</h1>
      <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-primary/10 bg-gray-bg/50">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">License</th>
              <th className="px-4 py-3">Insurance</th>
              <th className="px-4 py-3">Online</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((d) => (
              <tr key={String(d.id)} className="border-b border-primary/5">
                <td className="px-4 py-3">{String(d.full_name)}</td>
                <td className="px-4 py-3">{String(d.status)}</td>
                <td className="px-4 py-3">{d.license_verified ? "✓" : "—"}</td>
                <td className="px-4 py-3">{d.insurance_verified ? "✓" : "—"}</td>
                <td className="px-4 py-3">{d.is_online ? "Online" : "Offline"}</td>
                <td className="px-4 py-3">
                  {d.status === "PENDING" && (
                    <Button size="sm" onClick={() => approve(String(d.id))}>
                      Approve
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!data || data.length === 0) && <p className="p-6 text-center text-muted">No drivers yet</p>}
      </div>
    </div>
  );
}
