import { createContext, type ReactNode, useContext, useLayoutEffect, useMemo } from "react";
import { ActivityIndicator, Text, StyleSheet } from "react-native";
import { ClerkProvider, useAuth } from "@clerk/expo";
import { tokenCache } from "@clerk/expo/token-cache";
import { colors, typography } from "@porterchain/mobile-theme";
import { allowDevAuth, clerkPublishableKey } from "../config";
import { setSessionSnapshot } from "../session";
import { Screen } from "../ui/Screen";

type SessionView = {
  ready: boolean;
  signedIn: boolean;
};

const SessionContext = createContext<SessionView>({ ready: true, signedIn: allowDevAuth() });

export function useSessionView(): SessionView {
  return useContext(SessionContext);
}

function Boot() {
  return (
    <Screen>
      <ActivityIndicator color={colors.secondary} />
      <Text style={styles.boot}>Starting Porterchain…</Text>
    </Screen>
  );
}

function ClerkBridge({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, isSignedIn, signOut } = useAuth();
  const view = useMemo(
    () => ({ ready: isLoaded, signedIn: Boolean(isSignedIn) }),
    [isLoaded, isSignedIn]
  );

  useLayoutEffect(() => {
    setSessionSnapshot({
      ready: isLoaded,
      signedIn: Boolean(isSignedIn),
      getToken: async () => {
        const token = (await getToken()) ?? null;
        if (token) return token;
        return allowDevAuth() ? "dev" : null;
      },
      signOut: async () => {
        await signOut();
      },
    });
  }, [getToken, isLoaded, isSignedIn, signOut]);

  if (!isLoaded) return <Boot />;
  return <SessionContext.Provider value={view}>{children}</SessionContext.Provider>;
}

function DevBridge({ children }: { children: ReactNode }) {
  const view = useMemo(() => ({ ready: true, signedIn: allowDevAuth() }), []);

  useLayoutEffect(() => {
    setSessionSnapshot({
      ready: true,
      signedIn: allowDevAuth(),
      getToken: async () => (allowDevAuth() ? "dev" : null),
      signOut: async () => {
        setSessionSnapshot({
          ready: true,
          signedIn: false,
          getToken: async () => null,
          signOut: async () => undefined,
        });
      },
    });
  }, []);

  return <SessionContext.Provider value={view}>{children}</SessionContext.Provider>;
}

export function SessionGate({ children }: { children: ReactNode }) {
  if (clerkPublishableKey) {
    return (
      <ClerkProvider publishableKey={clerkPublishableKey} tokenCache={tokenCache}>
        <ClerkBridge>{children}</ClerkBridge>
      </ClerkProvider>
    );
  }
  return <DevBridge>{children}</DevBridge>;
}

const styles = StyleSheet.create({
  boot: {
    ...typography.body,
    color: colors.muted,
    textAlign: "center",
  },
});
