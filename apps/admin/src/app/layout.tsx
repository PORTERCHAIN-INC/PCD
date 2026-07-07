import type { Metadata } from "next";
import { Inter } from "next/font/google";
import AppClerkProvider from "@/components/providers/AppClerkProvider";
import { AdminAuthProvider } from "@/components/providers/AdminAuthProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Porterchain Admin",
  description: "Internal operations platform for Porterchain staff",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AppClerkProvider>
          <AdminAuthProvider>{children}</AdminAuthProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
