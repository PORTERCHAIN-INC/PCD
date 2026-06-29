"use client";

import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import Button from "@porterchain/ui/button";
import { useState } from "react";

export default function MerchantsPage() {
  const [refresh, setRefresh] = useState(0);
  const { data, getApiToken } = useApiData((t) => api.merchants(t), [refresh]);

  async function approve(id: string) {
    const token = await getApiToken();
    await api.approveMerchant(token, id);
    setRefresh((n) => n + 1);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Merchant Management</h1>
      <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-primary/10 bg-gray-bg/50">
            <tr>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Terms</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((m) => (
              <tr key={String(m.id)} className="border-b border-primary/5">
                <td className="px-4 py-3">{String(m.company_name)}</td>
                <td className="px-4 py-3">{String(m.email)}</td>
                <td className="px-4 py-3">{String(m.status)}</td>
                <td className="px-4 py-3">{String(m.payment_terms)}</td>
                <td className="px-4 py-3">
                  {m.status === "PENDING" && (
                    <Button size="sm" onClick={() => approve(String(m.id))}>
                      Approve
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
