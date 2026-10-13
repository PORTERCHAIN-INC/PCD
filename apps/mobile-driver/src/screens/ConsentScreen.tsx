/**
 * Location consent explainer, shown before the OS "Always allow" prompt (PIPEDA meaningful
 * consent; GDPR Art. 13 notice). Plain words: what, when, who sees it, how long, how to stop.
 */
import { StyleSheet, View } from "react-native";
import type { MonitoringPolicy } from "../api";
import { showMonitoringPolicy } from "../compliance";
import { locationRetentionDays } from "../config";
import { humanError } from "../errorCopy";
import {
  Banner,
  Body,
  Button,
  Card,
  Heading,
  Label,
  Muted,
  Screen,
  Strong,
  Title,
} from "../ui/kit";
import { Rise } from "../ui/motion";
import { space } from "../ui/theme";

const POINTS: Array<{ title: string; body: string }> = [
  {
    title: "Only while you're on duty",
    body: "Sharing starts when you tap Go on duty and stops when you go off duty or sign out. Never on your own time.",
  },
  {
    title: "Why",
    body: "So dispatch can see the van, give customers an accurate arrival time, and confirm you reached each stop.",
  },
  {
    title: "Even with the screen locked",
    body: 'Your phone will ask to allow location "Always". That keeps the van on the map while you drive. Choose "While using" if you prefer — dispatch then sees you only while the app is open.',
  },
  {
    title: "Who sees it",
    body: "PorterChain dispatch. A customer sees the van on the live-tracking map only for their own delivery while it is on the way. It is never sold or used for ads.",
  },
  {
    title: "How long it's kept",
    body: `Location points are deleted after ${locationRetentionDays} days, unless needed for a delivery dispute or claim.`,
  },
  {
    title: "Your choice",
    body: "Turn it off any time in Me → Location & privacy, or in your phone's Settings. Ask dispatch for a copy of your data or to delete it.",
  },
];

export function ConsentScreen({
  onAgree,
  onNotNow,
  busy,
  policy,
  error,
}: {
  onAgree: () => void;
  onNotNow: () => void;
  busy?: boolean;
  /** Ontario electronic monitoring policy from the server (version shown + agreed to). */
  policy?: MonitoringPolicy | null;
  error?: string | null;
}) {
  return (
    <Screen
      testID="screen-consent"
      footer={
        <>
          <Button
            tone="primary"
            testID="consent-agree"
            label="I agree — continue"
            hint="Then your phone asks for location permission"
            busy={busy}
            onPress={onAgree}
          />
          <Button tone="quiet" testID="consent-not-now" label="Not now" onPress={onNotNow} />
        </>
      }
    >
      <Label>Location · electronic monitoring</Label>
      <Title>Sharing your location</Title>
      <Body>Before we ask your phone for location access, here's exactly how it's used.</Body>
      {error ? <Banner tone="danger" title={humanError(error)} testID="consent-error" /> : null}
      {POINTS.map((p, i) => (
        <Rise key={p.title} index={i}>
          <Card>
            <Heading>{p.title}</Heading>
            <Body>{p.body}</Body>
          </Card>
        </Rise>
      ))}
      <Card testID="consent-policy">
        <Heading>{policy?.title ?? "Electronic Monitoring Policy"}</Heading>
        <Body>
          Ontario law asks us to tell you how we monitor drivers electronically. Tapping I agree
          records that you have read version {policy?.version ?? "2026-10"}.
        </Body>
        <Button
          label="Read the full policy"
          testID="consent-read-policy"
          onPress={() => showMonitoringPolicy(policy)}
        />
      </Card>
      <View style={styles.foot}>
        <Muted>
          <Strong>Not now</Strong> keeps location off in the background. You can still work while
          the app is open.
        </Muted>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({ foot: { paddingHorizontal: space.xs } });
