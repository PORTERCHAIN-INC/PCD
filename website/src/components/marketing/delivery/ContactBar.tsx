import { Clock3, Mail, Phone } from "lucide-react";
import Container from "@/components/ui/Container";
import { PUBLIC_CONTACT_PHONE_E164 } from "@/lib/google-business";

const EMAIL = "enterprise@porterchain.com";
const PHONE_DISPLAY = "+1 (647) 619-7951";

/** One compact contact bar for industry and area pages (same details as the footer). */
export default function ContactBar() {
  return (
    <section aria-labelledby="contact-bar-heading" className="bg-gray-bg">
      <Container className="py-8">
        <div
          className="flex flex-col gap-4 rounded-2xl border border-primary/10 bg-white p-5 sm:flex-row sm:items-center sm:justify-between"
          data-testid="contact-bar"
        >
          <h2 id="contact-bar-heading" className="text-base font-semibold text-primary">
            Talk to the Toronto team
          </h2>
          <ul className="flex flex-col gap-2 text-sm text-primary sm:flex-row sm:flex-wrap sm:gap-x-6">
            <li className="flex items-center gap-2">
              <Phone className="h-4 w-4 text-secondary" aria-hidden />
              <a
                href={`tel:${PUBLIC_CONTACT_PHONE_E164}`}
                className="font-semibold hover:text-secondary"
              >
                {PHONE_DISPLAY}
              </a>
            </li>
            <li className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-secondary" aria-hidden />
              <a href={`mailto:${EMAIL}`} className="font-semibold hover:text-secondary">
                {EMAIL}
              </a>
            </li>
            <li className="flex items-center gap-2 text-muted">
              <Clock3 className="h-4 w-4 text-secondary" aria-hidden />
              Mon–Fri 8 AM–6 PM · Sat 9 AM–2 PM
            </li>
          </ul>
        </div>
      </Container>
    </section>
  );
}
