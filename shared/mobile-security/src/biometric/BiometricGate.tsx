"use client";

import { useEffect, useState, type ReactNode } from "react";
import { ActivityIndicator, View } from "react-native";
import { authenticateWithBiometrics } from "../biometric/service";
import { emitSecurityEvent } from "../audit/emitter";

export function BiometricGate({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const [unlocked, setUnlocked] = useState(!enabled);

  useEffect(() => {
    if (!enabled) {
      setUnlocked(true);
      return;
    }
    void (async () => {
      const ok = await authenticateWithBiometrics("Unlock Porterchain");
      if (ok) {
        await emitSecurityEvent("biometric_unlock_success");
        setUnlocked(true);
      } else {
        await emitSecurityEvent("biometric_unlock_failure");
      }
    })();
  }, [enabled]);

  if (!unlocked) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator />
      </View>
    );
  }

  return <>{children}</>;
}
