"use client";

import Link from "next/link";
import { adminFetch } from "@/lib/api";
import { useApiData } from "@/hooks/useApiData";

type Status = { gst_hst_number: string; set: boolean; warning: string | null };

/** Admin-only: shown while our GST/HST number is unset (documents omit the line meanwhile). */
export function TaxRegistrationWarning() {
  const { data: status } = useApiData(
    (t) => adminFetch<Status>("/v1/admin/finance/tax-registration", t),
    []
  );
  if (!status || status.set) return null;
  return (
    <div
      role="alert"
      className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      {status.warning}{" "}
      <Link href="/settings?section=finance" className="font-semibold underline">
        Add it now
      </Link>
    </div>
  );
}
