import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Porterchain Driver",
  description: "Driver platform — earnings, stops, POD, wallet",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
