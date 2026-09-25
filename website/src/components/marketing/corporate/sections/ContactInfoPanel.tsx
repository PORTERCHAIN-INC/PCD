"use client";

import { Phone, Mail, MessageCircle, Clock, AlertCircle } from "lucide-react";
import FadeIn from "@/components/marketing/corporate/motion/FadeIn";
import TrackedContactLink from "@/components/seo/TrackedContactLink";

export interface ContactInfoData {
  phoneLabel: string;
  phone: string;
  phoneHref: string;
  emailLabel: string;
  email: string;
  emailHref: string;
  whatsappLabel: string;
  whatsapp: string;
  whatsappHref: string;
  hoursLabel: string;
  hours: string;
  emergencyLabel: string;
  emergency: string;
  emergencyDetail: string;
}

interface ContactInfoPanelProps {
  info: ContactInfoData;
}

function contactEvent(href: string): "phone" | "email" | "whatsapp" {
  if (href.startsWith("mailto:")) return "email";
  if (href.includes("wa.me") || href.includes("whatsapp")) return "whatsapp";
  return "phone";
}

export default function ContactInfoPanel({ info }: ContactInfoPanelProps) {
  const items = [
    {
      icon: Phone,
      label: info.phoneLabel,
      value: info.phone,
      href: info.phoneHref,
      external: true,
    },
    {
      icon: Mail,
      label: info.emailLabel,
      value: info.email,
      href: info.emailHref,
      external: true,
    },
    {
      icon: MessageCircle,
      label: info.whatsappLabel,
      value: info.whatsapp,
      href: info.whatsappHref,
      external: true,
    },
    {
      icon: Clock,
      label: info.hoursLabel,
      value: info.hours,
    },
    {
      icon: AlertCircle,
      label: info.emergencyLabel,
      value: info.emergency,
      detail: info.emergencyDetail,
      href: info.phoneHref,
      external: true,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        {items.map((item, i) => (
          <FadeIn key={item.label} delay={i * 0.05}>
            <div className="flex gap-4 p-4 rounded-xl hover:bg-white/80 transition-colors group">
              <div className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center shrink-0 group-hover:bg-secondary/15 transition-colors">
                <item.icon className="w-[18px] h-[18px] text-secondary" aria-hidden />
              </div>
              <div className="min-w-0 pt-0.5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                  {item.label}
                </p>
                {item.href ? (
                  <TrackedContactLink
                    href={item.href}
                    external={item.external}
                    sourceSection="contact_info_panel"
                    event={contactEvent(item.href)}
                    className="mt-1 block text-sm font-medium text-primary hover:text-secondary transition-colors leading-relaxed"
                  >
                    {item.value}
                  </TrackedContactLink>
                ) : (
                  <p className="mt-1 text-sm font-medium text-primary leading-relaxed">
                    {item.value}
                  </p>
                )}
                {item.detail && <p className="mt-0.5 text-xs text-muted">{item.detail}</p>}
              </div>
            </div>
          </FadeIn>
        ))}
      </div>
    </div>
  );
}
