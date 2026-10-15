import { Alert } from "react-native";
import { requestAccountDeletion } from "../accountDeletion";
import { requestPrivacy } from "../api";
import { haptic } from "../haptics";
import { toast } from "./toast";

/** Confirm, then file the account deletion request (Settings and Profile share this). */
export function confirmDeleteAccount(setBusy?: (b: boolean) => void): void {
  Alert.alert(
    "Delete your account?",
    "This deletes your PorterChain driver account and personal data. You won't be able to sign in or get jobs. Delivery records the law requires are kept.",
    [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete account",
        style: "destructive",
        onPress: () => {
          setBusy?.(true);
          void requestAccountDeletion(requestPrivacy)
            .then((m) => {
              haptic.success();
              Alert.alert(m.title, m.body);
            })
            .catch(() =>
              toast.show(
                "danger",
                "Couldn't send",
                "Try again with signal, or email privacy@porterchain.com."
              )
            )
            .finally(() => setBusy?.(false));
        },
      },
    ]
  );
}
