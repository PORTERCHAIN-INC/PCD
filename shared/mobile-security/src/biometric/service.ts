import * as LocalAuthentication from "expo-local-authentication";

export async function canUseBiometrics() {
  const compatible = await LocalAuthentication.hasHardwareAsync();
  const enrolled = await LocalAuthentication.isEnrolledAsync();
  return compatible && enrolled;
}

export async function authenticateWithBiometrics(prompt = "Unlock Porterchain") {
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: prompt,
    cancelLabel: "Cancel",
    disableDeviceFallback: false,
    fallbackLabel: "Use device passcode",
  });
  return result.success;
}
