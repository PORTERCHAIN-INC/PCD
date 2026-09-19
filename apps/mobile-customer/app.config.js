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
      appKind: "customer",
    },
  };
};
