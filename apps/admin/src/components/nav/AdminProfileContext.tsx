"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { useHydrated } from "@/hooks/useHydrated";
import type { AdminStaffProfile } from "@/lib/admin-access";

const AdminProfileContext = createContext<{
  profile: AdminStaffProfile | null;
  setProfile: (p: AdminStaffProfile | null) => void;
} | null>(null);

export function AdminProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<AdminStaffProfile | null>(null);
  return (
    <AdminProfileContext.Provider value={{ profile, setProfile }}>
      {children}
    </AdminProfileContext.Provider>
  );
}

export function useAdminProfile() {
  const ctx = useContext(AdminProfileContext);
  if (!ctx) throw new Error("useAdminProfile must be used within AdminProfileProvider");
  const hydrated = useHydrated();
  const pre = useMemo(() => ({ ...ctx, profile: null }), [ctx]);
  return hydrated ? ctx : pre;
}

/** Same as useAdminProfile but safe outside the provider (tests, isolated panels). */
export function useOptionalAdminProfile() {
  const profile = useContext(AdminProfileContext)?.profile ?? null;
  return useHydrated() ? profile : null;
}
