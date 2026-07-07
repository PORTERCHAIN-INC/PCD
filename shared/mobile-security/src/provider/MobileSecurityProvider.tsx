"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AppState, type AppStateStatus } from "react-native";
import { BiometricGate } from "../biometric/BiometricGate";
import { IntegrityGate } from "../device/IntegrityGate";
import { PinLockGate } from "../pin/PinLockGate";
import type { AuthPrincipal, MobileAppKind, SecurityPolicy } from "../types";
import { configureAuditBuffer, emitSecurityEvent, flushAuditBuffer } from "../audit/emitter";
import { DEFAULT_SECURITY_POLICY, type MobileSecurityEnv } from "../config";
import { checkDeviceIntegrity } from "../device/integrity";
import { configureCertificatePinning } from "../network/pinning";
import { principalFromAuthMe } from "../rbac/permissions";
import {
  isSessionExpired,
  loadPersistedSession,
  setBiometricEnabled as persistBiometric,
  setPinEnabled as persistPinEnabled,
  touchLastActive,
} from "../session/session-manager";
import { setPin, clearPin } from "../pin/service";

export type MobileSecurityProviderProps = {
  children: ReactNode;
  appKind: MobileAppKind;
  env: MobileSecurityEnv;
  policy?: Partial<SecurityPolicy>;
  getAccessToken?: () => string | null;
  onSessionTimeout?: () => void;
  onLoadPrincipal?: (accessToken: string) => Promise<AuthPrincipal | null>;
};

type MobileSecurityContextValue = {
  appKind: MobileAppKind;
  env: MobileSecurityEnv;
  policy: SecurityPolicy;
  locked: boolean;
  biometricEnabled: boolean;
  pinEnabled: boolean;
  principal: AuthPrincipal | null;
  integrity: Awaited<ReturnType<typeof checkDeviceIntegrity>> | null;
  unlock: () => void;
  lock: () => void;
  enableBiometric: (enabled: boolean) => Promise<void>;
  enablePin: (pin: string | null) => Promise<void>;
  setPrincipal: (principal: AuthPrincipal | null) => void;
};

const MobileSecurityContext = createContext<MobileSecurityContextValue | null>(null);

export function MobileSecurityProvider({
  children,
  appKind,
  env,
  policy: policyOverride,
  getAccessToken,
  onSessionTimeout,
  onLoadPrincipal,
}: MobileSecurityProviderProps) {
  const policy = useMemo(
    () => ({ ...DEFAULT_SECURITY_POLICY, ...policyOverride }),
    [policyOverride]
  );
  const [locked, setLocked] = useState(false);
  const [biometricEnabled, setBiometricEnabled] = useState(false);
  const [pinEnabled, setPinEnabled] = useState(false);
  const [principal, setPrincipal] = useState<AuthPrincipal | null>(null);
  const [integrity, setIntegrity] = useState<Awaited<
    ReturnType<typeof checkDeviceIntegrity>
  > | null>(null);
  const appState = useRef(AppState.currentState);

  useEffect(() => {
    configureCertificatePinning(policy);
    configureAuditBuffer(appKind, async (events) => {
      const token = getAccessToken?.();
      await fetch(`${env.apiBaseUrl}/v1/security/audit-events`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ events }),
      });
    });

    void (async () => {
      const session = await loadPersistedSession();
      setBiometricEnabled(session.biometricEnabled);
      setPinEnabled(session.pinEnabled);
      if (policy.enableIntegrityCheck) {
        setIntegrity(await checkDeviceIntegrity());
      }
      const token = session.accessToken ?? getAccessToken?.();
      if (token && onLoadPrincipal) {
        const loaded = await onLoadPrincipal(token);
        if (loaded) setPrincipal(loaded);
      }
    })();

    const sub = AppState.addEventListener("change", (next: AppStateStatus) => {
      if (appState.current.match(/active/) && next.match(/inactive|background/)) {
        void touchLastActive();
      }
      if (appState.current.match(/inactive|background/) && next === "active") {
        void (async () => {
          const expired = await isSessionExpired(policy.sessionTimeoutMinutes);
          if (expired) {
            await emitSecurityEvent("session_timeout");
            setLocked(true);
            onSessionTimeout?.();
          }
          await touchLastActive();
          await flushAuditBuffer();
        })();
      }
      appState.current = next;
    });

    const flushTimer = setInterval(() => void flushAuditBuffer(), 60_000);

    return () => {
      sub.remove();
      clearInterval(flushTimer);
    };
  }, [appKind, env.apiBaseUrl, getAccessToken, onLoadPrincipal, onSessionTimeout, policy]);

  const unlock = useCallback(() => setLocked(false), []);
  const lock = useCallback(() => setLocked(true), []);

  const enableBiometric = useCallback(async (enabled: boolean) => {
    await persistBiometric(enabled);
    setBiometricEnabled(enabled);
  }, []);

  const enablePin = useCallback(async (pin: string | null) => {
    if (pin) {
      await setPin(pin);
      await persistPinEnabled(true);
      await emitSecurityEvent("pin_set");
      setPinEnabled(true);
      return;
    }
    await clearPin();
    await persistPinEnabled(false);
    await emitSecurityEvent("pin_cleared");
    setPinEnabled(false);
  }, []);

  const value = useMemo(
    () => ({
      appKind,
      env,
      policy,
      locked,
      biometricEnabled,
      pinEnabled,
      principal,
      integrity,
      unlock,
      lock,
      enableBiometric,
      enablePin,
      setPrincipal,
    }),
    [
      appKind,
      biometricEnabled,
      enableBiometric,
      enablePin,
      env,
      integrity,
      lock,
      locked,
      pinEnabled,
      policy,
      principal,
      unlock,
    ]
  );

  return <MobileSecurityContext.Provider value={value}>{children}</MobileSecurityContext.Provider>;
}

export function useMobileSecurity() {
  const ctx = useContext(MobileSecurityContext);
  if (!ctx) throw new Error("useMobileSecurity must be used within MobileSecurityProvider");
  return ctx;
}

export function SecurityShell({ children }: { children: ReactNode }) {
  const { locked, biometricEnabled, pinEnabled, policy } = useMobileSecurity();

  return (
    <IntegrityGate enabled={policy.enableIntegrityCheck}>
      <BiometricGate enabled={locked || biometricEnabled}>
        <PinLockGate enabled={locked && pinEnabled}>{children}</PinLockGate>
      </BiometricGate>
    </IntegrityGate>
  );
}

export { principalFromAuthMe };
