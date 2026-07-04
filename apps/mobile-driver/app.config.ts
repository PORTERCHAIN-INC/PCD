import type { ExpoConfig } from "expo/config";

const googleMapsApiKey = (process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY ?? "").trim();

const config: ExpoConfig = {
  name: "Porterchain Driver",
  slug: "porterchain-driver",
  owner: "porterchains-organization",
  scheme: "porterchain-driver",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "automatic",
  splash: {
    image: "./assets/splash.png",
    resizeMode: "contain",
    backgroundColor: "#124835",
  },
  assetBundlePatterns: ["**/*"],
  extra: {
    eas: {
      projectId: "4beda39e-2c2c-4cda-b994-262e646438ca",
    },
  },
  ios: {
    supportsTablet: true,
    bundleIdentifier: "com.porterchain.PCD",
    buildNumber: "1",
    googleServicesFile: process.env.GOOGLE_SERVICES_INFO_PLIST ?? "./credentials/GoogleService-Info.plist",
    config: { googleMapsApiKey },
    infoPlist: {
      ITSAppUsesNonExemptEncryption: false,
      NSLocationWhenInUseUsageDescription: "Show your location while delivering",
      NSLocationAlwaysAndWhenInUseUsageDescription:
        "Share your location while online for dispatch and customer tracking.",
      NSCameraUsageDescription: "Capture proof-of-delivery photos.",
      NSPhotoLibraryUsageDescription: "Upload delivery photos.",
      UIBackgroundModes: ["location", "remote-notification"],
    },
  },
  android: {
    adaptiveIcon: {
      foregroundImage: "./assets/adaptive-icon.png",
      backgroundColor: "#124835",
    },
    package: "com.porterchain.PCD",
    versionCode: 1,
    googleServicesFile: process.env.GOOGLE_SERVICES_JSON ?? "./credentials/google-services.json",
    permissions: ["ACCESS_COARSE_LOCATION", "ACCESS_FINE_LOCATION", "CAMERA"],
    config: { googleMaps: { apiKey: googleMapsApiKey } },
  },
  plugins: [
    "@react-native-firebase/app",
    "@react-native-firebase/messaging",
    [
      "expo-build-properties",
      {
        ios: {
          useFrameworks: "static",
        },
      },
    ],
    [
      "expo-location",
      {
        locationWhenInUsePermission: "Show your location while delivering",
        locationAlwaysAndWhenInUsePermission:
          "Share your location while online for dispatch and customer tracking.",
        isIosBackgroundLocationEnabled: true,
        isAndroidBackgroundLocationEnabled: true,
        isAndroidForegroundServiceEnabled: true,
      },
    ],
    [
      "expo-image-picker",
      {
        photosPermission: "Upload proof-of-delivery photos.",
        cameraPermission: "Capture proof-of-delivery photos.",
      },
    ],
    [
      "expo-camera",
      {
        cameraPermission: "Capture proof-of-delivery photos.",
      },
    ],
    [
      "expo-notifications",
      {
        icon: "./assets/icon.png",
        color: "#124835",
      },
    ],
  ],
};

export default config;
