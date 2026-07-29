"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { SessionContext } from "./session-context";

export type SessionContextValue = {
  session: SessionContext | null;
  setSession: (ctx: SessionContext | null) => void;
  activeWorkspaceId: string | null;
  setActiveWorkspaceId: (id: string | null) => void;
};

const Ctx = createContext<SessionContextValue | null>(null);

export function SessionContextProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<SessionContext | null>(null);
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState<string | null>(null);
  const setSession = useCallback((ctx: SessionContext | null) => {
    setSessionState(ctx);
  }, []);
  const setActiveWorkspaceId = useCallback((id: string | null) => {
    setActiveWorkspaceIdState(id);
  }, []);
  const value = useMemo(
    () => ({ session, setSession, activeWorkspaceId, setActiveWorkspaceId }),
    [session, setSession, activeWorkspaceId, setActiveWorkspaceId]
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSessionContext(): SessionContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) {
    throw new Error("useSessionContext requires SessionContextProvider");
  }
  return ctx;
}

export function useOptionalSessionContext(): SessionContextValue | null {
  return useContext(Ctx);
}
