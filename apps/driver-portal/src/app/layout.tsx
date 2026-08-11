import type { Metadata } from "next";
import { Carlito } from "next/font/google";
import { AppClerkProvider, SessionContextProvider } from "@porterchain/auth";
import { CommunicationsProvider } from "@/components/providers/CommunicationsProvider";
import { GoogleMapsProvider } from "@porterchain/maps";
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
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
            <CommunicationsProvider>
              <GoogleMapsProvider apiKey={publicEnv.googleMapsApiKey}>
                {children}
              </GoogleMapsProvider>
            </CommunicationsProvider>
          </SessionContextProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
