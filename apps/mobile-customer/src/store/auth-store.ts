import { create } from "zustand";
import {
  clearSecureSession,
  deleteSecureItem,
  getSecureItem,
  secureKeys,
  setSecureItem,
} from "@porterchain/mobile-storage";

type AuthStore = {
  accessToken: string | null;
  clerkUserId: string | null;
  email: string | null;
  hydrated: boolean;
  biometricEnabled: boolean;
  hydrate: () => Promise<void>;
  setSession: (session: { token: string; clerkUserId: string; email: string }) => Promise<void>;
  clearSession: () => Promise<void>;
  setBiometricEnabled: (enabled: boolean) => Promise<void>;
};

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: null,
  clerkUserId: null,
  email: null,
  hydrated: false,
  biometricEnabled: false,
  hydrate: async () => {
    const [accessToken, clerkUserId, biometric] = await Promise.all([
      getSecureItem(secureKeys.accessToken),
      getSecureItem(secureKeys.customerId),
      getSecureItem(`${secureKeys.accessToken}.biometric`),
    ]);
    set({
      accessToken,
      clerkUserId,
      biometricEnabled: biometric === "1",
      hydrated: true,
    });
  },
  setSession: async ({ token, clerkUserId, email }) => {
    await Promise.all([
      setSecureItem(secureKeys.accessToken, token),
      setSecureItem(secureKeys.customerId, clerkUserId),
    ]);
    set({ accessToken: token, clerkUserId, email });
  },
  clearSession: async () => {
    await clearSecureSession();
    set({ accessToken: null, clerkUserId: null, email: null });
  },
  setBiometricEnabled: async (enabled) => {
    if (enabled) {
      await setSecureItem(`${secureKeys.accessToken}.biometric`, "1");
    } else {
      await deleteSecureItem(`${secureKeys.accessToken}.biometric`);
    }
    set({ biometricEnabled: enabled });
  },
}));

export function useIsSignedIn() {
  const token = useAuthStore((s) => s.accessToken);
  const hydrated = useAuthStore((s) => s.hydrated);
  return { signedIn: Boolean(token), hydrated };
}
