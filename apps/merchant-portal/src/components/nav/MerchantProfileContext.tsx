"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { MerchantAccessProfile } from "@/lib/merchant-access";

const MerchantProfileContext = createContext<{
  profile: MerchantAccessProfile | null;
  setProfile: (p: MerchantAccessProfile | null) => void;
} | null>(null);

export function MerchantProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<MerchantAccessProfile | null>(null);
  const value = useMemo(() => ({ profile, setProfile }), [profile]);
  return (
    <MerchantProfileContext.Provider value={value}>{children}</MerchantProfileContext.Provider>
  );
}

export function useMerchantProfile() {
  const ctx = useContext(MerchantProfileContext);
  if (!ctx) {
    throw new Error("useMerchantProfile must be used within MerchantProfileProvider");
  }
  return ctx;
}
