import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Carlito } from "next/font/google";
import { siteConfig } from "@/lib/seo/config";
import "./globals.css";

const brand = Carlito({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-brand",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(siteConfig.baseUrl),
};

type Props = {
  children: ReactNode;
};

/** Root layout — Next.js requires html/body here (covers /ravi and [locale]). */
export default function RootLayout({ children }: Props) {
  return (
    <html
      lang="en"
      className={`${brand.variable} scroll-smooth`}
      style={{ colorScheme: "light" }}
      suppressHydrationWarning
    >
      <body
        className={`${brand.className} min-h-screen bg-white font-sans antialiased`}
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
