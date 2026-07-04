import type { Metadata } from "next";
import { Inter } from "next/font/google";
import AppClerkProvider from "@/components/AppClerkProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Porterchain Customer Portal",
  description: "Track deliveries, invoices, and support",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AppClerkProvider>{children}</AppClerkProvider>
      </body>
    </html>
  );
}
