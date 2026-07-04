import { Platform } from "react-native";
import * as Application from "expo-application";
import type { DeviceIntegrityResult } from "../types";

type IntegrityAdapter = () => Promise<Partial<DeviceIntegrityResult>>;

let customAdapter: IntegrityAdapter | null = null;

export function registerIntegrityAdapter(adapter: IntegrityAdapter) {
  customAdapter = adapter;
}

export async function checkDeviceIntegrity(): Promise<DeviceIntegrityResult> {
  const reasons: string[] = [];
  let jailbroken = false;
  let rooted = false;

  if (customAdapter) {
    const custom = await customAdapter();
    return {
      compromised: custom.compromised ?? false,
      jailbroken: custom.jailbroken ?? false,
      rooted: custom.rooted ?? false,
      reasons: custom.reasons ?? [],
      checkedAt: new Date().toISOString(),
    };
  }

  if (__DEV__) {
    return { compromised: false, jailbroken: false, rooted: false, reasons: [], checkedAt: new Date().toISOString() };
  }

  if (Platform.OS === "ios") {
    const installer = Application.applicationId ?? "";
    if (installer && !installer.startsWith("com.porterchain")) {
      reasons.push("unexpected_bundle_id");
    }
  }

  if (Platform.OS === "android") {
    const referrer = (Application as { getInstallReferrerAsync?: () => Promise<string> }).getInstallReferrerAsync;
    if (referrer) {
      const value = await referrer().catch(() => null);
      if (value === "unknown") reasons.push("unknown_install_source");
    }
  }

  return {
    compromised: reasons.length > 0,
    jailbroken,
    rooted,
    reasons,
    checkedAt: new Date().toISOString(),
  };
}
