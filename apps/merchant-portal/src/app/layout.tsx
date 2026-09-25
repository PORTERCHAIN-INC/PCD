import type { Metadata } from "next";
import { Carlito } from "next/font/google";
import { AppClerkProvider, ImpersonationBanner, SessionContextProvider } from "@porterchain/auth";
import { MerchantAuthProvider } from "@/components/providers/MerchantAuthProvider";
import MerchantQueryProvider from "@/components/providers/MerchantQueryProvider";
import { publicEnv } from "@/lib/env";
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
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
          <MerchantAuthProvider>
            <MerchantQueryProvider>
              <SessionContextProvider>
                <ImpersonationBanner portal="merchant" />
                {children}
              </SessionContextProvider>
            </MerchantQueryProvider>
          </MerchantAuthProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
