/**
 * PorterChain Driver. Five screens: Sign in, Location consent, and three tabs (Today, Job, Me).
 * App owns navigation and the "run an action" helper; screens own their layout; stop logic
 * lives in src/stop; data lives in useFieldSession.
 */
import { useCallback, useEffect, useState, type ReactElement } from "react";
import { BackHandler, Platform, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { fetchOnboarding, fetchPublicHealth } from "./src/api";
import { SessionGate } from "./src/auth/SessionGate";
import { allowDevAuth, driverPortalUrl } from "./src/config";
import {
  agreeToMonitoring,
  checkCompliance,
  resendPendingConsent,
  withdrawMonitoring,
} from "./src/compliance";
import { readLocationConsent, type LocationConsent } from "./src/consent";
import type { MonitoringPolicy } from "./src/api";
import { useDispatchRoute } from "./src/hooks/useDispatchRoute";
import { isSilentError } from "./src/errorCopy";
import { canEnterRoute } from "./src/gate";
import { runHandshake } from "./src/handshake";
import { useDriverDeepLinks } from "./src/hooks/useDriverDeepLinks";
import { useFieldSession } from "./src/hooks/useFieldSession";
import { startBackgroundLocation, stopBackgroundLocation } from "./src/location";
import type { PretripChecks } from "./src/pretrip";
import { setActiveJobNotification } from "./src/push";
import { clearSession, getSessionSnapshot, waitForSignedSession } from "./src/session";
import { emptyPodDraft, type PodDraft } from "./src/stop/podDraft";
import { ConsentScreen } from "./src/screens/ConsentScreen";
import { JobScreen } from "./src/screens/JobScreen";
import { MeScreen } from "./src/screens/MeScreen";
import { SignInScreen } from "./src/screens/SignInScreen";
import { TodayScreen } from "./src/screens/TodayScreen";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AppErrorBoundary } from "./src/ui/AppErrorBoundary";
import { TabBarBelow } from "./src/ui/layout";
import { toast, ToastHost } from "./src/ui/toast";
import { TabBar, type TabId } from "./src/ui/kit";
import { Notice } from "./src/ui/Notice";
import { color } from "./src/ui/theme";
import type { MobileDriverPolicy } from "./src/types";
import { currentAppVersion, isBelowMinVersion } from "./src/version";

type Blocker = { kind: "update"; policy: MobileDriverPolicy } | { kind: "setup" } | null;

