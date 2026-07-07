"use client";

import { Modal, Pressable, View } from "react-native";
import { shadowForScheme, useTheme } from "@porterchain/mobile-theme";
import { Button } from "./button";
import { Body, Title } from "./typography";

export type DialogProps = {
  visible: boolean;
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
  onDismiss?: () => void;
};

export function Dialog({
  visible,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive,
  onConfirm,
  onCancel,
  onDismiss,
}: DialogProps) {
  const { theme } = useTheme();

  const dismiss = onDismiss ?? onCancel;

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={dismiss}>
      <Pressable
        style={{
          flex: 1,
          backgroundColor: theme.colors.overlay,
          alignItems: "center",
          justifyContent: "center",
          padding: theme.spacing["2xl"],
        }}
        onPress={dismiss}
      >
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{
            width: "100%",
            maxWidth: 360,
            backgroundColor: theme.colors.surface,
            borderRadius: theme.radii.xl,
            padding: theme.spacing["2xl"],
            borderWidth: 1,
            borderColor: theme.colors.border,
            ...shadowForScheme("lg", theme.scheme),
          }}
        >
          <Title>{title}</Title>
          {message ? (
            <Body muted style={{ marginTop: theme.spacing.sm }}>
              {message}
            </Body>
          ) : null}
          <View
            style={{
              flexDirection: "row",
              justifyContent: "flex-end",
              gap: theme.spacing.sm,
              marginTop: theme.spacing["2xl"],
            }}
          >
            {onCancel ? <Button label={cancelLabel} variant="ghost" onPress={onCancel} /> : null}
            {onConfirm ? (
              <Button
                label={confirmLabel}
                variant={destructive ? "danger" : "primary"}
                onPress={onConfirm}
              />
            ) : null}
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
