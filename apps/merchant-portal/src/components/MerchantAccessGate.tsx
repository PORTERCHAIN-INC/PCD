"use client";

import { useCallback, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { LogOut } from "lucide-react";
import { Spinner } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { merchantProfileFromSession } from "@/lib/merchant-access";
import { fetchMerchantOnboarding, isPendingMerchantPath } from "@/lib/onboarding";
import { isClerkConfigured, publicEnv, useLocalDevAuth } from "@/lib/env";
import {
  platformLoginUrl,
  useOptionalSessionContext,
  usePortalSessionGate,
  type SessionContext,
} from "@porterchain/auth";
import { isDevelopmentBuild } from "@porterchain/auth/devBypass";

type Props = {
  children: ReactNode;
  onProfile?: (profile: import("@/lib/merchant-access").MerchantAccessProfile) => void;
};

export default function MerchantAccessGate({ children, onProfile }: Props) {
  const localDevAuth = useLocalDevAuth();
  // Ungated only in a development build. A shipped portal with no Clerk keys
  // shows a wall instead of the portal — missing keys fail closed (BJ).
  if (isDevelopmentBuild() && (localDevAuth || !isClerkConfigured())) {
    return <>{children}</>;
  }
  if (!isClerkConfigured()) {
    return <MerchantSignInUnavailable />;
  }
  return (
    <MerchantAccessGateWithClerk onProfile={onProfile}>{children}</MerchantAccessGateWithClerk>
  );
}

function MerchantSignInUnavailable() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <div className="max-w-md rounded-2xl border border-primary/10 bg-white p-6 text-center">
        <p className="font-semibold text-primary">Sign-in unavailable</p>
        <p className="mt-2 text-sm text-muted">
          We cannot open your portal right now. Nothing is wrong with your account — please try
          again shortly, and contact PorterChain if it keeps happening.
        </p>
      </div>
    </div>
  );
}

/** ACTIVE/APPROVED merchant session already proves portal access — skip session-context. */
function sessionFromMerchant(merchant: {
  merchant_id: string;
  company_name: string;
  role: string;
  modules: string[];
  user_email: string;
  status?: string;
}): SessionContext {
  return {
    user_id: merchant.user_email,
    status: merchant.status ?? "active",
    onboarding_status: "complete",
    default_workspace: merchant.merchant_id,
    email: merchant.user_email,
    roles: [merchant.role],
    permissions: ["merchant_portal.access"],
    modules: merchant.modules,
    organization_ids: [merchant.merchant_id],
    workspaces: [
      {
        id: merchant.merchant_id,
        label: merchant.company_name,
        kind: "merchant",
        organization_id: merchant.merchant_id,
      },
    ],
    legacy_profile_ids: {},
  };
}

function MerchantAccessGateWithClerk({ children, onProfile }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoaded: clerkLoaded, isSignedIn } = useAuth();
  const { isLoaded: merchantAuthLoaded, getApiToken, session: merchantSession } = useMerchantAuth();
  const sessionCtx = useOptionalSessionContext();
  const setSession = sessionCtx?.setSession;
  const setActiveWorkspaceId = sessionCtx?.setActiveWorkspaceId;
  const onPendingPath = isPendingMerchantPath(pathname);

  const onSession = useCallback(
    (ctx: SessionContext) => {
      setSession?.(ctx);
      if (ctx.default_workspace) {
        setActiveWorkspaceId?.(ctx.default_workspace);
      }
      if (merchantSession) {
        onProfile?.({
          company_name: merchantSession.company_name,
          email: merchantSession.user_email,
          status: merchantSession.status ?? ctx.status,
          merchant_id: merchantSession.merchant_id,
          enterprise_role: merchantSession.role,
          logo_url: merchantSession.logo_url,
        });
      } else {
        onProfile?.(merchantProfileFromSession(ctx));
      }
    },
    [merchantSession, onProfile, setActiveWorkspaceId, setSession]
  );

  const onSignedOut = useCallback(() => {
    setSession?.(null);
    router.replace("/sign-in");
  }, [router, setSession]);

  const onNeedOnboarding = useCallback(() => {
    router.replace("/onboarding");
  }, [router]);

  // MerchantAuth already loaded /v1/merchant/session — skip onboarding API when clearly active.
  const fetchOnboarding = useCallback(
    async (token: string) => {
      const st = (merchantSession?.status || "").toUpperCase();
      if (st === "ACTIVE" || st === "APPROVED") {
        return { ready: true };
      }
      return fetchMerchantOnboarding(token);
    },
    [merchantSession?.status]
  );

  const resolveSession = useCallback(
    async (_token: string): Promise<SessionContext | null> => {
      const st = (merchantSession?.status || "").toUpperCase();
      if (!merchantSession || (st !== "ACTIVE" && st !== "APPROVED")) return null;
      return sessionFromMerchant(merchantSession);
    },
    [merchantSession]
  );

  // Wait for merchant session so ACTIVE users skip the duplicate session-context call.
  const gateReady = clerkLoaded && merchantAuthLoaded;

  const { checking, denied, errorDetail } = usePortalSessionGate({
    portal: "merchant",
    apiUrl: publicEnv.porterchainApiUrl,
    isLoaded: gateReady,
    isSignedIn: !!isSignedIn,
    getToken: getApiToken,
    skipCheck: onPendingPath,
    fetchOnboarding,
    resolveSession,
    onSession,
    onSignedOut,
    onNeedOnboarding,
  });

  if (!gateReady || checking) {
    return <Spinner label="Loading session…" />;
  }

  if (denied || errorDetail) {
    const loginUrl = platformLoginUrl(publicEnv.websiteUrl);
    const deniedAccess = errorDetail === "missing_portal_permission" || denied;
    return (
      <div className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-lg font-semibold text-primary">
          {deniedAccess ? "Access denied" : "Session error"}
        </h1>
        <p className="text-sm text-muted">
          {deniedAccess
            ? "This account is not provisioned for the Merchant portal."
            : errorDetail === "porterchain_api_timeout"
              ? "Porterchain API did not respond. Start the API on port 8001 and refresh."
              : errorDetail === "merchant_closed"
                ? "This company account is closed. Use Company at the top to switch to another company, or contact PorterChain."
                : errorDetail === "merchant_suspended"
                  ? "This company is suspended. Use Company at the top to switch to another company, or contact PorterChain to restore access."
                  : `Could not load your session (${errorDetail || "unknown"}).`}
        </p>
        <a
          href={loginUrl}
          className="mt-2 inline-flex rounded-xl bg-secondary px-4 py-2.5 text-sm font-semibold text-white"
        >
          Back to Platform login
        </a>
        <SignOutButton redirectUrl={loginUrl}>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </SignOutButton>
      </div>
    );
  }

  return <>{children}</>;
}
