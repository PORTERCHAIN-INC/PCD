import { useEffect, useState } from "react";
import { Alert, Linking, StyleSheet, View } from "react-native";
import { fetchSupportHub, sendEmergency } from "../api";
import { dispatchEmail, dispatchPhone, driverPortalUrl, locationRetentionDays } from "../config";
import type { LocationConsent } from "../consent";
import type { FieldSession } from "../hooks/useFieldSession";
import { readQueue } from "../offline";
import { currentAppVersion } from "../version";
import { Banner, Body, Button, Card, Heading, Label, Muted, Screen, Title } from "../ui/kit";
import { space } from "../ui/theme";

type Props = {
  field: FieldSession;
  consent: LocationConsent;
  onReviewConsent: () => void;
  onWithdrawConsent: () => void;
  onSync: () => void;
  onSignOut: () => Promise<void>;
};

export function MeScreen({
  field,
  consent,
  onReviewConsent,
  onWithdrawConsent,
  onSync,
  onSignOut,
}: Props) {
  const { handshake: h, pending } = field;
  const [phone, setPhone] = useState(dispatchPhone);
  const [email, setEmail] = useState(dispatchEmail);
  const [sos, setSos] = useState<"idle" | "sending" | "sent" | "failed">("idle");
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    void fetchSupportHub()
      .then((hub) => {
        if (hub.emergency_contact?.ops_hotline) setPhone(hub.emergency_contact.ops_hotline);
        if (hub.emergency_contact?.ops_email) setEmail(hub.emergency_contact.ops_email);
      })
      .catch(() => undefined);
  }, []);

  const signOut = () => {
    const go = () => {
      setSigningOut(true);
      void onSignOut().finally(() => setSigningOut(false));
    };
    void readQueue()
      .then((q) => {
        if (!q.length) {
          Alert.alert("Sign out?", "This removes your data from this phone.", [
            { text: "Cancel", style: "cancel" },
            { text: "Sign out", style: "destructive", onPress: go },
          ]);
          return;
        }
        Alert.alert(
          "Unsynced work on this phone",
          `${q.length} saved action${q.length === 1 ? " has" : "s have"} not reached PorterChain yet. Signing out deletes ${q.length === 1 ? "it" : "them"} from this phone. Get signal first if you can.`,
          [
            { text: "Cancel", style: "cancel" },
            { text: "Sign out anyway", style: "destructive", onPress: go },
          ]
        );
      })
      .catch(go);
  };

  const sendSos = () =>
    Alert.alert(
      "Send SOS to dispatch?",
      "Dispatch gets your location and calls you. In immediate danger, call 911.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Call 911", onPress: () => void Linking.openURL("tel:911") },
        {
          text: "Send SOS",
          style: "destructive",
          onPress: () => {
            setSos("sending");
            void sendEmergency()
              .then(() => setSos("sent"))
              .catch(() => setSos("failed"));
          },
        },
      ]
    );

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
        <View style={styles.row}>
          <Button label={consent ? "Review" : "Turn on"} onPress={onReviewConsent} />
          {consent ? (
            <Button tone="quiet" label="Turn off background location" onPress={onWithdrawConsent} />
          ) : null}
        </View>
      </Card>

      <Label>Account</Label>
      <Button label="Sign out" testID="sign-out" busy={signingOut} onPress={signOut} />
      <Muted>Version {currentAppVersion()}</Muted>
    </Screen>
  );
}

const styles = StyleSheet.create({ row: { gap: space.sm } });
