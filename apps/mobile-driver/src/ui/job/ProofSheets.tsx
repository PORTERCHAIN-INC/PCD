/** One focused sheet per proof the server asks for: signature, receiver ID, receiver code. */
import { useState } from "react";
import { Pressable, StyleSheet, TextInput, View } from "react-native";
import type { PodDraft } from "../../stop/podDraft";
import { Body, Button, Muted, Strong } from "../kit";
import { Sheet } from "../Sheet";
import { SignaturePad } from "../SignaturePad";
import { color, radius, space, target, type } from "../theme";

export type ProofSheet = "signature" | "id_check" | "otp" | null;

const ID_TYPES = [
  { id: "drivers_licence", label: "Driver's licence" },
  { id: "photo_id_card", label: "Ontario Photo Card" },
  { id: "health_card", label: "Health card" },
  { id: "passport", label: "Passport" },
  { id: "other_government", label: "Other government photo ID" },
];

export function ProofSheets({
  open,
  pod,
  pharmacy,
  onChange,
  onClose,
}: {
  open: ProofSheet;
  pod: PodDraft;
  pharmacy: boolean;
  onChange: (next: PodDraft) => void;
  onClose: () => void;
}) {
  const [signature, setSignature] = useState("");
  const [padKey, setPadKey] = useState(0);
  const [otp, setOtp] = useState(pod.otp);

  return (
    <>
      <Sheet
        visible={open === "signature"}
        title="Receiver signature"
        onClose={onClose}
        testID="sheet-signature"
        footer={
          <>
            <Button
              tone="primary"
              label="Save signature"
              disabled={!signature}
              onPress={() => {
                onChange({ ...pod, signature });
                onClose();
              }}
            />
            <Button
              label="Clear"
              disabled={!signature}
              onPress={() => {
                setSignature("");
                setPadKey((k) => k + 1);
              }}
            />
          </>
        }
      >
        <Body>Hand the phone to the receiver. They sign in the box with a finger.</Body>
        <SignaturePad key={padKey} onChange={setSignature} />
      </Sheet>

      <Sheet
        visible={open === "id_check"}
        title="Check receiver ID"
        onClose={onClose}
        testID="sheet-id"
        footer={
          <Button
            tone="primary"
            label="Photo and name match"
            disabled={!pod.idType}
            hint="Confirms the ID photo and name match the receiver"
            onPress={() => {
              onChange({ ...pod, idNameMatches: true });
              onClose();
            }}
          />
        }
      >
        {pharmacy ? (
          <Strong>Pharmacy / medical: hand over only to the named receiver.</Strong>
        ) : null}
        <Body>Which photo ID did they show?</Body>
        {ID_TYPES.map((t) => {
          const on = pod.idType === t.id;
          return (
            <Pressable
              key={t.id}
              accessibilityRole="radio"
              accessibilityState={{ selected: on }}
              onPress={() => onChange({ ...pod, idType: t.id, idNameMatches: false })}
              style={[styles.choice, on && styles.choiceOn]}
            >
              <Strong style={on ? styles.choiceTextOn : undefined}>{t.label}</Strong>
            </Pressable>
          );
        })}
        <Muted>Never write down or photograph the ID number.</Muted>
      </Sheet>

      <Sheet
        visible={open === "otp"}
        title="Receiver code"
        onClose={onClose}
        testID="sheet-otp"
        footer={
          <Button
            tone="primary"
            label="Save code"
            disabled={otp.trim().length < 4}
            onPress={() => {
              onChange({ ...pod, otp: otp.trim() });
              onClose();
            }}
          />
        }
      >
        <Body>Ask the receiver for the code in their PorterChain message.</Body>
        <View>
          <TextInput
            style={styles.otp}
            value={otp}
            onChangeText={(v) => setOtp(v.replace(/\D/g, "").slice(0, 8))}
            keyboardType="number-pad"
            autoFocus
            accessibilityLabel="Receiver code"
            placeholder="••••••"
            placeholderTextColor={color.border}
            testID="otp-input"
          />
        </View>
      </Sheet>
    </>
  );
}

const styles = StyleSheet.create({
  choice: {
    minHeight: target.min,
    borderRadius: radius.md,
    borderWidth: 2,
    borderColor: color.ink,
    backgroundColor: color.surface,
    paddingHorizontal: space.lg,
    justifyContent: "center",
  },
  choiceOn: { backgroundColor: color.primary, borderColor: color.primary },
  choiceTextOn: { color: color.onPrimary },
  otp: {
    ...type.display,
    letterSpacing: 8,
    textAlign: "center",
    minHeight: target.primary,
    borderRadius: radius.lg,
    borderWidth: 2,
    borderColor: color.ink,
    backgroundColor: color.surface,
    color: color.ink,
  },
});
