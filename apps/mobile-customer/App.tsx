import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Text, StyleSheet } from "react-native";
import { StatusBar } from "expo-status-bar";
import * as Linking from "expo-linking";
import { colors, typography } from "@porterchain/mobile-theme";
import {
  fetchOnboarding,
  fetchSessionContext,
  hasCustomerAccess,
  probeApi,
  type OnboardingStatus,
} from "./src/api";
import { SessionGate, useSessionView } from "./src/auth/SessionGate";
import { allowDevAuth } from "./src/config";
import { humanCustomerError } from "./src/errors";
import { screenFromUrl, type VisitorTracking } from "./src/linking";
import { AccountScreen } from "./src/screens/AccountScreen";
import { ActivityScreen } from "./src/screens/ActivityScreen";
import { AlertsScreen } from "./src/screens/AlertsScreen";
import { BookScreen } from "./src/screens/BookScreen";
import { HomeScreen } from "./src/screens/HomeScreen";
import { AccessDeniedScreen, OnboardingScreen } from "./src/screens/OnboardingScreen";
import { SignInScreen } from "./src/screens/SignInScreen";
import { TrackScreen } from "./src/screens/TrackScreen";
import { clearSession } from "./src/session";
import { Screen } from "./src/ui/Screen";
import { Tabs, type TabId } from "./src/ui/Tabs";

type Phase = "signin" | "checking" | "onboarding" | "denied" | "app";

function Root() {
  const session = useSessionView();
  const [phase, setPhase] = useState<Phase>("signin");
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [gateError, setGateError] = useState<string | null>(null);
  const [denied, setDenied] = useState("");
  const [tab, setTab] = useState<TabId>("home");
  const [tracking, setTracking] = useState("");
  const [showTrack, setShowTrack] = useState(false);
  const [rebookOrderId, setRebookOrderId] = useState<string | undefined>();
  const [vehicle, setVehicle] = useState<string | undefined>();
  const [quoteId, setQuoteId] = useState<string | undefined>();
  const [visitorId, setVisitorId] = useState<string | undefined>();
  const [visitorTracking, setVisitorTracking] = useState<VisitorTracking | undefined>();
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const started = useRef(false);

  const enter = useCallback(async () => {
    setPhase("checking");
    setGateError(null);
    try {
      const status = await fetchOnboarding();
      setOnboarding(status);
      if (!status.ready) {
        setPhase("onboarding");
        return;
      }
      const ctx = await fetchSessionContext();
      if (!hasCustomerAccess(ctx.permissions)) {
        if (allowDevAuth()) {
          setPhase("app");
          return;
        }
        setDenied("This account is not provisioned for the customer portal.");
        setPhase("denied");
        return;
      }
      setPhase("app");
    } catch (err) {
      const raw = err instanceof Error ? err.message : "request_failed";
      const message = humanCustomerError(raw);
      if (
        raw.startsWith("identity_conflict") ||
        raw === "user_not_provisioned" ||
        raw === "missing_portal_permission" ||
        raw === "email_clerk_mismatch"
      ) {
        setDenied(message);
        setPhase("denied");
        return;
      }
      setGateError(message);
      setPhase("onboarding");
    }
  }, []);

  useEffect(() => {
    void probeApi().then(setApiUp);
  }, []);

  useEffect(() => {
    function apply(url: string | null) {
      const next = screenFromUrl(url);
      if (!next) return;
      if (next.screen === "track") {
        setTracking(next.tracking ?? "");
        setShowTrack(true);
      }
      if (next.screen === "book") {
        setTab("book");
        setVehicle(next.vehicle);
        setQuoteId(next.quoteId);
        setVisitorId(next.visitorId);
        setVisitorTracking(next.visitorTracking);
      }
      if (next.screen === "sign-in") setShowTrack(false);
    }
    void Linking.getInitialURL().then(apply);
    const sub = Linking.addEventListener("url", (event: { url: string }) => apply(event.url));
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (!session.ready || session.bootError) return;
    if (!session.signedIn && !allowDevAuth()) {
      started.current = false;
      setPhase("signin");
      return;
    }
    if (started.current) return;
    started.current = true;
    void enter();
  }, [enter, session.bootError, session.ready, session.signedIn]);

  async function signOut() {
    started.current = false;
    await clearSession();
    setShowTrack(false);
    setPhase("signin");
  }

  if (showTrack && phase !== "app") {
    return <TrackScreen initialTracking={tracking} onBack={() => setShowTrack(false)} />;
  }

  if (!session.ready) {
    return (
      <Screen>
        <ActivityIndicator color={colors.secondary} />
      </Screen>
    );
  }

  if (phase === "signin") {
    return (
      <SignInScreen
        apiUp={apiUp}
        onSignedIn={() => {
          started.current = false;
          started.current = true;
          void enter();
        }}
        onTrack={() => {
          setTracking("");
          setShowTrack(true);
        }}
      />
    );
  }

  if (phase === "checking") {
    return (
      <Screen>
        <ActivityIndicator color={colors.secondary} />
        <Text style={styles.meta}>Checking your account…</Text>
      </Screen>
    );
  }

  if (phase === "onboarding") {
    return (
      <OnboardingScreen
        status={onboarding}
        error={gateError}
        onRefresh={() => void enter()}
        onSignOut={() => void signOut()}
      />
    );
  }

  if (phase === "denied") {
    return <AccessDeniedScreen detail={denied} onSignOut={() => void signOut()} />;
  }

  if (showTrack) {
    return <TrackScreen initialTracking={tracking} onBack={() => setShowTrack(false)} />;
  }

  return (
    <>
      {tab === "home" ? (
        <HomeScreen
          onBook={(orderId) => {
            setRebookOrderId(orderId);
            setTab("book");
          }}
          onTrack={(number) => {
            setTracking(number);
            setShowTrack(true);
          }}
        />
      ) : null}
      {tab === "book" ? (
        <BookScreen
          rebookOrderId={rebookOrderId}
          vehicle={vehicle}
          quoteId={quoteId}
          visitorId={visitorId}
          visitorTracking={visitorTracking}
          onTracked={(number) => {
            setTracking(number);
            setShowTrack(true);
          }}
        />
      ) : null}
      {tab === "activity" ? (
        <ActivityScreen
          onTrack={(number) => {
            setTracking(number);
            setShowTrack(true);
          }}
        />
      ) : null}
      {tab === "alerts" ? (
        <AlertsScreen
          onTrack={(number) => {
            setTracking(number);
            setShowTrack(true);
          }}
        />
      ) : null}
      {tab === "account" ? <AccountScreen onSignedOut={() => void signOut()} /> : null}
      <Tabs current={tab} onChange={setTab} />
    </>
  );
}

export default function App() {
  return (
    <SessionGate>
      <Root />
      <StatusBar style="dark" />
    </SessionGate>
  );
}

const styles = StyleSheet.create({
  meta: { ...typography.caption, color: colors.muted, textAlign: "center" },
});
