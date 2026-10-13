import { useEffect, useState } from "react";
import { Linking, StyleSheet, View } from "react-native";
import { fetchSupportHub } from "../api";
import { dispatchEmail, dispatchPhone, driverPortalUrl, locationRetentionDays } from "../config";
import type { MonitoringPolicy } from "../api";
import { haptic } from "../haptics";
import { Rise } from "../ui/motion";
import { usePolicyPage } from "../ui/PolicyPage";
import type { LocationConsent } from "../consent";
import { useSos } from "../ui/SosButton";
import type { FieldSession } from "../hooks/useFieldSession";
import { readQueue } from "../offline";
import { currentAppVersion } from "../version";
import { Banner, Body, Button, Card, Heading, Label, Muted, Screen, Title } from "../ui/kit";
import { space } from "../ui/theme";

type Props = {
  field: FieldSession;
  consent: LocationConsent;
  policy?: MonitoringPolicy | null;
  onReviewConsent: () => void;
  onWithdrawConsent: () => void;
  onSync: () => void;
  onSignOut: () => Promise<void>;
};

export function MeScreen({
  field,
  consent,
  policy,
  onReviewConsent,
  onWithdrawConsent,
  onSync,
  onSignOut,
}: Props) {
  const { handshake: h, pending } = field;
  const [phone, setPhone] = useState(dispatchPhone);
  const [email, setEmail] = useState(dispatchEmail);
  const { state: sos, ask: sendSos, page: sosPage } = useSos();
  const policyPage = usePolicyPage();
  /** Inline confirm (no popup): null = closed, number = unsynced actions found. */
  const [confirmOut, setConfirmOut] = useState<number | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    void fetchSupportHub()
      .then((hub) => {
        if (hub.emergency_contact?.ops_hotline) setPhone(hub.emergency_contact.ops_hotline);
        if (hub.emergency_contact?.ops_email) setEmail(hub.emergency_contact.ops_email);
      })
      .catch(() => undefined);
  }, []);

  const goSignOut = () => {
    setSigningOut(true);
    void onSignOut().finally(() => setSigningOut(false));
  };
  const signOut = () => {
    haptic.press();
    void readQueue()
      .then((q) => setConfirmOut(q.length))
      .catch(() => setConfirmOut(0));
  };

  return (
    <Screen testID="screen-me">
      <Title>{h.driverName ?? "Me"}</Title>
      <Muted>{h.online ? "On duty" : "Off duty"}</Muted>
      {h.push.kind === "denied" ? (
        <Banner
          tone="warn"
          title="Job alerts are off"
          body="Turn on notifications for PorterChain Driver in Settings, or you will miss new jobs."
          action={{ label: "Open Settings", onPress: () => void Linking.openSettings() }}
        />
      ) : null}

      <Card testID="me-dispatch">
        <Heading>Dispatch</Heading>
        {phone ? (
          <Button
            tone="primary"
            label="Call dispatch"
            hint={phone}
            onPress={() => void Linking.openURL(`tel:${phone}`)}
          />
        ) : null}
        <Button
          label="Email dispatch"
          hint={email}
          onPress={() => void Linking.openURL(`mailto:${email}`)}
        />
        <Button
          tone="danger"
          label="SOS — emergency"
          testID="sos"
          busy={sos === "sending"}
          onPress={sendSos}
        />
        {sos === "sent" ? (
          <Banner tone="success" title="SOS sent. Dispatch will call you." />
        ) : null}
        {sos === "failed" ? (
          <Banner
            tone="danger"
            title="SOS did not send"
            body="No connection. Call dispatch or 911."
            action={{ label: "Call 911", onPress: () => void Linking.openURL("tel:911") }}
          />
        ) : null}
      </Card>

      <Card testID="me-sync">
        <Heading>Saved work</Heading>
        <Body>
          {pending
            ? `${pending} action${pending === 1 ? "" : "s"} waiting to sync`
            : "Everything is synced."}
        </Body>
        {pending ? <Button label="Sync now" onPress={onSync} /> : null}
      </Card>

      <Card testID="me-portal">
        <Heading>Earnings, documents & messages</Heading>
        <Body>These are on the driver web portal.</Body>
        <Button
          label="Open driver portal"
          hint="Opens in your browser"
          onPress={() => void Linking.openURL(driverPortalUrl)}
        />
      </Card>

      <Card testID="me-privacy">
        <Heading>Location & privacy</Heading>
        <Body>
          {consent
            ? `Background location: on while on duty. You agreed ${new Date(consent.agreedAt).toLocaleDateString()}.`
            : "Background location: off. Dispatch sees you only while the app is open."}
        </Body>
        <Muted>Location points are deleted after {locationRetentionDays} days.</Muted>
        <Button
          tone="quiet"
          label={`Electronic Monitoring Policy${policy ? ` (v${policy.version})` : ""}`}
          testID="me-policy"
          onPress={() => policyPage.open(policy)}
        />
        <View style={styles.row}>
          <Button label={consent ? "Review" : "Turn on"} onPress={onReviewConsent} />
          {consent ? (
            <Button tone="quiet" label="Turn off background location" onPress={onWithdrawConsent} />
          ) : null}
        </View>
      </Card>

      <Label>Account</Label>
      {confirmOut == null ? (
        <Button label="Sign out" testID="sign-out" busy={signingOut} onPress={signOut} />
      ) : (
        <Rise>
          <Banner
            tone={confirmOut ? "danger" : "warn"}
            title={confirmOut ? "Unsynced work on this phone" : "Sign out?"}
            body={
              confirmOut
                ? `${confirmOut} saved action${confirmOut === 1 ? " hasn't" : "s haven't"} reached PorterChain yet. Signing out deletes ${confirmOut === 1 ? "it" : "them"}. Get signal first if you can.`
                : "This removes your data from this phone."
            }
          />
          <View style={styles.confirm}>
            <Button
              tone="danger"
              label={confirmOut ? "Sign out anyway" : "Sign out"}
              busy={signingOut}
              onPress={goSignOut}
              testID="sign-out-confirm"
            />
            <Button tone="quiet" label="Cancel" onPress={() => setConfirmOut(null)} />
          </View>
        </Rise>
      )}
      <Muted>Version {currentAppVersion()}</Muted>
      {sosPage}
      {policyPage.page}
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: { gap: space.sm },
  confirm: { gap: space.sm, marginTop: space.sm },
});
