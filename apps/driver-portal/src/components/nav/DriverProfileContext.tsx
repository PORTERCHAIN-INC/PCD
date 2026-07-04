"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import type { DriverProfile } from "@/lib/api";

const DriverProfileContext = createContext<{
  profile: DriverProfile | null;
  setProfile: (p: DriverProfile | null) => void;
} | null>(null);

export function DriverProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  return (
    <DriverProfileContext.Provider value={{ profile, setProfile }}>
      {children}
    </DriverProfileContext.Provider>
  );
}

export function useDriverProfile() {
  const ctx = useContext(DriverProfileContext);
  if (!ctx) {
    throw new Error("useDriverProfile must be used within DriverProfileProvider");
  }
  return ctx;
}
