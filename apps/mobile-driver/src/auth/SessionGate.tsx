import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { ActivityIndicator } from "react-native";
import { allowDevAuth, appEnv } from "../config";
import { setSessionSnapshot } from "../session";
import { Body, Muted, Screen } from "../ui/kit";
import { color } from "../ui/theme";
import {
  browserSignInFresh,
  endpoints,
  type IdpHint,
  type KeycloakConfig,
  keycloakConfig,
  needsRefresh,
  refreshTokens,
  revoke,
  type Tokens,
} from "./keycloak";
import {
  endBrowserSession,
  loadTokens,
  nativeSignIn,
  saveTokens,
  signInWithKeycloak,
} from "./keycloakNative";

export type SignInOptions = { idpHint?: IdpHint; register?: boolean; native?: boolean };

type SessionView = {
  ready: boolean;
  signedIn: boolean;
  bootError: string | null;
  /** Keycloak sign-in (null in dev builds without Keycloak). */
  signIn: ((opts?: SignInOptions) => Promise<void>) | null;
  /**
   * Clears Keycloak tokens and the system-browser sign-in cookie.
   * Does not wipe jobs, proof photos, or the offline queue. Null when there is no Keycloak.
   */
  resetSignIn: (() => Promise<void>) | null;
  accountUrl: string | null;
};

const SessionContext = createContext<SessionView>({
  ready: true,
  signedIn: allowDevAuth(),
  bootError: null,
  signIn: null,
  resetSignIn: null,
  accountUrl: null,
});

export function useSessionView(): SessionView {
  return useContext(SessionContext);
}

function Boot({ detail }: { detail?: string | null }) {
  return (
    <Screen testID="auth-boot" scroll={false}>
      <ActivityIndicator size="large" color={color.ink} />
      <Body>Starting Porterchain…</Body>
      {detail ? <Muted>{detail}</Muted> : null}
    </Screen>
  );
}

const keycloak = keycloakConfig(undefined, allowDevAuth());

/** Keycloak session (L36): tokens in SecureStore, refreshed before expiry. */
function KeycloakBridge({ kc, children }: { kc: KeycloakConfig; children: ReactNode }) {
  const [tokens, setTokens] = useState<Tokens | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);
  const tokensRef = useRef<Tokens | null>(null);
  const refreshing = useRef<Promise<Tokens | null> | null>(null);
  /** Next browser sign-in asks for credentials again (prompt=login) after a failure or reset. */
  const forceFresh = useRef(false);

  const store = useCallback(async (next: Tokens | null) => {
    tokensRef.current = next;
    setTokens(next);
    await saveTokens(next);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void loadTokens().then((t) => {
      if (cancelled) return;
      tokensRef.current = t;
      setTokens(t);
      setLoaded(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const getToken = useCallback(
    async (opts?: { fresh?: boolean }): Promise<string | null> => {
      const current = tokensRef.current;
      if (!current) return null;
      if (!opts?.fresh && !needsRefresh(current)) return current.accessToken;
      refreshing.current ??= refreshTokens(fetch as never, kc, current)
        .then(async (t) => {
          await store(t);
          return t;
        })
        .catch(async (err: unknown) => {
          if (err instanceof Error && err.message === "invalid_grant") await store(null);
          else setBootError("Couldn’t refresh your session. Check your connection.");
          return null;
        })
        .finally(() => {
          refreshing.current = null;
        });
      const t = await refreshing.current;
      return t?.accessToken ?? null;
    },
    [kc, store]
  );

  const signIn = useCallback(
    async (opts: SignInOptions = {}) => {
      setBootError(null);
      try {
        const nativeAttempted = Boolean(opts.native && opts.idpHint);
        const native = nativeAttempted ? await nativeSignIn(kc, opts.idpHint as IdpHint) : null;
        if (native) {
          forceFresh.current = false;
          await store(native);
          return;
        }
        const fresh = browserSignInFresh(nativeAttempted, forceFresh.current);
        await store(await signInWithKeycloak(kc, { ...opts, fresh }));
        forceFresh.current = false;
      } catch (err) {
        const code = err instanceof Error ? err.message : "";
        if (code !== "cancel" && code !== "dismiss") forceFresh.current = true;
        throw err;
      }
    },
    [kc, store]
  );

  const signOut = useCallback(async () => {
    const current = tokensRef.current;
    await store(null);
    if (current) await revoke(fetch as never, kc, current);
  }, [kc, store]);

  const resetSignIn = useCallback(async () => {
    // Auth material only. Do not call clearSession: that wipes the offline queue and proof photos.
    setBootError(null);
    const current = tokensRef.current;
    forceFresh.current = true;
    if (current) await revoke(fetch as never, kc, current).catch(() => undefined);
    await store(null);
    await endBrowserSession(kc, current?.idToken ?? null);
  }, [kc, store]);

  const view = useMemo(
    () => ({
      ready: loaded,
      signedIn: Boolean(tokens),
      bootError,
      signIn,
      resetSignIn,
      accountUrl: endpoints(kc).account,
    }),
    [bootError, kc, loaded, resetSignIn, signIn, tokens]
  );

  useLayoutEffect(() => {
    setSessionSnapshot({
      ready: loaded,
      signedIn: Boolean(tokens),
      getToken,
      signOut,
    });
  }, [getToken, loaded, signOut, tokens]);

  if (!loaded) return <Boot detail={`env=${appEnv}`} />;
  return <SessionContext.Provider value={view}>{children}</SessionContext.Provider>;
}

function DevBridge({ children }: { children: ReactNode }) {
  const view = useMemo(
    () => ({
      ready: true,
      signedIn: allowDevAuth(),
      bootError: null as string | null,
      signIn: null,
      resetSignIn: null,
      accountUrl: null,
    }),
    []
  );

  useLayoutEffect(() => {
    setSessionSnapshot({
      ready: true,
      signedIn: allowDevAuth(),
      getToken: async () => (allowDevAuth() ? "dev" : null),
      signOut: async () => {
        setSessionSnapshot({
          ready: true,
          signedIn: false,
          getToken: async () => null,
          signOut: async () => undefined,
        });
      },
    });
  }, []);

  return <SessionContext.Provider value={view}>{children}</SessionContext.Provider>;
}

export function SessionGate({ children }: { children: ReactNode }) {
  if (!keycloak) return <DevBridge>{children}</DevBridge>;
  return <KeycloakBridge kc={keycloak}>{children}</KeycloakBridge>;
}
