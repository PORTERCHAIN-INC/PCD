"use client";

import { useEffect, useState, type ReactNode } from "react";
import { View } from "react-native";
import { Body, Button, Caption } from "@porterchain/mobile-ui";
import { emitSecurityEvent } from "../audit/emitter";
import { checkDeviceIntegrity } from "../device/integrity";

export function IntegrityGate({
  enabled,
  children,
  mode = "warn",
}: {
  enabled: boolean;
  children: ReactNode;
  mode?: "warn" | "block";
}) {
  const [result, setResult] = useState<Awaited<ReturnType<typeof checkDeviceIntegrity>> | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    void (async () => {
      const integrity = await checkDeviceIntegrity();
      setResult(integrity);
      if (integrity.compromised) {
        await emitSecurityEvent("device_compromised", { reasons: integrity.reasons });
      }
    })();
  }, [enabled]);

  if (!enabled || !result?.compromised) return <>{children}</>;
  if (mode === "warn" && dismissed) return <>{children}</>;

  return (
    <View style={{ flex: 1, justifyContent: "center", padding: 24, gap: 12 }}>
      <Body style={{ fontSize: 22, fontWeight: "700" }}>Device integrity warning</Body>
      <Caption>
        This device may be jailbroken or rooted. Porterchain security controls may be reduced.
      </Caption>
      {result.reasons.map((reason) => (
        <Caption key={reason}>• {reason}</Caption>
      ))}
      {mode === "warn" ? (
        <Button label="Continue at my risk" variant="outline" onPress={() => setDismissed(true)} />
      ) : null}
    </View>
  );
}
