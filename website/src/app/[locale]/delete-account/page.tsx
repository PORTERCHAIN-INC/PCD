import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import { routing } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

/** Public account deletion page (G21 A-APR-03; Google Play web deletion requirement). */
export const metadata: Metadata = {
  title: "Delete your PorterChain account | PorterChain",
  description: "How to delete your PorterChain customer or driver account and what data is kept.",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

const MAILTO =
  "mailto:privacy@porterchain.com?subject=" +
  encodeURIComponent("Account deletion request") +
  "&body=" +
  encodeURIComponent(
    "Please delete my PorterChain account.\nApp (customer or driver):\nEmail on the account:\n"
  );

export default async function DeleteAccountPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SiteShell>
      <Container className="py-10 md:py-16">
        <article className="prose max-w-2xl" data-testid="delete-account-page">
          <h1>Delete your PorterChain account</h1>
          <h2>In the app</h2>
          <ul>
            <li>
              <strong>PorterChain (customer):</strong> Account → Request account deletion.
            </li>
            <li>
              <strong>PorterChain Driver:</strong> Me → Settings → Delete account.
            </li>
          </ul>
          <h2>Without the app</h2>
          <p>
            Email <a href={MAILTO}>privacy@porterchain.com</a> from the address on your account. We
            confirm within 30 days.
          </p>
          <h2>What is deleted and what is kept</h2>
          <p>
            We delete your profile, saved addresses, contact details and sign-in. Delivery and tax
            records the law requires (for example invoices and proof of delivery) are kept for the
            legal retention period, then deleted.
          </p>
        </article>
      </Container>
    </SiteShell>
  );
}
