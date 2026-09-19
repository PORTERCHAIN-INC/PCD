import { Component, type ErrorInfo, type ReactNode } from "react";
import { Text, View, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import { PrimaryButton } from "./PrimaryButton";

type Props = { children: ReactNode };
type State = { error: Error | null };

/** Fatal UI catch — #36. Keeps field ops recoverable without a full process kill. */
export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("driver_app_crash", error.message, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <View style={styles.wrap} testID="error-boundary">
        <Text style={styles.title}>Something broke</Text>
        <Text style={styles.lede}>
          The screen hit an unexpected error. Retry to reload the field shell.
        </Text>
        <Text style={styles.detail}>{this.state.error.message}</Text>
        <PrimaryButton
          label="Retry"
          testID="error-boundary-retry"
          onPress={() => this.setState({ error: null })}
        />
      </View>
    );
  }
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    justifyContent: "center",
    gap: spacing.md,
    padding: spacing.lg,
    backgroundColor: colors.white,
  },
  title: { ...typography.title, fontSize: 24, color: colors.primary },
  lede: { ...typography.body, color: colors.muted },
  detail: {
    ...typography.caption,
    color: colors.danger,
    backgroundColor: "#fef2f2",
    borderRadius: radius.lg,
    padding: spacing.md,
  },
});
