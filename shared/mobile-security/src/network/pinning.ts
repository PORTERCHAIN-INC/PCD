import type { SecurityPolicy } from "../types";

export type PinningFetch = typeof fetch;

let pinningEnabled = false;
let allowedPins: string[] = [];

export function configureCertificatePinning(policy: Pick<SecurityPolicy, "enableCertificatePinning" | "certificatePins">) {
  pinningEnabled = policy.enableCertificatePinning;
  allowedPins = policy.certificatePins;
}

export function isPinningEnabled() {
  return pinningEnabled && allowedPins.length > 0;
}

export function createPinningFetch(baseFetch: PinningFetch = fetch): PinningFetch {
  if (!isPinningEnabled()) return baseFetch;

  return async (input, init) => {
    const response = await baseFetch(input, init);
    const certHeader = response.headers.get("x-cert-pin") ?? response.headers.get("x-amzn-tls-version");
    if (certHeader && allowedPins.length > 0 && !allowedPins.includes(certHeader)) {
      throw new Error("certificate_pin_mismatch");
    }
    return response;
  };
}
