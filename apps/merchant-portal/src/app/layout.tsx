import type { Metadata } from "next";
import { Inter } from "next/font/google";
import AppClerkProvider from "@/components/providers/AppClerkProvider";
import { MerchantAuthProvider } from "@/components/providers/MerchantAuthProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Porterchain Merchant Portal",
  description: "Secure B2B delivery portal for approved Porterchain merchants",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.variable}>
        <AppClerkProvider>
          <MerchantAuthProvider>{children}</MerchantAuthProvider>
        </AppClerkProvider>
      </body>
    </html>
  );
}
