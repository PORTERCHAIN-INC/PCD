import Image from "next/image";
import { ArrowRight, Check, ChevronDown, X } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/marketing/ui/SectionHeader";
import type { VerticalPhoto } from "@/components/marketing/delivery/vertical-visuals";

/** Server-only building blocks for the /delivery pages (no client JS). */

export function DeliverySection({
  title,
  eyebrow,
  lead,
  children,
  tone = "white",
  id,
}: {
  title?: string;
  eyebrow?: string;
  lead?: string;
  children: React.ReactNode;
  tone?: "white" | "soft";
  id?: string;
}) {
  const headingId = id ? `${id}-heading` : undefined;
  return (
    <section
      id={id}
      aria-labelledby={title ? headingId : undefined}
      className={tone === "soft" ? "bg-gray-bg py-14 sm:py-20" : "bg-white py-14 sm:py-20"}
    >
      <Container>
        {title ? (
          <SectionHeader id={headingId} eyebrow={eyebrow} title={title} lead={lead} />
        ) : null}
        <div className={title ? "mt-8" : undefined}>{children}</div>
      </Container>
    </section>
  );
}

export function QuickFacts({ items }: { items: Array<{ label: string; value: string }> }) {
  return (
    <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="rounded-2xl border border-primary/10 bg-white p-4">
          <dt className="text-xs font-medium uppercase tracking-wide text-muted">{item.label}</dt>
          <dd className="mt-1 text-base font-semibold text-primary">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => (
        <li
          key={item}
          className="flex gap-3 rounded-2xl border border-primary/8 bg-white p-4 text-sm leading-relaxed text-primary/90 sm:p-5 sm:text-base"
        >
          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-800">
            <Check className="h-3.5 w-3.5" aria-hidden />
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

/** Titled cards (hub sections such as vehicles, multi-box handling, scheduling). */
export function CardGrid({
  items,
  numbered = false,
}: {
  items: Array<{ title: string; body: string; photo?: VerticalPhoto }>;
  numbered?: boolean;
}) {
  return (
    <ul className={items.length === 2 ? "grid gap-4 md:grid-cols-2" : "grid gap-4 md:grid-cols-3"}>
      {items.map((item, index) => (
        <li
          key={item.title}
          className="overflow-hidden rounded-2xl border border-primary/8 bg-white"
        >
          {item.photo ? (
            <Image
              src={item.photo.src}
              alt={item.photo.alt}
              width={item.photo.width}
              height={item.photo.height}
              sizes="(min-width: 768px) 560px, 100vw"
              className="aspect-[16/8] w-full object-cover"
            />
          ) : null}
          <div className={item.photo ? "p-6" : "border-t-2 border-secondary/70 p-6"}>
            {numbered ? (
              <span className="mb-4 flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-white">
                {index + 1}
              </span>
            ) : null}
            <h3 className="text-lg font-semibold text-primary">{item.title}</h3>
            <p className="mt-1.5 text-sm leading-relaxed text-muted sm:text-base">{item.body}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

/** What the service includes / does not include — factual service terms, side by side. */
export function IncludedList({
  included,
  notIncluded,
  includedLabel = "Included",
  notIncludedLabel = "Not included",
}: {
  included: string[];
  notIncluded: string[];
  includedLabel?: string;
  notIncludedLabel?: string;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-2xl border border-emerald-200 bg-white p-6">
        <h3 className="text-base font-semibold text-emerald-900">{includedLabel}</h3>
        <ul className="mt-4 space-y-3">
          {included.map((item) => (
            <li
              key={item}
              className="flex gap-3 text-sm leading-relaxed text-primary/90 sm:text-base"
            >
              <Check className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" aria-hidden />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded-2xl border border-primary/10 bg-white p-6">
        <h3 className="text-base font-semibold text-primary">{notIncludedLabel}</h3>
        <ul className="mt-4 space-y-3">
          {notIncluded.map((item) => (
            <li
              key={item}
              className="flex gap-3 text-sm leading-relaxed text-primary/90 sm:text-base"
            >
              <X className="mt-0.5 h-5 w-5 shrink-0 text-rose-700" aria-hidden />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function VehicleCards({
  vehicles,
}: {
  vehicles: Array<{
    id: string;
    label: string;
    capacity: string;
    bestFor: string;
    photo?: VerticalPhoto;
  }>;
}) {
  return (
    <ul
      className={
        vehicles.length === 1
          ? "grid gap-4 sm:max-w-md"
          : "grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      }
    >
      {vehicles.map((v) => (
        <li key={v.id} className="overflow-hidden rounded-2xl border border-primary/8 bg-white">
          {v.photo ? (
            <Image
              src={v.photo.src}
              alt=""
              width={v.photo.width}
              height={v.photo.height}
              sizes="(min-width: 1024px) 380px, (min-width: 640px) 50vw, 100vw"
              className="aspect-[16/9] w-full object-cover"
            />
          ) : null}
          <div className="p-5">
            <p className="text-lg font-semibold text-primary">{v.label}</p>
            <p className="mt-1 text-sm text-muted">Capacity: {v.capacity}.</p>
            <p className="mt-1 text-sm text-muted">Best for {v.bestFor}.</p>
            <p className="mt-2 text-xs font-medium text-primary/70">
              Driven on a standard Ontario G licence.
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

/** FAQ answers are in the HTML (not collapsed behind JS) for search and AI crawlers. */
export function FaqList({ items }: { items: Array<{ question: string; answer: string }> }) {
  return (
    <div className="max-w-3xl divide-y divide-primary/10 border-y border-primary/10">
      {items.map((item) => (
        <details key={item.question} className="group" open>
          <summary className="flex min-h-[3.25rem] cursor-pointer list-none items-center justify-between gap-4 rounded py-4 text-left text-base font-semibold text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary [&::-webkit-details-marker]:hidden">
            {item.question}
            <ChevronDown
              className="h-5 w-5 shrink-0 text-muted transition-transform group-open:rotate-180 motion-reduce:transition-none"
              aria-hidden
            />
          </summary>
          <p className="pb-5 pr-8 text-base leading-relaxed text-muted">{item.answer}</p>
        </details>
      ))}
    </div>
  );
}

export function LinkGrid({
  links,
}: {
  links: Array<{ href: string; label: string; note?: string }>;
}) {
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {links.map((link) => (
        <li key={link.href}>
          <Link
            href={link.href}
            className="group flex h-full items-start justify-between gap-3 rounded-2xl border border-primary/8 bg-white p-4 transition-[border-color,box-shadow,transform] duration-200 hover:border-secondary/40 hover:shadow-lg hover:shadow-primary/5 motion-safe:hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
          >
            <span>
              <span className="font-semibold text-primary">{link.label}</span>
              {link.note ? (
                <span className="mt-1 block text-xs text-muted">{link.note}</span>
              ) : null}
            </span>
            <ArrowRight
              className="mt-1 h-4 w-4 shrink-0 text-secondary transition-transform motion-safe:group-hover:translate-x-0.5"
              aria-hidden
            />
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function AnswerFirst({ text }: { text: string }) {
  return (
    <p className="max-w-3xl rounded-2xl border-l-4 border-secondary bg-secondary/5 p-5 text-base leading-relaxed text-primary">
      {text}
    </p>
  );
}
