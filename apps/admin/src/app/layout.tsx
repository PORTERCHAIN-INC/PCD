import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { SessionContextProvider } from "@porterchain/auth";
import { AdminAuthProvider } from "@/components/providers/AdminAuthProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Porterchain Admin",
  description: "Internal operations platform for Porterchain staff",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ colorScheme: "light" }}>
      <body className={inter.className}>
        <AdminAuthProvider>
          <SessionContextProvider>{children}</SessionContextProvider>
        </AdminAuthProvider>
      </body>
    </html>
  );
}
