import { View } from "react-native";
import type { OnboardingStatus } from "../api";
import { spacing } from "../theme";
import { Banner, Button, Card, Divider, ListRow, Txt } from "../ui/kit";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";

type Props = {
  status: OnboardingStatus | null;
  error: string | null;
  onRefresh: () => void;
  onSignOut: () => void;
};

export function OnboardingScreen({ status, error, onRefresh, onSignOut }: Props) {
  const steps = status?.steps ?? [];
  return (
    <Screen
      scroll
      testID="customer-onboarding"
      title="Finish setting up"
      subtitle="PorterChain checks these steps before opening your account."
    >
      {error ? <Banner tone="danger" text={error} /> : null}
      {steps.length ? (
        <Card style={{ paddingVertical: spacing.xs, gap: 0 }}>
          {steps.map((step, i) => (
            <View key={step.id}>
              {i ? <Divider /> : null}
              <ListRow
                icon={step.complete ? "checkmark-circle" : "ellipse-outline"}
                title={step.label}
                subtitle={
                  step.status.startsWith("conflict_")
                    ? "Wrong account type"
                    : step.id === "portal_enabled" && !step.complete
                      ? "Portal is turned off"
                      : step.complete
                        ? "Done"
                        : step.description || "Needed"
                }
              />
            </View>
          ))}
        </Card>
      ) : null}
      <PrimaryButton label="Check again" onPress={onRefresh} />
      <Button variant="plain" label="Sign out" onPress={onSignOut} />
    </Screen>
  );
}

export function AccessDeniedScreen({
  detail,
  onSignOut,
}: {
  detail: string;
  onSignOut: () => void;
}) {
  return (
    <Screen scroll testID="customer-denied" title="This account can't book">
      <Banner tone="danger" text={detail} />
      <Txt v="callout" tone="muted">
        Sign out and use your customer account, or contact support from porterchain.com.
      </Txt>
      <Button label="Sign out" variant="ghost" onPress={onSignOut} />
    </Screen>
  );
}
