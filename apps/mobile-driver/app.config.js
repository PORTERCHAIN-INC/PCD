const appJson = require("./app.json");

module.exports = () => {
  const appEnv = process.env.EXPO_PUBLIC_APP_ENV ?? "development";
  const expo = appJson.expo;
  return {
    ...expo,
    android: {
      ...expo.android,
      usesCleartextTraffic: appEnv !== "production",
    },
    extra: {
      ...(expo.extra ?? {}),
      appEnv,
      allowDevAuth:
        process.env.EXPO_PUBLIC_ALLOW_DEV_AUTH === "true" ||
        (process.env.EXPO_PUBLIC_ALLOW_DEV_AUTH !== "false" && appEnv === "development"),
    },
  };
};
