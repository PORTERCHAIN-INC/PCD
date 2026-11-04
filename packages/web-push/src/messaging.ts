"use client";

import { initializeApp, getApps, getApp, type FirebaseApp } from "firebase/app";
import {
  getMessaging,
  getToken,
  isSupported,
  onMessage,
  type Messaging,
  type Unsubscribe,
} from "firebase/messaging";
import { firebaseWebConfig } from "./config";

let app: FirebaseApp | null = null;
let messaging: Messaging | null = null;

function getFirebaseApp(): FirebaseApp | null {
  const cfg = firebaseWebConfig();
  if (!cfg) return null;
  if (app) return app;
  const { vapidKey: _v, ...firebaseConfig } = cfg;
  app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  return app;
}

async function getMessagingIfSupported(): Promise<Messaging | null> {
  const cfg = firebaseWebConfig();
  if (!cfg || typeof window === "undefined") return null;
  if (!(await isSupported())) return null;
  const firebaseApp = getFirebaseApp();
  if (!firebaseApp) return null;
  if (!messaging) messaging = getMessaging(firebaseApp);
  return messaging;
}

/** FCM token for this browser; registers each portal's /firebase-messaging-sw.js. */
export async function getWebFcmToken(): Promise<string | null> {
  const cfg = firebaseWebConfig();
  if (!cfg) return null;
  const msg = await getMessagingIfSupported();
  if (!msg) return null;
  const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js");
  await navigator.serviceWorker.ready;
  return getToken(msg, { vapidKey: cfg.vapidKey, serviceWorkerRegistration: registration });
}

export type ForegroundPushPayload = {
  title: string;
  body: string;
  priority: string;
  deepLink?: string;
  tag?: string;
};

/** In-tab alerts while a portal is focused (the service worker covers background). */
export async function attachForegroundMessaging(
  onPush: (payload: ForegroundPushPayload) => void,
  defaultTag = "porterchain-ops"
): Promise<Unsubscribe | null> {
  const msg = await getMessagingIfSupported();
  if (!msg) return null;
  return onMessage(msg, (payload) => {
    const data = payload.data || {};
    const notification = payload.notification || {};
    onPush({
      title: String(notification.title || data.title || "PorterChain"),
      body: String(notification.body || data.body || ""),
      priority: String(data.priority || "normal").toLowerCase(),
      deepLink: data.deep_link ? String(data.deep_link) : undefined,
      tag: String(data.order_id || data.exception_id || data.deep_link || defaultTag),
    });
  });
}
