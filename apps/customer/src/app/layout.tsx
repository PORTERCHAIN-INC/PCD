import type { Metadata } from "next";
import { Carlito } from "next/font/google";
import { AppClerkProvider, ImpersonationBanner, SessionContextProvider } from "@porterchain/auth";
import CustomerQueryProvider from "@/components/providers/CustomerQueryProvider";
import { publicEnv } from "@/lib/env";
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={brand.variable} style={{ colorScheme: "light" }}>
      <body className={brand.className}>
        <AppClerkProvider
          publishableKey={publicEnv.clerkPublishableKey}
          signInUrl="/sign-in"
          signUpUrl="/sign-up"
          afterSignOutUrl="/sign-in"
          fallbackRedirect="/dashboard"
        >
          <CustomerQueryProvider>
            <SessionContextProvider>
              <ImpersonationBanner portal="customer" />
              {children}
            </SessionContextProvider>
          </CustomerQueryProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
