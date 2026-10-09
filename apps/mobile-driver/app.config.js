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
    extra: {
      ...(config.extra ?? {}),
      appEnv,
      allowDevAuth:
        process.env.EXPO_PUBLIC_ALLOW_DEV_AUTH === "true" ||
        (process.env.EXPO_PUBLIC_ALLOW_DEV_AUTH !== "false" && appEnv === "development"),
    },
  };
};
