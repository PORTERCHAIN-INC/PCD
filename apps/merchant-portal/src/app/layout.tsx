import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Carlito } from "next/font/google";
import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { AppAuthProvider, ImpersonationBanner, SessionContextProvider } from "@porterchain/auth";
import { PC_IMP_FLAG } from "@porterchain/auth/impersonation";
import { MerchantAuthProvider } from "@/components/providers/MerchantAuthProvider";
import MerchantQueryProvider from "@/components/providers/MerchantQueryProvider";
import { publicEnv } from "@/lib/env";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";
import SignupAttributionCapture from "@/components/SignupAttributionCapture";
import { I18N_HEAD_SCRIPT, I18nRoot } from "@/i18n/I18nRoot";
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
  const jar = await cookies();
  const impersonating = jar.get(PC_IMP_FLAG)?.value === "1";
  const uiFr = jar.get("pc_locale")?.value === "fr";
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
      lang={uiFr ? "fr-CA" : "en"}
      {...(uiFr ? { "data-i18n-pending": "" } : {})}
      className={brand.variable}
      suppressHydrationWarning
      style={{ colorScheme: "light" }}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: I18N_HEAD_SCRIPT }} />
      </head>
      <body className={`${brand.className} min-h-dvh bg-gray-bg text-primary antialiased`}>
        <I18nRoot>
          <AppAuthProvider>
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
          </AppAuthProvider>
        </I18nRoot>
      </body>
    </html>
  );
}