function DriverApp() {
  const field = useFieldSession();
  const { handshake: h, setHandshake, setError } = field;
  const [signedInView, setSignedInView] = useState(false);
  const [blocker, setBlocker] = useState<Blocker>(null);
  const [tab, setTab] = useState<TabId>("today");
  const [pod, setPod] = useState<PodDraft>(emptyPodDraft());
  const [action, setAction] = useState<string | null>(null);
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [consent, setConsent] = useState<LocationConsent>(null);
  const [consentFor, setConsentFor] = useState<
    null | { then: "duty"; pretrip: PretripChecks } | { then: "review" }
  >(null);
  const [entering, setEntering] = useState(false);
  const [policy, setPolicy] = useState<MonitoringPolicy | null>(null);
  const [consentError, setConsentError] = useState<string | null>(null);
  const route = useDispatchRoute(signedInView && Boolean(h.online));

  useEffect(() => {
    void readLocationConsent().then(setConsent);
  }, []);

  // Minimum app version from the server.
  useEffect(() => {
    void fetchPublicHealth()
      .then((health) => {
        const policy = health.mobile?.driver;
        if (
          policy?.min_version &&
          policy.force_update &&
          isBelowMinVersion(currentAppVersion(), policy.min_version)
        ) {
          setBlocker({ kind: "update", policy });
        }
      })
      .catch(() => undefined);
  }, []);

  // Lock-screen card for the active job.
  useEffect(() => {
    void setActiveJobNotification(
      h.currentOrderId && h.online
        ? { orderId: h.currentOrderId, orderNumber: h.currentOrderNumber }
        : null
    );
  }, [h.currentOrderId, h.currentOrderNumber, h.online]);

  /** Signed in → handshake → setup check → Today. */
  const enter = useCallback(() => {
    void (async () => {
      setEntering(true);
      setError(null);
      try {
        if (!allowDevAuth()) await waitForSignedSession();
        const next = await runHandshake(h.location);
        setHandshake(next);
        const gate = canEnterRoute(next, getSessionSnapshot().signedIn, allowDevAuth());
        if (!gate.ok) {
          setHandshake({ ...next, error: gate.reason });
          return;
        }
        const onboarding = await fetchOnboarding().catch(() => null);
        if (onboarding && !onboarding.ready && !allowDevAuth()) {
          setBlocker({ kind: "setup" });
          return;
        }
        setBlocker(null);
        setInviteToken(null);
        setSignedInView(true);
        // GPS consent lives on the server (Ontario monitoring policy). If it needs a (re)agree,
        // forget the local yes so the consent screen shows before location is shared again.
        void (async () => {
          const local = await resendPendingConsent();
          const check = await checkCompliance(local);
          setPolicy(check.policy);
          if (check.needed && check.policy) {
            setConsent(null);
            if (next.online) setConsentFor({ then: "review" });
          } else setConsent(local);
        })();
        setTab(next.currentOrderId ? "job" : "today");
        void field.refreshCounts();
      } finally {
        setEntering(false);
      }
    })();
  }, [field.refreshCounts, h.location, setError, setHandshake]);

  useDriverDeepLinks({
    onInvite: (token) => {
      setInviteToken(token);
      setSignedInView(false);
    },
    onJob: () => setTab("job"),
    onPushWithoutJob: enter,
  });

  /** Run a driver action: busy state, plain-language errors, then refresh from the server. */
  const run = useCallback(
    async (name: string, work: () => Promise<unknown>) => {
      setAction(name);
      try {
        await work();
      } catch (err) {
        const code = err instanceof Error ? err.message : name;
        if (!isSilentError(code)) setError(code);
      } finally {
        setAction(null);
      }
      await field.refresh();
    },
    [field, setError]
  );

  const startDuty = (pretrip: PretripChecks) => void run("duty", () => field.goOnDuty(pretrip));

  const signOut = async () => {
    try {
      await clearSession();
    } finally {
      setConsent(null);
      setPod(emptyPodDraft());
      setTab("today");
      setSignedInView(false);
      setHandshake((prev) => ({ ...prev, online: false, error: null }));
    }
  };

  // Android back: close consent, step back to Today, never leave the app mid-stop.
  useEffect(() => {
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      if (consentFor) {
        setConsentFor(null);
        return true;
      }
      if (!signedInView) return false;
      if (tab === "job" && h.online && h.stopId) {
        toast.show(
          "warn",
          "Stop in progress",
          "Finish or report this stop first. Your work is saved."
        );
        return true;
      }
      if (tab !== "today") {
        setTab("today");
        return true;
      }
      return false;
    });
    return () => sub.remove();
  }, [consentFor, signedInView, tab, h.online, h.stopId]);

  let body: ReactElement;
  if (blocker?.kind === "update") {
    const url =
      Platform.OS === "ios" ? blocker.policy.store_url_ios : blocker.policy.store_url_android;
    body = (
      <Notice
        testID="force-update"
        title="Update required"
        body={
          blocker.policy.message ?? "This version is no longer supported. Update to keep working."
        }
        link={url ? { label: "Update the app", url } : undefined}
      />
    );
  } else if (blocker?.kind === "setup") {
    body = (
      <Notice
        testID="setup-needed"
        title="Finish your setup"
        body="Upload your licence, insurance and vehicle details on the driver portal. Then come back and tap Check again."
        link={{ label: "Open driver portal", url: `${driverPortalUrl}/onboarding` }}
        retry={{ label: "Check again", onPress: enter, busy: entering }}
      />
    );
  } else if (consentFor) {
    body = (
      <ConsentScreen
        busy={action === "duty" || action === "consent"}
        policy={policy}
        error={consentError}
        onAgree={() => {
          setAction("consent");
          setConsentError(null);
          void agreeToMonitoring(policy)
            .then((saved) => {
              setConsent(saved);
              const next = consentFor;
              setConsentFor(null);
              if (next.then === "duty") startDuty(next.pretrip);
              else if (h.online) void startBackgroundLocation();
            })
            .catch((err: Error) => setConsentError(err.message))
            .finally(() => setAction(null));
        }}
        onNotNow={() => {
          const next = consentFor;
          setConsentFor(null);
          if (next.then === "duty") startDuty(next.pretrip);
        }}
      />
    );
  } else if (!signedInView) {
    body = (
      <SignInScreen
        error={h.error}
        probing={entering}
        inviteToken={inviteToken}
        onContinue={enter}
        onSignOut={signOut}
      />
    );
  } else {
    const onSync = () => void field.refresh();
    body = (
      <View style={{ flex: 1 }}>
        <TabBarBelow.Provider value={true}>
          {tab === "today" ? (
            <TodayScreen
              field={field}
              route={route}
              action={action}
              onOpenJob={() => setTab("job")}
              onGoOnDuty={(pretrip) =>
                consent ? startDuty(pretrip) : setConsentFor({ then: "duty", pretrip })
              }
              onGoOffDuty={() => void run("duty", field.goOffDuty)}
              onSync={onSync}
            />
          ) : null}
          {tab === "job" ? (
            <JobScreen
              field={field}
              route={route}
              action={action}
              pod={pod}
              setPod={setPod}
              run={run}
              onGoToday={() => setTab("today")}
              onSync={onSync}
            />
          ) : null}
          {tab === "me" ? (
            <MeScreen
              field={field}
              consent={consent}
              onReviewConsent={() => setConsentFor({ then: "review" })}
              policy={policy}
              onWithdrawConsent={() =>
                void withdrawMonitoring().then(() => {
                  setConsent(null);
                  // Background stops now; foreground pings continue while the app is open on duty.
                  void stopBackgroundLocation();
                })
              }
              onSync={onSync}
              onSignOut={signOut}
            />
          ) : null}
        </TabBarBelow.Provider>
        <TabBar
          tab={tab}
          onTab={setTab}
          jobBadge={(Boolean(h.currentOrderId) || Boolean(route.stop)) && tab !== "job"}
        />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: color.bg }}>
      {body}
      <ToastHost />
      <StatusBar style="light" />
    </View>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <SessionGate>
        <AppErrorBoundary>
          <DriverApp />
        </AppErrorBoundary>
      </SessionGate>
    </SafeAreaProvider>
  );
}
