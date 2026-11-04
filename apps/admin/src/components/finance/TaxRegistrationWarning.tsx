"use client";

import Link from "next/link";
import { adminFetch } from "@/lib/api";
import { useApiData } from "@/hooks/useApiData";

type Status = { gst_hst_number: string; set: boolean; warning: string | null };

/** Admin-only notice while not registered: the system charges and shows no GST/HST. */
export function TaxRegistrationWarning() {
  const { data: status } = useApiData(
    (t) => adminFetch<Status>("/v1/admin/finance/tax-registration", t),
    []
  );
  if (!status || status.set) return null;
  return (
    <div
      role="status"
      className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800"
    >
      {status.warning}{" "}
      <Link href="/finance/tax-registration" className="font-semibold underline">
        Register GST/HST
      </Link>
    </div>
  );
}
