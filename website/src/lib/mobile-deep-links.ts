/**
 * Universal Links / App Links SSOT — porterchain.com → native apps (Wave 10 w10-2).
 */

export const APP_LINK_HOSTS = ["porterchain.com", "www.porterchain.com"] as const;

export const MOBILE_APP_IDS = {
  customer: {
    iosBundleId: "com.porterchain.customer",
    androidPackage: "com.porterchain.customer",
    urlScheme: "porterchain-customer",
  },
  driver: {
    iosBundleId: "com.porterchain.PCD",
    androidPackage: "com.porterchain.PCD",
    urlScheme: "porterchain-driver",
  },
} as const;

/** AASA path patterns per app (Apple applinks). */
export const CUSTOMER_UNIVERSAL_PATHS = [
  "/track",
  "/track/*",
  "/*/track",
  "/*/track/*",
  "/login",
  "/login/*",
] as const;

export const DRIVER_UNIVERSAL_PATHS = ["/auth/driver-invite", "/auth/driver-invite/*"] as const;

export function buildAppleAppSiteAssociationDocument(teamId: string) {
  return {
    applinks: {
      apps: [] as string[],
      details: [
        {
          appID: `${teamId}.${MOBILE_APP_IDS.customer.iosBundleId}`,
          paths: [...CUSTOMER_UNIVERSAL_PATHS],
        },
        {
          appID: `${teamId}.${MOBILE_APP_IDS.driver.iosBundleId}`,
          paths: [...DRIVER_UNIVERSAL_PATHS],
        },
      ],
    },
  };
}

export function buildAndroidAssetLinks(fingerprints: { customer: string[]; driver: string[] }) {
  return [
    {
      relation: ["delegate_permission/common.handle_all_urls"],
      target: {
        namespace: "android_app",
        package_name: MOBILE_APP_IDS.customer.androidPackage,
        sha256_cert_fingerprints: fingerprints.customer,
      },
    },
    {
      relation: ["delegate_permission/common.handle_all_urls"],
      target: {
        namespace: "android_app",
        package_name: MOBILE_APP_IDS.driver.androidPackage,
        sha256_cert_fingerprints: fingerprints.driver,
      },
    },
  ];
}

export function parseFingerprintList(value: string | undefined, fallback: string): string[] {
  const raw = (value ?? fallback).trim();
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}
