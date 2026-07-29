import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AppClerkProvider, SessionContextProvider } from "@porterchain/auth";
import { AdminAuthProvider } from "@/components/providers/AdminAuthProvider";
import { publicEnv } from "@/lib/env";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Porterchain Admin",
  description: "Internal operations platform for Porterchain staff",
};

function allowedRedirectOrigins(): string[] {
  const origins = new Set<string>(["https://admin.porterchain.com"]);
  const site = (process.env.NEXT_PUBLIC_SITE_URL ?? "").trim();
  if (site) origins.add(site.replace(/\/$/, ""));
  if (process.env.NEXT_PUBLIC_APP_ENV === "local" || process.env.NODE_ENV === "development") {
    origins.add("http://localhost:3002");
    origins.add("http://127.0.0.1:3002");
  }
  return [...origins];
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ colorScheme: "light" }}>
      <body className={inter.className}>
        <AppClerkProvider
          publishableKey={publicEnv.clerkPublishableKey}
          signInUrl={process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL ?? "/sign-in"}
          signUpUrl={process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL ?? "/sign-in"}
          afterSignOutUrl={process.env.NEXT_PUBLIC_CLERK_AFTER_SIGN_OUT_URL ?? "/sign-in"}
          fallbackRedirect={
            process.env.NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL ?? "/dashboard"
          }
          forceRedirect={process.env.NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL ?? "/dashboard"}
          allowedOrigins={allowedRedirectOrigins()}
        >
          <AdminAuthProvider>
            <SessionContextProvider>{children}</SessionContextProvider>
          </AdminAuthProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
