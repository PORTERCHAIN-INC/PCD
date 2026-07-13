"use client";

import { useTranslations } from "next-intl";
import { MapPin } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Marquee from "@/components/magic/marquee";

const CITY_SLUGS: Record<string, string> = {
  Toronto: "toronto",
  Mississauga: "mississauga",
  Brampton: "brampton",
  Vaughan: "vaughan",
  Markham: "markham",
  Oakville: "oakville",
  Hamilton: "hamilton",
  "Kitchener–Waterloo": "kitchener-waterloo",
};

export default function HomeGtaMarquee() {
  const t = useTranslations("gtaFrame");
  const cities = t.raw("cities") as string[];

  const chips = cities.map((city) => {
    const slug = CITY_SLUGS[city];
    const className =
      "flex shrink-0 items-center gap-2 rounded-full border border-primary/8 bg-white px-4 py-2.5 text-sm font-semibold text-primary shadow-sm transition-colors hover:border-secondary/30 hover:text-secondary";
    const content = (
      <>
        <MapPin className="h-3.5 w-3.5 text-secondary" aria-hidden />
        {city}
      </>
    );

    return slug ? (
      <Link key={city} href={`/service-areas/${slug}`} className={className}>
        {content}
      </Link>
    ) : (
      <span key={city} className={className}>
        {content}
      </span>
    );
  });

  return (
    <section className="border-b border-primary/6 bg-gray-bg/80 py-4 overflow-hidden">
      <p className="mb-3 text-center text-[11px] font-semibold uppercase tracking-[0.22em] text-muted">
        {t("label")}
      </p>
      <Marquee speed="slow">
        <div className="flex gap-3 px-2">{chips}</div>
      </Marquee>
    </section>
  );
}
