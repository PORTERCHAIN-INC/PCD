import { useEffect, useRef } from "react";
import { AppState, type AppStateStatus } from "react-native";

export function useForegroundAwareInterval(callback: () => void, delayMs: number | null, pauseInBackground = true) {
  const saved = useRef(callback);

  useEffect(() => {
    saved.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delayMs === null) return;

    let timer: ReturnType<typeof setInterval> | null = null;

    const start = () => {
      if (timer) return;
      timer = setInterval(() => saved.current(), delayMs);
    };

    const stop = () => {
      if (!timer) return;
      clearInterval(timer);
      timer = null;
    };

    const onChange = (state: AppStateStatus) => {
      if (!pauseInBackground) {
        start();
        return;
      }
      if (state === "active") start();
      else stop();
    };

    if (!pauseInBackground || AppState.currentState === "active") start();
    const sub = AppState.addEventListener("change", onChange);

    return () => {
      stop();
      sub.remove();
    };
  }, [delayMs, pauseInBackground]);
}
