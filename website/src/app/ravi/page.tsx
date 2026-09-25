import type { Metadata } from "next";
import { RaviContactCard } from "@/components/personal/ravi/RaviContactCard";
import { raviContact } from "@/lib/ravi-contact";
import "./ravi-contact.css";

const pageUrl = "https://porterchain.com/ravi";
const ogTitle = `${raviContact.name} | ${raviContact.company}`;
const ogDescription = `${raviContact.role} · ${raviContact.company} · ${raviContact.phone}`;

export const metadata: Metadata = {
  title: ogTitle,
  description: `Connect with ${raviContact.name}, ${raviContact.role} at ${raviContact.company}. Phone, email, and social links.`,
  alternates: { canonical: pageUrl },
  openGraph: {
    title: ogTitle,
    description: ogDescription,
    url: pageUrl,
    siteName: raviContact.company,
    type: "profile",
    locale: "en_CA",
  },
  twitter: {
    card: "summary_large_image",
    title: ogTitle,
    description: ogDescription,
  },
  robots: { index: true, follow: true },
};

export default function RaviContactPage() {
  return <RaviContactCard />;
}
