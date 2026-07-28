"use client";

import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";

type Props = {
  href: string;
  children: React.ReactNode;
  className?: string;
  external?: boolean;
  sourceSection: string;
  event: "phone" | "email" | "whatsapp";
};

const EVENT_MAP = {
  phone: ANALYTICS_EVENTS.PHONE_CLICK,
  email: ANALYTICS_EVENTS.EMAIL_CLICK,
  whatsapp: ANALYTICS_EVENTS.WHATSAPP_CHAT_CLICK,
} as const;

/** Trackable tel:/mailto:/WhatsApp anchors for contact surfaces. */
export default function TrackedContactLink({
  href,
  children,
  className,
  external,
  sourceSection,
  event,
}: Props) {
  return (
    <a
      href={href}
      target={external ? "_blank" : undefined}
      rel={external ? "noopener noreferrer" : undefined}
      className={className}
      onClick={() =>
        track(EVENT_MAP[event], {
          source_section: sourceSection,
          href,
        })
      }
    >
      {children}
    </a>
  );
}
