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
  refreshToken: string | null;
  driverId: string | null;
  email: string | null;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  setSession: (session: { token: string; refreshToken: string; driverId: string; email: string }) => Promise<void>;
  clearSession: () => Promise<void>;
};

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: null,
  refreshToken: null,
  driverId: null,
  email: null,
  hydrated: false,
  hydrate: async () => {
    const [accessToken, refreshToken, driverId] = await Promise.all([
      getSecureItem(secureKeys.accessToken),
      getSecureItem(secureKeys.refreshToken),
      getSecureItem(secureKeys.driverId),
    ]);
    set({ accessToken, refreshToken, driverId, hydrated: true });
  },
  setSession: async ({ token, refreshToken, driverId, email }) => {
    await Promise.all([
      setSecureItem(secureKeys.accessToken, token),
      setSecureItem(secureKeys.refreshToken, refreshToken),
      setSecureItem(secureKeys.driverId, driverId),
    ]);
    set({ accessToken: token, refreshToken, driverId, email });
  },
  clearSession: async () => {
    await clearSecureSession();
    set({ accessToken: null, refreshToken: null, driverId: null, email: null });
  },
}));

export function useIsSignedIn() {
  const token = useAuthStore((s) => s.accessToken);
  const hydrated = useAuthStore((s) => s.hydrated);
  return { signedIn: Boolean(token), hydrated };
}
