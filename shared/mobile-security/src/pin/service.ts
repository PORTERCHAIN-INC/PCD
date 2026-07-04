import { createHash } from "./pin-hash";
import {
  deleteSecureValue,
  getSecureValue,
  securityKeys,
  setSecureValue,
} from "../storage/secure-session";

export async function setPin(pin: string) {
  const hash = createHash(pin);
  await setSecureValue(securityKeys.pinHash, hash);
}

export async function clearPin() {
  await deleteSecureValue(securityKeys.pinHash);
}

export async function hasPin() {
  const hash = await getSecureValue(securityKeys.pinHash);
  return Boolean(hash);
}

export async function verifyPin(pin: string) {
  const stored = await getSecureValue(securityKeys.pinHash);
  if (!stored) return false;
  return stored === createHash(pin);
}
