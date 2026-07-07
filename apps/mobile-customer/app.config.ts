import type { ExpoConfig } from "expo/config";

const googleMapsApiKey = (process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY ?? "").trim();

const config: ExpoConfig = {
  name: "Porterchain Customer",
  slug: "porterchain-customer",
  owner: "porterchains-organization",
  scheme: "porterchain-customer",
  version: "1.0.0",
  orientation: "portrait",
  userInterfaceStyle: "automatic",
  splash: {
    resizeMode: "contain",
    backgroundColor: "#0a1628",
  },
  extra: {
    eas: {
      projectId: process.env.EAS_PROJECT_ID ?? "",
    },
  },
  ios: {
    supportsTablet: true,
    bundleIdentifier: "com.porterchain.customer",
    googleServicesFile:
      process.env.GOOGLE_SERVICES_INFO_PLIST ?? "./credentials/GoogleService-Info.plist",
    config: { googleMapsApiKey },
    infoPlist: {
      UIBackgroundModes: ["remote-notification"],
    },
  },
  android: {
    package: "com.porterchain.customer",
    googleServicesFile: process.env.GOOGLE_SERVICES_JSON ?? "./credentials/google-services.json",
    config: { googleMaps: { apiKey: googleMapsApiKey } },
  },
  plugins: [
    "@react-native-firebase/app",
    "@react-native-firebase/messaging",
    [
      "expo-build-properties",
      {
        ios: { useFrameworks: "static" },
      },
    ],
    ["expo-notifications", { color: "#2563eb" }],
  ],
};

export default config;
