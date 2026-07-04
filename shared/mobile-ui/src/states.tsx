"use client";

import type { ReactNode } from "react";
import { ActivityIndicator, View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Button } from "./button";
import { Body, Headline, Title } from "./typography";

type StateAction = { label: string; onPress: () => void };

function StateIcon({ color, children }: { color: string; children: string }) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        width: 56,
        height: 56,
        borderRadius: theme.radii.full,
        backgroundColor: color,
        alignItems: "center",
        justifyContent: "center",
        marginBottom: theme.spacing.lg,
      }}
    >
      <Title style={{ color: theme.colors.text }}>{children}</Title>
    </View>
  );
}

function StateShell({
  icon,
  title,
  message,
  action,
  children,
}: {
  icon: ReactNode;
  title: string;
  message?: string;
  action?: StateAction;
  children?: ReactNode;
}) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flex: 1,
        alignItems: "center",
        justifyContent: "center",
        padding: theme.spacing["3xl"],
      }}
    >
      {icon}
      <Headline style={{ textAlign: "center" }}>{title}</Headline>
      {message ? (
        <Body muted style={{ textAlign: "center", marginTop: theme.spacing.sm }}>
          {message}
        </Body>
      ) : null}
      {children}
      {action ? (
        <Button label={action.label} onPress={action.onPress} style={{ marginTop: theme.spacing["2xl"] }} />
      ) : null}
    </View>
  );
}

export function LoadingState({ message = "Loading…" }: { message?: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: theme.spacing["3xl"] }}>
      <ActivityIndicator size="large" color={theme.colors.secondary} />
      <Body muted style={{ marginTop: theme.spacing.lg }}>
        {message}
      </Body>
    </View>
  );
}

export function EmptyState({
  title = "Nothing here yet",
  message,
  action,
}: {
  title?: string;
  message?: string;
  action?: StateAction;
}) {
  const { theme } = useTheme();
  return (
    <StateShell
      icon={<StateIcon color={theme.colors.surfaceMuted}>○</StateIcon>}
      title={title}
      message={message}
      action={action}
    />
  );
}

export function ErrorState({
  title = "Something went wrong",
  message = "We couldn't load this content. Please try again.",
  action,
}: {
  title?: string;
  message?: string;
  action?: StateAction;
}) {
  const { theme } = useTheme();
  return (
    <StateShell
      icon={<StateIcon color={theme.colors.dangerSoft}>!</StateIcon>}
      title={title}
      message={message}
      action={action ?? { label: "Try again", onPress: () => {} }}
    />
  );
}

export function SuccessState({
  title = "All set",
  message,
  action,
}: {
  title?: string;
  message?: string;
  action?: StateAction;
}) {
  const { theme } = useTheme();
  return (
    <StateShell
      icon={<StateIcon color={theme.colors.successSoft}>✓</StateIcon>}
      title={title}
      message={message}
      action={action}
    />
  );
}
