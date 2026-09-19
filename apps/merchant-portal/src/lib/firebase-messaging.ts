"use client";

import { initializeApp, getApps, getApp, type FirebaseApp } from "firebase/app";
import { getMessaging, getToken, isSupported, type Messaging } from "firebase/messaging";
import { firebaseWebConfig } from "@/lib/firebase-public";

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

export async function getWebFcmToken(): Promise<string | null> {
  const cfg = firebaseWebConfig();
  if (!cfg || typeof window === "undefined") return null;
  if (!(await isSupported())) return null;
  const firebaseApp = getFirebaseApp();
  if (!firebaseApp) return null;
  if (!messaging) messaging = getMessaging(firebaseApp);
  const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js");
  await navigator.serviceWorker.ready;
  return getToken(messaging, { vapidKey: cfg.vapidKey, serviceWorkerRegistration: registration });
}
