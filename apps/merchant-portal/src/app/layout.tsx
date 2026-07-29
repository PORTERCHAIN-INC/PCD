import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AppClerkProvider, SessionContextProvider } from "@porterchain/auth";
import { MerchantAuthProvider } from "@/components/providers/MerchantAuthProvider";
import { publicEnv } from "@/lib/env";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Porterchain Merchant Portal",
  description: "Secure B2B delivery portal for approved Porterchain merchants",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning style={{ colorScheme: "light" }}>
      <body className={`${inter.variable} min-h-dvh bg-gray-bg text-primary antialiased`}>
        <AppClerkProvider
          publishableKey={publicEnv.clerkPublishableKey}
          signInUrl="/sign-in"
          signUpUrl="/sign-up"
          afterSignOutUrl="/sign-in"
          fallbackRedirect="/dashboard"
        >
          <MerchantAuthProvider>
            <SessionContextProvider>{children}</SessionContextProvider>
          </MerchantAuthProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
