/**
 * Dynamic Expo config. Expo passes the static app.json "expo" block in as `config`,
 * so app.json stays the single source of truth (expo-doctor: config uses app.json).
 *
 * Cleartext HTTP (local API over http://) is allowed only outside production, via the
 * supported expo-build-properties option rather than the non-schema
 * `android.usesCleartextTraffic` field.
 */
function withCleartext(plugins, allow) {
  let found = false;
  const next = (plugins ?? []).map((p) => {
    const name = Array.isArray(p) ? p[0] : p;
    if (name !== "expo-build-properties") return p;
    found = true;
    const opts = Array.isArray(p) ? { ...(p[1] ?? {}) } : {};
    return [
      "expo-build-properties",
      { ...opts, android: { ...(opts.android ?? {}), usesCleartextTraffic: allow } },
    ];
  });
  if (!found) next.push(["expo-build-properties", { android: { usesCleartextTraffic: allow } }]);
  return next;
}

module.exports = ({ config }) => {
  const appEnv = process.env.EXPO_PUBLIC_APP_ENV ?? "development";
  return {
    ...config,
    plugins: withCleartext(config.plugins, appEnv !== "production"),
    android: {
      ...(config.android ?? {}),
      // In-app live map (react-native-maps, Google on Android; iOS uses Apple Maps, no key).
      // GOOGLE_MAPS_ANDROID_API_KEY = "PorterChain Android Maps" key (Maps SDK for Android
      // only, restricted to com.porterchain.customer + SHA-1s). Build-time only: not
      // EXPO_PUBLIC_, so it is not inlined into the JS bundle. Doppler pcd/prd + EAS env.
      config: {
        ...(config.android?.config ?? {}),
        googleMaps: {
          apiKey: (process.env.GOOGLE_MAPS_ANDROID_API_KEY || "").trim(),
        },
      },
    },
    extra: {
      ...(config.extra ?? {}),
      appEnv,
      appKind: "customer",
    },
  };
};
