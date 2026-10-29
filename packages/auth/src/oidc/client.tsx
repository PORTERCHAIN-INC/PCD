"use client";

/**
 * Browser side of Keycloak OIDC (L36). Tokens never touch localStorage: the access token is
 * fetched from the app's own /auth/session route (httpOnly cookie) and kept in memory.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { SessionUser } from "./core";

type SessionPayload =
  | { signedIn: false }
  | { signedIn: true; user: SessionUser; accessToken: string; expiresAt: number };

export type AuthState = {
  isLoaded: boolean;
  isSignedIn: boolean;
  userId: string | null;
  user: SessionUser | null;
  getToken: (opts?: { fresh?: boolean; skipCache?: boolean }) => Promise<string | null>;
  signIn: (opts?: { returnTo?: string; idpHint?: string; loginHint?: string }) => void;
  signUp: (opts?: { returnTo?: string; idpHint?: string }) => void;
  signOut: (opts?: { returnTo?: string }) => void;
  openAccount: () => void;
  reload: () => Promise<void>;
};

const Ctx = createContext<AuthState | null>(null);

function go(path: string, q: Record<string, string | undefined>) {
  const u = new URL(path, window.location.origin);
  for (const [k, v] of Object.entries(q)) if (v) u.searchParams.set(k, v);
  window.location.assign(u.toString());
}

function here() {
  return `${window.location.pathname}${window.location.search}`;
}

export function AuthProvider({
  children,
  basePath = "",
}: {
  children: ReactNode;
  /** Next basePath, if the app uses one. */
  basePath?: string;
}) {
  const [data, setData] = useState<SessionPayload | null>(null);
  const cache = useRef<{ token: string; exp: number } | null>(null);
  const inflight = useRef<Promise<SessionPayload> | null>(null);

  const fetchSession = useCallback(
    (fresh = false) => {
      if (inflight.current && !fresh) return inflight.current;
      const p = fetch(`${basePath}/auth/session${fresh ? "?fresh=1" : ""}`, {
        credentials: "same-origin",
        cache: "no-store",
      })
        .then((r) => (r.ok ? (r.json() as Promise<SessionPayload>) : { signedIn: false as const }))
        .catch(() => ({ signedIn: false as const }))
        .then((d) => {
          cache.current = d.signedIn ? { token: d.accessToken, exp: d.expiresAt } : null;
          setData(d);
          return d;
        })
        .finally(() => {
          if (inflight.current === p) inflight.current = null;
        });
      inflight.current = p;
      return p;
    },
    [basePath]
  );

  useEffect(() => {
    void fetchSession();
  }, [fetchSession]);

  const value = useMemo<AuthState>(() => {
    const signedIn = data?.signedIn === true ? data : null;
    return {
      isLoaded: data !== null,
      isSignedIn: Boolean(signedIn),
      userId: signedIn?.user.id ?? null,
      user: signedIn?.user ?? null,
      getToken: async (opts) => {
        const fresh = Boolean(opts?.fresh || opts?.skipCache);
        const c = cache.current;
        if (!fresh && c && c.exp - 30 > Date.now() / 1000) return c.token;
        const d = await fetchSession(fresh);
        return d.signedIn ? d.accessToken : null;
      },
      signIn: (o) =>
        go(`${basePath}/auth/login`, {
          return_to: o?.returnTo ?? here(),
          idp: o?.idpHint,
          login_hint: o?.loginHint,
        }),
      signUp: (o) =>
        go(`${basePath}/auth/register`, { return_to: o?.returnTo ?? here(), idp: o?.idpHint }),
      signOut: (o) => go(`${basePath}/auth/logout`, { return_to: o?.returnTo ?? "/sign-in" }),
      openAccount: () => window.open(`${basePath}/auth/account`, "_blank", "noopener"),
      reload: async () => {
        await fetchSession(true);
      },
    };
  }, [basePath, data, fetchSession]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/** Session for client components. Outside a provider it reports "loaded, signed out". */
export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (v) return v;
  return {
    isLoaded: true,
    isSignedIn: false,
    userId: null,
    user: null,
    getToken: async () => null,
    signIn: () => undefined,
    signUp: () => undefined,
    signOut: () => undefined,
    openAccount: () => undefined,
    reload: async () => undefined,
  };
}

export function useUser() {
  const a = useAuth();
  return { isLoaded: a.isLoaded, isSignedIn: a.isSignedIn, user: a.user };
}

/** Sends the browser to Keycloak (replaces the old embedded sign-in widget). */
export function SignInRedirect({
  mode = "sign-in",
  returnTo,
  fallback = null,
}: {
  mode?: "sign-in" | "sign-up";
  returnTo?: string;
  fallback?: ReactNode;
}) {
  const a = useAuth();
  useEffect(() => {
    if (!a.isLoaded) return;
    if (a.isSignedIn) {
      window.location.replace(returnTo ?? "/");
      return;
    }
    if (new URLSearchParams(window.location.search).get("auth_error")) return;
    const back = returnTo ?? new URLSearchParams(window.location.search).get("redirect_url") ?? "/";
    if (mode === "sign-up") a.signUp({ returnTo: back });
    else a.signIn({ returnTo: back });
  }, [a, mode, returnTo]);
  return <>{fallback}</>;
}

export function SignOutButton({ children, returnTo }: { children?: ReactNode; returnTo?: string }) {
  const a = useAuth();
  return (
    <span
      role="button"
      tabIndex={0}
      onClick={() => a.signOut({ returnTo })}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") a.signOut({ returnTo });
      }}
    >
      {children ?? "Sign out"}
    </span>
  );
}

function initials(u: SessionUser | null): string {
  const src =
    u?.fullName || [u?.firstName, u?.lastName].filter(Boolean).join(" ") || u?.email || "?";
  return (
    src
      .split(/[\s@.]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]!.toUpperCase())
      .join("") || "?"
  );
}

/** Avatar button: account (Keycloak console) and sign out. */
export function UserButton({ returnTo = "/sign-in" }: { returnTo?: string }) {
  const a = useAuth();
  const [open, setOpen] = useState(false);
  if (!a.isSignedIn) return null;
  return (
    <div className="relative">
      <button
        type="button"
        aria-label="Account menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-xs font-semibold text-white"
      >
        {initials(a.user)}
      </button>
      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-56 rounded-xl border border-primary/10 bg-white p-1 text-sm shadow-lg"
        >
          <p className="truncate px-3 py-2 text-muted">{a.user?.email ?? a.user?.username}</p>
          <button
            type="button"
            role="menuitem"
            className="block w-full rounded-lg px-3 py-2 text-left hover:bg-primary/5"
            onClick={() => a.openAccount()}
          >
            Manage account
          </button>
          <button
            type="button"
            role="menuitem"
            className="block w-full rounded-lg px-3 py-2 text-left text-red-600 hover:bg-red-50"
            onClick={() => a.signOut({ returnTo })}
          >
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}
