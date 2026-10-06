import { Component, type ErrorInfo, type ReactNode } from "react";
import { Text, View, StyleSheet } from "react-native";
import { colors, spacing, typography } from "@porterchain/mobile-theme";
import { PrimaryButton } from "./PrimaryButton";

type Props = { children: ReactNode };
type State = { error: Error | null };

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("customer_app_crash", error.message, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <View style={styles.wrap}>
        <Text style={styles.title}>Something broke</Text>
        <Text style={styles.lede}>This screen hit an unexpected error.</Text>
        <Text style={styles.detail}>{this.state.error.message}</Text>
        <PrimaryButton label="Retry" onPress={() => this.setState({ error: null })} />
      </View>
    );
  }
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    justifyContent: "center",
    gap: spacing.lg,
    padding: spacing.xl,
    backgroundColor: colors.grayBg,
  },
  title: { ...typography.title, color: colors.primary },
  lede: { ...typography.body, color: colors.muted },
  detail: { ...typography.caption, color: colors.danger },
});
