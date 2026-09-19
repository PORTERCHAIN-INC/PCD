import { useCallback, useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import {
  acceptOrder,
  arriveStop,
  fetchPublicHealth,
  reportException,
  retryOfflineFailed,
} from "./src/api";
import { SessionGate } from "./src/auth/SessionGate";
import { allowDevAuth } from "./src/config";
import { completeStopAction } from "./src/hooks/completeStopAction";
import { useDriverDeepLinks } from "./src/hooks/useDriverDeepLinks";
import { useEnterRoute } from "./src/hooks/useEnterRoute";
import { useFieldSession } from "./src/hooks/useFieldSession";
import { openTurnByTurn } from "./src/maps";
import { flushOfflineQueues, runOnlineOrQueue } from "./src/offline";
import { setActiveJobNotification } from "./src/push";
import { DocsScreen } from "./src/screens/DocsScreen";
import { ForceUpdateScreen } from "./src/screens/ForceUpdateScreen";
import { InboxScreen } from "./src/screens/InboxScreen";
import { InviteScreen } from "./src/screens/InviteScreen";
import { JobDetailScreen } from "./src/screens/JobDetailScreen";
import { JobsScreen } from "./src/screens/JobsScreen";
import { MoneyScreen } from "./src/screens/MoneyScreen";
import { MoreScreen } from "./src/screens/MoreScreen";
import { OnboardingScreen } from "./src/screens/OnboardingScreen";
import { RouteScreen } from "./src/screens/RouteScreen";
import { SignInScreen } from "./src/screens/SignInScreen";
import { SupportScreen } from "./src/screens/SupportScreen";
import { FieldShell } from "./src/ui/FieldShell";
import { AppErrorBoundary } from "./src/ui/AppErrorBoundary";
import { emptyPodDraft, type PodDraft } from "./src/ui/PodCapture";
import type { FieldTab, MobileDriverPolicy, Screen } from "./src/types";
import { currentAppVersion, isBelowMinVersion } from "./src/version";

// Universal / App Link: /auth/driver-invite · /jobs/{id}
// Background location task must register before App mounts (see index.ts).

function DriverApp() {
  const [screen, setScreen] = useState<Screen>("sign-in");
  const [tab, setTab] = useState<FieldTab>("work");
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [action, setAction] = useState<string | null>(null);
  const [navBusy, setNavBusy] = useState(false);
  const [podDraft, setPodDraft] = useState<PodDraft>(emptyPodDraft());
  const [focusOrderId, setFocusOrderId] = useState<string | null>(null);
  const [scanComplete, setScanComplete] = useState(false);
  const [moneyTick, setMoneyTick] = useState(0);
  const [updatePolicy, setUpdatePolicy] = useState<MobileDriverPolicy | null>(null);
  const [updateSoft, setUpdateSoft] = useState(false);

  const {
    handshake,
    setHandshake,
    busy,
    setBusy,
    location,
    offlinePending,
    offlineNote,
    setOfflineNote,
    lastFlush,
    applyFlush,
    refreshHandshake,
    refreshOfflineCount,
    goOnDuty,
    goOffDuty,
  } = useFieldSession();

  useEffect(() => {
    const orderId = handshake.currentOrderId;
    if (!orderId || !handshake.online) {
      void setActiveJobNotification(null);
      return;
    }
    void setActiveJobNotification({
      orderId,
      orderNumber: handshake.currentOrderNumber,
    });
  }, [handshake.currentOrderId, handshake.currentOrderNumber, handshake.online]);

  useEffect(() => {
    void fetchPublicHealth()
      .then((health) => {
        const policy = health.mobile?.driver;
        if (!policy?.min_version) return;
        if (!isBelowMinVersion(currentAppVersion(), policy.min_version)) return;
        setUpdatePolicy(policy);
        setUpdateSoft(!policy.force_update);
        setScreen("force-update");
      })
      .catch(() => {
        /* offline / first boot */
      });
  }, []);

  const openJob = useCallback((orderId: string) => {
    setFocusOrderId(orderId);
    setScreen("job-detail");
  }, []);

  const onInvite = useCallback((token: string) => {
    setInviteToken(token);
    setScreen("invite");
  }, []);

  const enterRoute = useEnterRoute({
    location,
    setBusy,
    setHandshake,
    setTab,
    setScreen,
  });

  useDriverDeepLinks({
    onInvite,
    onJob: openJob,
    onPushWithoutJob: enterRoute,
  });

  const runAction = async (name: string, work: () => Promise<unknown>) => {
    setAction(name);
    try {
      await work();
      await refreshHandshake();
    } catch (err) {
      setHandshake((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : name,
      }));
    } finally {
      setAction(null);
    }
  };

  return (
    <>
      {screen === "force-update" && updatePolicy ? (
        <ForceUpdateScreen
          policy={updatePolicy}
          soft={updateSoft}
          onContinue={
            updateSoft
              ? () => {
                  setUpdatePolicy(null);
                  setScreen("sign-in");
                }
              : undefined
          }
        />
      ) : null}
      {screen === "invite" ? (
        <InviteScreen inviteToken={inviteToken} error={handshake.error} onContinue={enterRoute} />
      ) : null}
      {screen === "sign-in" ? (
        <SignInScreen handshake={handshake} probing={busy} onContinue={enterRoute} />
      ) : null}
      {screen === "onboarding" ? (
        <OnboardingScreen
          allowSkip={allowDevAuth()}
          onReady={() => {
            setTab("work");
            setScreen("route");
          }}
          onSkipDev={() => {
            setTab("work");
            setScreen("route");
          }}
        />
      ) : null}
      {screen === "job-detail" && focusOrderId ? (
        <JobDetailScreen
          orderId={focusOrderId}
          onBack={() => {
            setFocusOrderId(null);
            setScreen("route");
            setTab("jobs");
          }}
          onOpenWork={() => {
            setFocusOrderId(null);
            setTab("work");
            setScreen("route");
            void refreshHandshake();
          }}
        />
      ) : null}
      {screen === "inbox" ? (
        <InboxScreen
          onBack={() => {
            setScreen("route");
            setTab("more");
          }}
          onOpenJob={openJob}
        />
      ) : null}
      {screen === "support" ? (
        <SupportScreen
          onBack={() => {
            setScreen("route");
            setTab("more");
          }}
        />
      ) : null}
      {screen === "route" ? (
        <FieldShell tab={tab} onTab={setTab}>
          {tab === "work" ? (
            <RouteScreen
              handshake={handshake}
              refreshing={busy}
              action={action}
              navBusy={navBusy}
              podDraft={podDraft}
              offlinePending={offlinePending}
              offlineNote={offlineNote}
              lastFlush={lastFlush}
              scanComplete={scanComplete}
              onDismissOfflineNote={() => setOfflineNote(null)}
              onPodChange={setPodDraft}
              onScanCompleteChange={setScanComplete}
              onRefresh={() => void refreshHandshake()}
              onDuty={() =>
                void runAction("duty", async () => {
                  if (handshake.online) {
                    await goOffDuty();
                    return;
                  }
                  await goOnDuty(handshake.routeId);
                })
              }
              onArrive={() =>
                void runAction("arrive", async () => {
                  if (!handshake.routeId || !handshake.stopId) throw new Error("no_stop");
                  await runOnlineOrQueue(
                    "arrive_stop",
                    { stop_id: handshake.stopId, route_id: handshake.routeId },
                    () => arriveStop(handshake.routeId as string, handshake.stopId as string)
                  );
                })
              }
              onComplete={() =>
                void runAction("deliver", async () => {
                  await completeStopAction({
                    routeId: handshake.routeId,
                    stopId: handshake.stopId,
                    nextStopType: handshake.nextStopType,
                    otpRequired: handshake.otpRequired,
                    podDraft,
                    setPodDraft,
                  });
                  setMoneyTick((n) => n + 1);
                })
              }
              onAccept={() =>
                void runAction("accept", () => {
                  if (!handshake.currentOrderId) throw new Error("no_job");
                  return acceptOrder(handshake.currentOrderId);
                })
              }
              onNavigate={() => {
                setNavBusy(true);
                void openTurnByTurn({
                  navigationUrl: handshake.navigationUrl,
                  lat: handshake.destLat,
                  lng: handshake.destLng,
                  address: handshake.nextStop,
                })
                  .catch((err: unknown) => {
                    setHandshake((prev) => ({
                      ...prev,
                      error: err instanceof Error ? err.message : "navigate_failed",
                    }));
                  })
                  .finally(() => setNavBusy(false));
              }}
              onException={(reason) =>
                void runAction("exception", async () => {
                  if (!handshake.routeId || !handshake.stopId) throw new Error("no_stop");
                  await reportException(handshake.routeId, handshake.stopId, reason);
                })
              }
              onPhotoError={(message) => {
                setHandshake((prev) => ({ ...prev, error: message }));
              }}
              onFlushOffline={() =>
                void runAction("flush", async () => {
                  const result = await flushOfflineQueues();
                  applyFlush(result);
                  try {
                    await retryOfflineFailed();
                  } catch {
                    /* server retry optional when queue empty */
                  }
                  await refreshOfflineCount();
                  if (!result.synced && result.queued === 0 && result.gps_flushed === 0) {
                    throw new Error("nothing_to_sync");
                  }
                })
              }
            />
          ) : null}
          {tab === "jobs" ? (
            <JobsScreen
              currentOrderId={handshake.currentOrderId}
              onOpenWork={() => setTab("work")}
              onOpenJob={openJob}
              onSequenceApplied={() => void refreshHandshake()}
            />
          ) : null}
          {tab === "money" ? <MoneyScreen refreshToken={moneyTick} /> : null}
          {tab === "docs" ? <DocsScreen /> : null}
          {tab === "more" ? (
            <MoreScreen
              handshake={handshake}
              onOpenInbox={() => setScreen("inbox")}
              onOpenSupport={() => setScreen("support")}
              onSignedOut={() => {
                setPodDraft(emptyPodDraft());
                setFocusOrderId(null);
                setTab("work");
                setScreen("sign-in");
              }}
            />
          ) : null}
        </FieldShell>
      ) : null}
      <StatusBar style="dark" />
    </>
  );
}

export default function App() {
  return (
    <SessionGate>
      <AppErrorBoundary>
        <DriverApp />
      </AppErrorBoundary>
    </SessionGate>
  );
}
