import { Linking } from "react-native";
import { Banner, Body, Button, Screen, Title } from "./kit";

/** Full-screen "you can't continue yet" message: app update needed, or setup not finished. */
export function Notice({
  title,
  body,
  link,
  retry,
  error,
  testID,
}: {
  title: string;
  body: string;
  link?: { label: string; url: string };
  retry?: { label: string; onPress: () => void; busy?: boolean };
  error?: string | null;
  testID?: string;
}) {
  return (
    <Screen
      testID={testID}
      footer={
        <>
          {link ? (
            <Button
              tone="primary"
              label={link.label}
              hint="Opens in your browser"
              onPress={() => void Linking.openURL(link.url)}
            />
          ) : null}
          {retry ? (
            <Button
              tone={link ? "secondary" : "primary"}
              label={retry.label}
              busy={retry.busy}
              onPress={retry.onPress}
            />
          ) : null}
        </>
      }
    >
      <Title>{title}</Title>
      <Body>{body}</Body>
      {error ? <Banner tone="danger" title={error} /> : null}
    </Screen>
  );
}
