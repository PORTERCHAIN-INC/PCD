import { humanError } from "../errorCopy";
import { openRefusedReview } from "../refusedReview";
import { Banner } from "./kit";

/** Connection / sync / error state, worded for a driver. Shown at the top of Today and Job. */
export function SyncBanners({
  offline,
  pending,
  rejected,
  error,
  onSync,
  onDismissError,
}: {
  offline: boolean;
  pending: number;
  rejected: number;
  error: string | null;
  onSync: () => void;
  onDismissError: () => void;
}) {
  return (
    <>
      {offline ? (
        <Banner
          tone="warn"
          testID="offline-banner"
          title="No connection"
          body="Keep working. Everything is saved on this phone and sends when signal is back."
        />
      ) : null}
      {pending > 0 ? (
        <Banner
          tone="info"
          testID="banner-syncing"
          title={`Syncing ${pending} saved action${pending === 1 ? "" : "s"}`}
          action={offline ? undefined : { label: "Sync now", onPress: onSync }}
        />
      ) : null}
      {rejected > 0 ? (
        <Banner
          tone="danger"
          testID="banner-rejected"
          title={`${rejected} saved action${rejected === 1 ? " was" : "s were"} refused`}
          body="The server did not accept it. Review to retry or discard, or call dispatch."
          action={{ label: "Review", onPress: openRefusedReview }}
        />
      ) : null}
      {error ? (
        <Banner
          tone="danger"
          testID="banner-error"
          title={humanError(error)}
          action={{ label: "Dismiss", onPress: onDismissError }}
        />
      ) : null}
    </>
  );
}
