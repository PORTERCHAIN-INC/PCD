"use client";

import { useCallback, useEffect, useState } from "react";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { merchantStatusLabel } from "@/lib/catalog";
import { getMerchantMemberships, type MerchantMembership } from "@/lib/api";

function optionLabel(m: MerchantMembership): string {
  const role = m.role_label ? ` · ${m.role_label}` : "";
  // Only call out a status that stops them working; Active needs no label.
  const status =
    m.can_open === false ? ` · ${m.status_label || merchantStatusLabel(m.status)}` : "";
  return `${m.company_name}${role}${status}`;
}

export default function MerchantCompanySwitcher({ compact = false }: { compact?: boolean }) {
  const { orgId, setOrgId, getApiToken, isSignedIn } = useMerchantAuth();
  const [memberships, setMemberships] = useState<MerchantMembership[]>([]);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    try {
      const token = await getApiToken();
      setMemberships(await getMerchantMemberships(token, orgId));
    } catch {
      setMemberships([]);
    }
  }, [getApiToken, isSignedIn, orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (memberships.length < 2) return null;

  return (
    <label className={compact ? "block min-w-0" : "block"}>
      {!compact && (
        <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted">
          Company
        </span>
      )}
      <select
        className={
          compact
            ? "max-w-[14rem] truncate rounded-lg border border-primary/15 bg-white px-2 py-1 text-xs text-primary"
            : "mt-1 w-full rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm text-primary"
        }
        value={orgId || ""}
        aria-label="Switch company"
        onChange={(e) => setOrgId(e.target.value)}
      >
        {memberships.map((m) => (
          <option key={m.merchant_id} value={m.merchant_id} disabled={m.can_open === false}>
            {optionLabel(m)}
          </option>
        ))}
      </select>
    </label>
  );
}
