import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
} from "react";
import { ActivityIndicator, Text, StyleSheet } from "react-native";
import { ClerkProvider, useAuth, useClerk, useUser } from "@clerk/expo";
import { tokenCache } from "@clerk/expo/token-cache";
import { colors, typography } from "@porterchain/mobile-theme";
import { allowDevAuth, appEnv, clerkPublishableKey } from "../config";
import { setSessionSnapshot } from "../session";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";

const CLERK_BOOT_TIMEOUT_MS = 15_000;

type SessionView = {
  ready: boolean;
  signedIn: boolean;
  bootError: string | null;
};

const SessionContext = createContext<SessionView>({
  ready: true,
  signedIn: allowDevAuth(),
  bootError: null,
});

export function useSessionView(): SessionView {
  return useContext(SessionContext);
}

function Boot({
  timedOut,
  detail,
  onRetry,
}: {
  timedOut: boolean;
  detail?: string | null;
  onRetry?: () => void;
}) {
  return (
    <Screen testID="clerk-boot">
      {!timedOut ? <ActivityIndicator color={colors.secondary} /> : null}
      <Text style={styles.boot}>
        {timedOut ? "Couldn’t finish starting sign-in." : "Starting Porterchain…"}
      </Text>
      {detail ? <Text style={styles.hint}>{detail}</Text> : null}
      {timedOut && onRetry ? <PrimaryButton label="Retry" onPress={onRetry} /> : null}
    </Screen>
  );
}

function clerkStatus(clerk: ReturnType<typeof useClerk>): string {
  return String((clerk as { status?: string }).status ?? "?");
}

function clerkErrorMessage(clerk: ReturnType<typeof useClerk>): string | null {
  const anyClerk = clerk as {
    error?: unknown;
    errors?: Array<{ message?: string; longMessage?: string; code?: string }>;
  };
  if (typeof anyClerk.error === "string" && anyClerk.error.trim()) return anyClerk.error;
  if (anyClerk.error instanceof Error) return anyClerk.error.message;
  const first = anyClerk.errors?.[0];
  if (first?.code === "native_api_disabled") {
    return "Clerk Native API is disabled on PorterChain Platform. Enable it under Native applications.";
  }
  return first?.longMessage?.trim() || first?.message?.trim() || null;
}

function ClerkBridge({ children, onRemount }: { children: ReactNode; onRemount: () => void }) {
  const { getToken, isLoaded, isSignedIn, signOut, userId } = useAuth();
  const { user } = useUser();
  const clerk = useClerk();
  const status = clerkStatus(clerk);
  const clerkErr = clerkErrorMessage(clerk);
  const settled = isLoaded || status === "error" || status === "degraded";
  const [timedOut, setTimedOut] = useState(false);
  const bootError =
    status === "error"
      ? (clerkErr ?? "Clerk Native API may be disabled for PorterChain Platform.")
      : timedOut && !isLoaded
        ? "Clerk timed out before ready."
        : null;
  const view = useMemo(
    () => ({
      ready: settled || timedOut,
      signedIn: Boolean(isSignedIn),
      bootError,
    }),
    [bootError, isSignedIn, settled, timedOut]
  );
  const email = user?.primaryEmailAddress?.emailAddress ?? null;

  useEffect(() => {
    if (settled) {
      setTimedOut(false);
      return;
    }
    const t = setTimeout(() => setTimedOut(true), CLERK_BOOT_TIMEOUT_MS);
    return () => clearTimeout(t);
  }, [settled]);

  useLayoutEffect(() => {
    setSessionSnapshot({
      ready: settled || timedOut,
      signedIn: Boolean(isSignedIn),
      userId: userId ?? null,
      email,
      getToken: async () => {
        if (!isLoaded) return allowDevAuth() ? "dev" : null;
        const token = (await getToken()) ?? null;
        if (token) return token;
        return allowDevAuth() ? "dev" : null;
      },
      signOut: async () => {
        if (isLoaded) await signOut();
      },
    });
  }, [email, getToken, isLoaded, isSignedIn, settled, signOut, timedOut, userId]);

  if (!settled && !timedOut) return <Boot timedOut={false} detail={`env=${appEnv}`} />;
  if (!settled && timedOut) return <Boot timedOut detail={`env=${appEnv}`} onRetry={onRemount} />;
  return <SessionContext.Provider value={view}>{children}</SessionContext.Provider>;
}

function DevBridge({ children }: { children: ReactNode }) {
  const view = useMemo(
    () => ({ ready: true, signedIn: allowDevAuth(), bootError: null as string | null }),
    []
  );

  useLayoutEffect(() => {
    setSessionSnapshot({
      ready: true,
      signedIn: allowDevAuth(),
      userId: allowDevAuth() ? "dev_customer_user" : null,
      email: allowDevAuth() ? "customer@porterchain.com" : null,
      getToken: async () => (allowDevAuth() ? "dev" : null),
      signOut: async () => {
        setSessionSnapshot({
          ready: true,
          signedIn: false,
          userId: null,
          email: null,
          getToken: async () => null,
          signOut: async () => undefined,
        });
      },
    });
  }, []);

  return <SessionContext.Provider value={view}>{children}</SessionContext.Provider>;
}

export function SessionGate({ children }: { children: ReactNode }) {
  const [epoch, setEpoch] = useState(0);

  if (!clerkPublishableKey) {
    return <DevBridge>{children}</DevBridge>;
  }

  return (
    <ClerkProvider
      key={epoch}
      publishableKey={clerkPublishableKey}
      tokenCache={tokenCache}
      __experimental_disableNativeClientSync
    >
      <ClerkBridge onRemount={() => setEpoch((n) => n + 1)}>{children}</ClerkBridge>
    </ClerkProvider>
  );
}

const styles = StyleSheet.create({
  boot: {
    ...typography.body,
    color: colors.muted,
    textAlign: "center",
  },
  hint: {
    ...typography.caption,
    color: colors.muted,
    textAlign: "center",
    maxWidth: 320,
  },
});
