import messaging, { type FirebaseMessagingTypes } from "@react-native-firebase/messaging";
import { requestNotificationPermission } from "./permissions";

export async function getFcmToken(): Promise<string | null> {
  try {
    const granted = await requestNotificationPermission();
    if (!granted) return null;

    await messaging().registerDeviceForRemoteMessages();
    await messaging().requestPermission();

    return await messaging().getToken();
  } catch {
    return null;
  }
}

export function onForegroundMessage(handler: (message: unknown) => void) {
  return messaging().onMessage(handler);
}

export async function getInitialNotification(): Promise<FirebaseMessagingTypes.RemoteMessage | null> {
  return messaging().getInitialNotification();
}

export function onNotificationOpenedApp(
  handler: (message: FirebaseMessagingTypes.RemoteMessage) => void
) {
  return messaging().onNotificationOpenedApp(handler);
}
