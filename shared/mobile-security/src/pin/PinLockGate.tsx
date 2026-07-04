"use client";

import { useEffect, useState, type ReactNode } from "react";
import { ActivityIndicator, Pressable, View } from "react-native";
import { Body, Caption, Input } from "@porterchain/mobile-ui";
import { emitSecurityEvent } from "../audit/emitter";
import { verifyPin } from "../pin/service";

export function PinLockGate({
  enabled,
  children,
}: {
  enabled: boolean;
  children: ReactNode;
}) {
  const [unlocked, setUnlocked] = useState(!enabled);
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) setUnlocked(true);
  }, [enabled]);

  async function submit() {
    const ok = await verifyPin(pin);
    if (ok) {
      await emitSecurityEvent("pin_unlock_success");
      setUnlocked(true);
      setError(null);
      return;
    }
    await emitSecurityEvent("pin_unlock_failure");
    setError("Incorrect PIN");
    setPin("");
  }

  if (!enabled || unlocked) return <>{children}</>;

  return (
    <View style={{ flex: 1, justifyContent: "center", padding: 24, gap: 16 }}>
      <Body style={{ fontSize: 22, fontWeight: "700" }}>Enter PIN</Body>
      <Caption>Your session was locked for security.</Caption>
      <Input label="PIN" value={pin} onChangeText={setPin} keyboardType="number-pad" secureTextEntry maxLength={6} />
      {error ? <Caption style={{ color: "#b42318" }}>{error}</Caption> : null}
      <Pressable onPress={() => void submit()} style={{ padding: 14, backgroundColor: "#124835", borderRadius: 12 }}>
        <Body style={{ color: "#fff", textAlign: "center", fontWeight: "600" }}>Unlock</Body>
      </Pressable>
      <ActivityIndicator />
    </View>
  );
}
