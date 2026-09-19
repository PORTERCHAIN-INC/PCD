import { useEffect } from "react";
import * as Linking from "expo-linking";
import { parseDriverLink } from "../linking";
import { attachPushListeners } from "../push";

type Options = {
  onInvite: (token: string) => void;
  onJob: (orderId: string) => void;
  onPushWithoutJob: () => void;
};

/** Universal / App Links + notification cold-start / tap. */
export function useDriverDeepLinks({ onInvite, onJob, onPushWithoutJob }: Options): void {
  useEffect(() => {
    function apply(url: string | null) {
      const link = parseDriverLink(url);
      if (link.kind === "invite") {
        onInvite(link.token);
        return;
      }
      if (link.kind === "job") {
        onJob(link.orderId);
      }
    }
    void Linking.getInitialURL().then(apply);
    const sub = Linking.addEventListener("url", (event: { url: string }) => apply(event.url));
    return () => sub.remove();
  }, [onInvite, onJob]);

  useEffect(() => {
    return attachPushListeners((payload) => {
      // Lock-screen Accept/Decline: open JobDetail only when the API call failed.
      if (payload.action === "accept" || payload.action === "decline") {
        if (payload.error && payload.orderId) {
          onJob(payload.orderId);
        }
        return;
      }
      if (payload.orderId) {
        onJob(payload.orderId);
        return;
      }
      onPushWithoutJob();
    });
  }, [onJob, onPushWithoutJob]);
}
