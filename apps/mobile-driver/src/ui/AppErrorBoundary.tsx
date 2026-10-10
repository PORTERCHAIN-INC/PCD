import { Component, type ErrorInfo, type ReactNode } from "react";
import { StyleSheet, View } from "react-native";
import { Body, Button, Muted, Title } from "./kit";
import { color, space } from "./theme";

type Props = { children: ReactNode };
type State = { error: Error | null };

/** Last-resort catch so a render bug never kills the app mid-route. Queued work is on disk. */
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
        <Title>Something went wrong</Title>
        <Body>Your saved work is safe on this phone. Tap Retry to reload.</Body>
        <Muted>{this.state.error.message}</Muted>
        <Button
          tone="primary"
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
    gap: space.md,
    padding: space.lg,
    backgroundColor: color.bg,
  },
});
