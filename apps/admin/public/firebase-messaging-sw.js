importScripts("https://www.gstatic.com/firebasejs/11.0.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/11.0.2/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyCYbNVZaYseoFi3ptDKVQkYBC-gKyDr35M",
  authDomain: "porterchain-55313.firebaseapp.com",
  projectId: "porterchain-55313",
  storageBucket: "porterchain-55313.firebasestorage.app",
  messagingSenderId: "430248198034",
  appId: "1:430248198034:ios:82293eed2853f8ec2f0b4b",
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const data = payload.data || {};
  const notification = payload.notification || {};
  const priority = String(data.priority || "normal").toLowerCase();
  const urgent = priority === "critical" || priority === "high";
  const title = notification.title || data.title || "PorterChain";
  const body = notification.body || data.body || "";
  const tag = data.order_id || data.exception_id || data.deep_link || "porterchain-ops";
  const options = {
    body,
    data,
    tag: String(tag),
    renotify: urgent,
    requireInteraction: urgent,
    silent: false,
  };
  return self.registration.showNotification(title, options);
});
