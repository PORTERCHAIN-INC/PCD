"use client";

import { Link } from "@/i18n/navigation";
import { ArrowRight } from "lucide-react";
import FadeIn from "@/components/corporate/motion/FadeIn";
import {
  resolveFeatureIcon,
  type FeatureIconName,
} from "@/components/corporate/icons/feature-icons";

export type SolutionCardData = {
  key: string;
  href: string;
  title: string;
  description: string;
  icon: FeatureIconName;
  viewLabel: string;
};

export default function HowItWorksSolutionCards({ items }: { items: SolutionCardData[] }) {
  return (
    <div className="grid sm:grid-cols-2 gap-4 sm:gap-5">
      {items.map((item, i) => {
        const Icon = resolveFeatureIcon(item.icon);
        return (
          <FadeIn key={item.key} delay={i * 0.06}>
            <Link
              href={item.href}
              className="group flex h-full flex-col rounded-2xl border border-primary/8 bg-white p-5 sm:p-6 shadow-sm transition-all hover:border-secondary/30 hover:shadow-md"
            >
              {Icon ? (
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
              ) : null}
              <h3 className="mt-4 text-lg font-semibold text-primary tracking-tight">
                {item.title}
              </h3>
              <p className="mt-2 flex-1 text-sm text-muted leading-relaxed">{item.description}</p>
              <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-secondary">
                {item.viewLabel}
                <ArrowRight
                  className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
                  aria-hidden
                />
              </span>
            </Link>
          </FadeIn>
        );
      })}
    </div>
  );
}
