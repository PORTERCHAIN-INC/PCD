import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Carlito } from "next/font/google";
import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { AppClerkProvider, ImpersonationBanner, SessionContextProvider } from "@porterchain/auth";
import { PC_IMP_FLAG } from "@porterchain/auth/impersonation";
import { MerchantAuthProvider } from "@/components/providers/MerchantAuthProvider";
import MerchantQueryProvider from "@/components/providers/MerchantQueryProvider";
import { publicEnv } from "@/lib/env";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";
import SignupAttributionCapture from "@/components/SignupAttributionCapture";
import "./globals.css";

const brand = Carlito({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-brand",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Porterchain Merchant Portal",
  description: "Secure B2B delivery portal for approved Porterchain merchants",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const initialOrgId = (await merchantOrgId()) ?? undefined;
  const impersonating = (await cookies()).get(PC_IMP_FLAG)?.value === "1";
  const client = new QueryClient();
  if (initialOrgId && !impersonating) {
    const inbox = await merchantServerFetch<unknown>(
      "/v1/notifications/inbox?limit=20",
      initialOrgId
    );
    if (inbox) client.setQueryData(["merchant-notification-inbox", initialOrgId], inbox);
  }
  return (
    <html
      lang="en"
      className={brand.variable}
      suppressHydrationWarning
      style={{ colorScheme: "light" }}
    >
      <body className={`${brand.className} min-h-dvh bg-gray-bg text-primary antialiased`}>
        <AppClerkProvider
          publishableKey={publicEnv.clerkPublishableKey}
          signInUrl="/sign-in"
          signUpUrl="/sign-up"
          afterSignOutUrl="/sign-in"
          fallbackRedirect="/dashboard"
        >
          <MerchantAuthProvider initialOrgId={initialOrgId}>
            <MerchantQueryProvider>
              <HydrationBoundary state={dehydrate(client)}>
                <SessionContextProvider>
                  <SignupAttributionCapture />
                  <ImpersonationBanner portal="merchant" active={impersonating} />
                  {children}
                </SessionContextProvider>
              </HydrationBoundary>
            </MerchantQueryProvider>
          </MerchantAuthProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
