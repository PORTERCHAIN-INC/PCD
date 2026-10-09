"use client";

import { MessageCircle } from "lucide-react";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { buildWhatsAppDeepLink } from "@/lib/whatsapp";

type Props = {
  message: string;
  label: string;
  hint?: string;
  sourceSection: string;
  className?: string;
};

export default function WhatsAppQuoteLink({
  message,
  label,
  hint,
  sourceSection,
  className,
}: Props) {
  const href = buildWhatsAppDeepLink(message);

  return (
    <div className={className}>
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#075E54] px-5 py-3 text-sm font-semibold text-white hover:bg-[#064a42] transition-colors"
        onClick={() =>
          track(ANALYTICS_EVENTS.WHATSAPP_QUOTE_CLICK, {
            source_section: sourceSection,
          })
        }
      >
        <MessageCircle className="h-4 w-4 shrink-0" aria-hidden />
        {label}
      </a>
      {hint ? <p className="mt-3 text-xs text-muted leading-relaxed">{hint}</p> : null}
    </div>
  );
}
