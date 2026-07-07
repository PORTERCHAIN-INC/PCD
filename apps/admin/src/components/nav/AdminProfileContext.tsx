"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
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
  return ctx;
}
