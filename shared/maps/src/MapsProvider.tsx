"use client";

import { createContext, useContext, type ReactNode } from "react";

type MapsContextValue = {
  googleMapsApiKey: string;
  enabled: boolean;
};

const MapsContext = createContext<MapsContextValue>({ googleMapsApiKey: "", enabled: false });

export function MapsProvider({
  children,
  googleMapsApiKey,
}: {
  children: ReactNode;
  googleMapsApiKey: string;
}) {
  const enabled = googleMapsApiKey.trim().length > 0;
  return (
    <MapsContext.Provider value={{ googleMapsApiKey: googleMapsApiKey.trim(), enabled }}>
      {children}
    </MapsContext.Provider>
  );
}

export function useMapsConfig() {
  return useContext(MapsContext);
}
