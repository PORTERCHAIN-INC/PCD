import { useEffect } from "react";
import { Alert } from "react-native";
import {
  ackMonitoringPolicy,
  fetchGpsStatus,
  fetchMonitoringPolicy,
  sendGpsConsent,
  type MonitoringPolicy,
} from "../api";
import { refreshGpsPolicy } from "../location";

export function policyText(p: MonitoringPolicy): string {
  return p.sections
    .map((s) =>
      [s.heading, s.body, ...(s.items ?? []).map((i) => `• ${i}`)].filter(Boolean).join("\n")
    )
    .join("\n\n");
}

export function showMonitoringPolicy(): void {
  void fetchMonitoringPolicy()
    .then((p) => Alert.alert(`${p.title} (v${p.version})`, policyText(p)))
    .catch(() => Alert.alert("Electronic Monitoring Policy", "Could not load. Try again online."));
}

/** On each app open after sign-in: ask for location consent / policy acknowledgment if needed. */
export function useComplianceGate(active: boolean): void {
  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void (async () => {
      try {
        const [gps, policy] = await Promise.all([fetchGpsStatus(), fetchMonitoringPolicy()]);
        const needsConsent = Boolean(gps.consent_required);
        const needsAck = !policy.acknowledged;
        if (cancelled || (!needsConsent && !needsAck)) return;
        const agree = async () => {
          if (needsAck) await ackMonitoringPolicy();
          if (needsConsent) await sendGpsConsent(true);
          await refreshGpsPolicy();
        };
        Alert.alert(
          "Location sharing and monitoring",
          `${needsConsent ? `${gps.consent_text || gps.message}\n\n` : ""}Please read our ${policy.title} (v${policy.version}). Until you agree, your location is not shared.`,
          [
            {
              text: "Read policy",
              onPress: () =>
                Alert.alert(policy.title, policyText(policy), [
                  { text: "Not now", style: "cancel" },
                  { text: "I agree", onPress: () => void agree() },
                ]),
            },
            { text: "Not now", style: "cancel" },
            { text: "I agree", onPress: () => void agree() },
          ]
        );
      } catch {
        /* offline: ask next open */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [active]);
}
