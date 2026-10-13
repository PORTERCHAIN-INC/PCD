/**
 * GPS consent + Ontario electronic monitoring policy, kept in step with the server.
 * Without the server-side consent (policy 2026-10) every location ping is dropped, so the
 * van is invisible to dispatch and customers — this module makes sure that never happens
 * silently.
 */
import { Alert } from "react-native";
import {
  ackMonitoringPolicy,
  fetchGpsStatus,
  fetchMonitoringPolicy,
  sendGpsConsent,
  type MonitoringPolicy,
} from "./api";
import {
  readLocationConsent,
  saveLocationConsent,
  withdrawLocationConsent,
  type LocationConsent,
} from "./consent";
import { refreshGpsPolicy } from "./location";
import { isNetworkError } from "./netErrors";

export type ComplianceCheck = {
  /** The driver must (re)agree before location is shared. */
  needed: boolean;
  policy: MonitoringPolicy | null;
  consentText: string | null;
};

export function policyText(p: MonitoringPolicy): string {
  return p.sections
    .map((s) =>
      [s.heading, s.body, ...(s.items ?? []).map((i) => `• ${i}`)].filter(Boolean).join("\n")
    )
    .join("\n\n");
}

export function showMonitoringPolicy(policy?: MonitoringPolicy | null): void {
  const show = (p: MonitoringPolicy) => Alert.alert(`${p.title} (v${p.version})`, policyText(p));
  if (policy) return show(policy);
  void fetchMonitoringPolicy()
    .then(show)
    .catch(() =>
      Alert.alert("Electronic Monitoring Policy", "Couldn't load it. Try again online.")
    );
}

/** Ask the server. Offline: fall back to the local record (never blocks work offline). */
export async function checkCompliance(local: LocationConsent): Promise<ComplianceCheck> {
  try {
    const [gps, policy] = await Promise.all([fetchGpsStatus(), fetchMonitoringPolicy()]);
    const needed =
      Boolean(gps.consent_required) ||
      !policy.acknowledged ||
      (local?.policyVersion != null && local.policyVersion !== policy.version);
    return { needed, policy, consentText: gps.consent_text ?? null };
  } catch {
    return { needed: !local, policy: null, consentText: null };
  }
}

/** "I agree": record on the server (policy ack + GPS consent), then locally. */
export async function agreeToMonitoring(policy: MonitoringPolicy | null): Promise<LocationConsent> {
  try {
    if (!policy || !policy.acknowledged) await ackMonitoringPolicy();
    await sendGpsConsent(true);
    const saved = await saveLocationConsent(new Date(), {
      policyVersion: policy?.version ?? null,
      serverSynced: true,
    });
    await refreshGpsPolicy();
    return saved;
  } catch (err) {
    if (!isNetworkError(err)) throw err;
    // Offline: remember it and tell the server on the next open.
    return saveLocationConsent(new Date(), {
      policyVersion: policy?.version ?? null,
      serverSynced: false,
    });
  }
}

/** Agreed while offline earlier → tell the server now. Silent; retried next open on failure. */
export async function resendPendingConsent(): Promise<LocationConsent> {
  const local = await readLocationConsent();
  if (!local || local.serverSynced) return local;
  try {
    return await agreeToMonitoring(null);
  } catch {
    return local;
  }
}

/** Withdraw: tell the server (best effort) and forget locally. */
export async function withdrawMonitoring(): Promise<void> {
  try {
    await sendGpsConsent(false);
  } catch {
    /* offline: server still stops storing pings when the app stops sending them */
  }
  await withdrawLocationConsent();
}
