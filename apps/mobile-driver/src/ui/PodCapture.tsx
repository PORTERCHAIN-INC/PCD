import { useState } from "react";
import { Text, TextInput, View, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import { generateOtp } from "../api";
import { PrimaryButton } from "./PrimaryButton";
import { SignaturePad } from "./SignaturePad";
import { BarcodeScannerModal } from "./BarcodeScannerModal";
import { capturePodPhotoDataUrl } from "../pod";

export type PodDraft = {
  photoUrl: string | null;
  signature: string;
  barcode: string;
  otp: string;
};

type Props = {
  busy: boolean;
  draft: PodDraft;
  orderId: string | null;
  otpRequired: boolean;
  onChange: (next: PodDraft) => void;
  onPhotoError: (message: string) => void;
};

export const emptyPodDraft = (): PodDraft => ({
  photoUrl: null,
  signature: "",
  barcode: "",
  otp: "",
});

export function PodCapture({ busy, draft, orderId, otpRequired, onChange, onPhotoError }: Props) {
  const [picking, setPicking] = useState(false);
  const [otpBusy, setOtpBusy] = useState(false);
  const [otpHint, setOtpHint] = useState<string | null>(null);
  const [scanOpen, setScanOpen] = useState(false);
  const [padKey, setPadKey] = useState(0);

  return (
    <View style={styles.wrap} testID="pod-capture">
      <Text style={styles.title}>Proof of delivery</Text>
      <Text style={styles.lede}>
        Photo required before complete
        {otpRequired ? " · merchant requires receiver OTP" : ""}.
      </Text>
      <PrimaryButton
        tone="ghost"
        label={picking ? "Opening camera…" : draft.photoUrl ? "Retake photo" : "Capture photo"}
        disabled={busy || picking}
        onPress={() => {
          setPicking(true);
          void capturePodPhotoDataUrl()
            .then((url) => onChange({ ...draft, photoUrl: url }))
            .catch((err: unknown) => {
              const msg = err instanceof Error ? err.message : "photo_failed";
              onPhotoError(
                msg === "photo_too_large" ? "Photo too large — retake closer / lower quality" : msg
              );
            })
            .finally(() => setPicking(false));
        }}
      />
      <Text style={styles.meta}>{draft.photoUrl ? "Photo ready" : "No photo yet"}</Text>
      {!draft.photoUrl ? (
        <Text style={styles.meta}>Photos are compressed for offline sync</Text>
      ) : null}

      <Text style={styles.label}>Receiver signature</Text>
      <SignaturePad
        key={padKey}
        disabled={busy}
        onChange={(signature) => onChange({ ...draft, signature })}
      />
      <Text style={styles.meta}>
        {draft.signature ? "Signature captured" : "Sign above with finger"}
      </Text>
      <PrimaryButton
        tone="ghost"
        label="Clear signature"
        disabled={busy || !draft.signature}
        onPress={() => {
          onChange({ ...draft, signature: "" });
          setPadKey((k) => k + 1);
        }}
      />

      <Text style={styles.label}>Barcode / tracking</Text>
      <TextInput
        style={styles.input}
        value={draft.barcode}
        onChangeText={(barcode) => onChange({ ...draft, barcode })}
        placeholder="Optional scan code"
        placeholderTextColor={colors.muted}
        autoCapitalize="characters"
        editable={!busy}
        testID="pod-barcode-input"
      />
      <PrimaryButton
        tone="ghost"
        label="Scan with camera"
        disabled={busy}
        testID="pod-barcode-scan"
        onPress={() => setScanOpen(true)}
      />

      <Text style={styles.label}>Delivery OTP{otpRequired ? " (required)" : ""}</Text>
      <TextInput
        style={styles.input}
        value={draft.otp}
        onChangeText={(otp) => onChange({ ...draft, otp })}
        placeholder="6-digit code from receiver"
        placeholderTextColor={colors.muted}
        keyboardType="number-pad"
        editable={!busy}
        testID="pod-otp-input"
      />
      {orderId ? (
        <PrimaryButton
          tone="ghost"
          label={otpBusy ? "Generating…" : "Generate OTP for receiver"}
          disabled={busy || otpBusy}
          onPress={() => {
            setOtpBusy(true);
            setOtpHint(null);
            void generateOtp(orderId)
              .then((res) => {
                onChange({ ...draft, otp: res.otp });
                setOtpHint("OTP generated — share with receiver, then complete");
              })
              .catch((err: unknown) => {
                onPhotoError(err instanceof Error ? err.message : "otp_failed");
              })
              .finally(() => setOtpBusy(false));
          }}
        />
      ) : null}
      {otpHint ? <Text style={styles.meta}>{otpHint}</Text> : null}
      {otpRequired && !draft.otp.trim() ? (
        <Text style={styles.warn}>Enter OTP before complete</Text>
      ) : null}

      <BarcodeScannerModal
        visible={scanOpen}
        onClose={() => setScanOpen(false)}
        onScan={(barcode) => onChange({ ...draft, barcode })}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.sm,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
  },
  title: {
    ...typography.title,
    fontSize: 18,
    color: colors.primary,
  },
  lede: {
    ...typography.caption,
    color: colors.muted,
  },
  meta: {
    ...typography.caption,
    color: colors.secondary,
    fontWeight: "600",
  },
  warn: {
    ...typography.caption,
    color: colors.danger,
    fontWeight: "600",
  },
  label: {
    ...typography.caption,
    color: colors.muted,
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  input: {
    ...typography.body,
    borderWidth: 1,
    borderColor: colors.muted,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    color: colors.primary,
    minHeight: 48,
  },
});
