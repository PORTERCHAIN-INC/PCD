import { useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import * as Linking from "expo-linking";
import { probeApi } from "./src/api";
import { screenFromUrl, type Screen } from "./src/linking";
import { SignInScreen } from "./src/screens/SignInScreen";
import { TrackScreen } from "./src/screens/TrackScreen";

export default function App() {
  const [screen, setScreen] = useState<Screen>("sign-in");
  const [trackingFromLink, setTrackingFromLink] = useState("");
  const [apiUp, setApiUp] = useState<boolean | null>(null);

  useEffect(() => {
    function apply(url: string | null) {
      const next = screenFromUrl(url);
      if (!next) return;
      setScreen(next.screen);
      if (next.tracking) setTrackingFromLink(next.tracking);
    }

    void Linking.getInitialURL().then(apply);
    const sub = Linking.addEventListener("url", (event: { url: string }) => apply(event.url));
    return () => sub.remove();
  }, []);

  useEffect(() => {
    void probeApi().then(setApiUp);
  }, []);

  return (
    <>
      {screen === "sign-in" ? (
        <SignInScreen apiUp={apiUp} onContinue={() => setScreen("track")} />
      ) : (
        <TrackScreen initialTracking={trackingFromLink} />
      )}
      <StatusBar style="dark" />
    </>
  );
}
