import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";

/** Server-only building blocks for the /delivery pages (no client JS). */

export function DeliverySection({
  title,
  children,
  tone = "white",
  id,
}: {
  title?: string;
  children: React.ReactNode;
  tone?: "white" | "soft";
  id?: string;
}) {
  return (
    <section
      id={id}
      className={tone === "soft" ? "bg-slate-50 py-12 sm:py-16" : "bg-white py-12 sm:py-16"}
    >
      <Container>
        {title ? (
          <h2 className="text-2xl font-semibold text-primary sm:text-3xl">{title}</h2>
        ) : null}
        <div className={title ? "mt-6" : undefined}>{children}</div>
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
          className="rounded-xl border border-primary/10 bg-white p-4 text-sm leading-relaxed text-primary/90"
        >
          {item}
        </li>
      ))}
    </ul>
  );
}

/** FAQ answers are in the HTML (not collapsed behind JS) for search and AI crawlers. */
export function FaqList({ items }: { items: Array<{ question: string; answer: string }> }) {
  return (
    <div className="divide-y divide-primary/10 rounded-2xl border border-primary/10 bg-white">
      {items.map((item) => (
        <details key={item.question} className="group p-5" open>
          <summary className="cursor-pointer list-none text-base font-semibold text-primary">
            {item.question}
          </summary>
          <p className="mt-2 text-sm leading-relaxed text-muted">{item.answer}</p>
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
            className="block rounded-xl border border-primary/10 bg-white p-4 transition-colors hover:border-secondary/40"
          >
            <span className="font-semibold text-primary">{link.label}</span>
            {link.note ? <span className="mt-1 block text-xs text-muted">{link.note}</span> : null}
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
