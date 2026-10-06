import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Carlito } from "next/font/google";
import { AppClerkProvider, ImpersonationBanner, SessionContextProvider } from "@porterchain/auth";
import { PC_IMP_FLAG } from "@porterchain/auth/impersonation";
import { CommunicationsProvider } from "@/components/providers/CommunicationsProvider";
import DriverQueryProvider from "@/components/providers/DriverQueryProvider";
import DriverFrame from "@/components/DriverFrame";
import { publicEnv } from "@/lib/env";
import "./globals.css";

const brand = Carlito({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-brand",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Porterchain Driver",
  description: "Driver platform — earnings, stops, POD, wallet",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
  },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const impersonating = (await cookies()).get(PC_IMP_FLAG)?.value === "1";
  return (
    <html lang="en" className={brand.variable} style={{ colorScheme: "light" }}>
      <body className={brand.className}>
        <AppClerkProvider
          publishableKey={publicEnv.clerkPublishableKey}
          signInUrl="/login"
          afterSignOutUrl="/login"
          fallbackRedirect="/onboarding"
        >
          <SessionContextProvider>
            <ImpersonationBanner portal="driver" active={impersonating} />
            <DriverQueryProvider>
              <CommunicationsProvider>
                <DriverFrame>{children}</DriverFrame>
              </CommunicationsProvider>
            </DriverQueryProvider>
          </SessionContextProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
