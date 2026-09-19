/** Public Firebase web config — FCM only (not Auth). */

export function firebaseWebConfig(): {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket: string;
  messagingSenderId: string;
  appId: string;
  vapidKey: string;
} | null {
  const apiKey = (process.env.NEXT_PUBLIC_FIREBASE_API_KEY ?? "").trim();
  const projectId = (process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ?? "").trim();
  const messagingSenderId = (process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID ?? "").trim();
  const appId = (process.env.NEXT_PUBLIC_FIREBASE_APP_ID ?? "").trim();
  const vapidKey = (process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY ?? "").trim();
  if (!apiKey || !projectId || !messagingSenderId || !appId || !vapidKey) return null;
  return {
    apiKey,
    authDomain:
      process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN?.trim() || `${projectId}.firebaseapp.com`,
    projectId,
    storageBucket:
      process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET?.trim() || `${projectId}.firebasestorage.app`,
    messagingSenderId,
    appId,
    vapidKey,
  };
}

export function isFcmRegistrationToken(token: string): boolean {
  return token.includes(":APA91") && !token.startsWith("web-");
}
