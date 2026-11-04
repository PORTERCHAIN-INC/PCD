import CookieConsent from "@/components/consent/CookieConsent";
import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Carlito } from "next/font/google";
import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { AppAuthProvider, ImpersonationBanner, SessionContextProvider } from "@porterchain/auth";
import { PC_IMP_FLAG } from "@porterchain/auth/impersonation";
import CustomerFrame from "@/components/CustomerFrame";
import CustomerQueryProvider from "@/components/providers/CustomerQueryProvider";
import { publicEnv } from "@/lib/env";
import { customerServerFetch } from "@/lib/server-api";
import { I18N_HEAD_SCRIPT, I18nRoot } from "@/i18n/I18nRoot";
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
  const jar = await cookies();
  const impersonating = jar.get(PC_IMP_FLAG)?.value === "1";
  const uiFr = jar.get("pc_locale")?.value === "fr";
  const client = new QueryClient();
  const inbox = await customerServerFetch<unknown>("/v1/notifications/inbox?limit=20");
  if (inbox) client.setQueryData(["customer-notification-inbox"], inbox);

  const region = await customerServerFetch<{ locale?: string; cookie_banner?: boolean }>(
    "/v1/public/region"
  );
  const locale = region?.locale ?? "en-CA";

  return (
    <html
      lang={uiFr ? "fr-CA" : locale.slice(0, 2)}
      className={brand.variable}
      style={{ colorScheme: "light" }}
      {...(uiFr ? { "data-i18n-pending": "" } : {})}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: I18N_HEAD_SCRIPT }} />
      </head>
      <body className={brand.className}>
        <I18nRoot>
          <AppAuthProvider>
            <CustomerQueryProvider>
              <HydrationBoundary state={dehydrate(client)}>
                <SessionContextProvider>
                  <ImpersonationBanner portal="customer" active={impersonating} />
                  <CustomerFrame>{children}</CustomerFrame>
                  <CookieConsent show={!!region?.cookie_banner} locale={locale} />
                </SessionContextProvider>
              </HydrationBoundary>
            </CustomerQueryProvider>
          </AppAuthProvider>
        </I18nRoot>
      </body>
    </html>
  );
}
