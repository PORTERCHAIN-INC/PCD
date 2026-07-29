import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AppClerkProvider, SessionContextProvider } from "@porterchain/auth";
import { publicEnv } from "@/lib/env";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Porterchain Customer Portal",
  description: "Track deliveries, invoices, and support",
};

export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ colorScheme: "light" }}>
      <body className={inter.className}>
        <AppClerkProvider
          publishableKey={publicEnv.clerkPublishableKey}
          signInUrl="/sign-in"
          afterSignOutUrl="/sign-in"
          fallbackRedirect="/dashboard"
        >
          <SessionContextProvider>{children}</SessionContextProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
