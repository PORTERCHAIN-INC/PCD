import type { Metadata } from "next";
import { Carlito } from "next/font/google";
import { SessionContextProvider } from "@porterchain/auth";
import { AdminAuthProvider } from "@/components/providers/AdminAuthProvider";
import "./globals.css";

/** Calibri-compatible web font (Calibri is used when installed on the OS). */
const brand = Carlito({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-brand",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Porterchain Admin",
  description: "Internal operations platform for Porterchain staff",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={brand.variable}
      style={{ colorScheme: "light" }}
      suppressHydrationWarning
    >
      {/* suppressHydrationWarning: browser extensions (e.g. Grammarly) inject body attrs */}
      <body className={brand.className} suppressHydrationWarning>
        <AdminAuthProvider>
          <SessionContextProvider>{children}</SessionContextProvider>
        </AdminAuthProvider>
      </body>
    </html>
  );
}
