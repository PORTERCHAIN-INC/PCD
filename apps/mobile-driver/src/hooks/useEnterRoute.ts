import { useCallback, type Dispatch, type SetStateAction } from "react";
import { fetchOnboarding } from "../api";
import { allowDevAuth } from "../config";
import { canEnterRoute } from "../gate";
import { runHandshake } from "../handshake";
import { getSessionSnapshot } from "../session";
import type { FieldTab, Handshake, LocationState, Screen } from "../types";

type Options = {
  location: LocationState;
  setBusy: (busy: boolean) => void;
  setHandshake: Dispatch<SetStateAction<Handshake>>;
  setTab: Dispatch<SetStateAction<FieldTab>>;
  setScreen: Dispatch<SetStateAction<Screen>>;
};

export function useEnterRoute({ location, setBusy, setHandshake, setTab, setScreen }: Options) {
  return useCallback(() => {
    const session = getSessionSnapshot();
    void (async () => {
      setBusy(true);
      try {
        const next = await runHandshake(location);
        setHandshake(next);
        const gate = canEnterRoute(next, session.signedIn, allowDevAuth());
        if (!gate.ok) {
          setHandshake({ ...next, error: gate.reason });
          return;
        }
        try {
          const onboarding = await fetchOnboarding();
          if (!onboarding.ready) {
            setScreen("onboarding");
            return;
          }
        } catch {
          if (!allowDevAuth()) {
            setHandshake({
              ...next,
              error: "Could not load onboarding status",
            });
            return;
          }
        }
        setTab("work");
        setScreen("route");
      } finally {
        setBusy(false);
      }
    })();
  }, [location, setBusy, setHandshake, setScreen, setTab]);
}
