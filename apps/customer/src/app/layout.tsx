import CookieConsent from "@/components/consent/CookieConsent";
import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Carlito } from "next/font/google";
import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { AppClerkProvider, ImpersonationBanner, SessionContextProvider } from "@porterchain/auth";
import { PC_IMP_FLAG } from "@porterchain/auth/impersonation";
import CustomerFrame from "@/components/CustomerFrame";
import CustomerQueryProvider from "@/components/providers/CustomerQueryProvider";
import { publicEnv } from "@/lib/env";
import { customerServerFetch } from "@/lib/server-api";
import "./globals.css";

const brand = Carlito({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-brand",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Porterchain Customer Portal",
  description: "Track deliveries, invoices, and support",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const impersonating = (await cookies()).get(PC_IMP_FLAG)?.value === "1";
  const client = new QueryClient();
  const inbox = await customerServerFetch<unknown>("/v1/notifications/inbox?limit=20");
  if (inbox) client.setQueryData(["customer-notification-inbox"], inbox);

  const region = await customerServerFetch<{ locale?: string; cookie_banner?: boolean }>(
    "/v1/public/region"
  );
  const locale = region?.locale ?? "en-CA";

  return (
    <html lang={locale.slice(0, 2)} className={brand.variable} style={{ colorScheme: "light" }}>
      <body className={brand.className}>
        <AppClerkProvider
          publishableKey={publicEnv.clerkPublishableKey}
          signInUrl="/sign-in"
          signUpUrl="/sign-up"
          afterSignOutUrl="/sign-in"
          fallbackRedirect="/orders"
        >
          <CustomerQueryProvider>
            <HydrationBoundary state={dehydrate(client)}>
              <SessionContextProvider>
                <ImpersonationBanner portal="customer" active={impersonating} />
                <CustomerFrame>{children}</CustomerFrame>
                <CookieConsent show={!!region?.cookie_banner} locale={locale} />
              </SessionContextProvider>
            </HydrationBoundary>
          </CustomerQueryProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
