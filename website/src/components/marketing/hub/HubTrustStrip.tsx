"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ShieldCheck, Building2, FileCheck2 } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { easeOutQuart, fadeUp, springSnappy, staggerFast } from "@/lib/motion";

type Props = {
  eyebrow: string;
  title: string;
  body: string;
  companyLabel: string;
  trustLabel: string;
  contactLabel: string;
};

export default function HubTrustStrip({
  eyebrow,
  title,
  body,
  companyLabel,
  trustLabel,
  contactLabel,
}: Props) {
  const reduce = useReducedMotion();
  const links = [
    { href: "/company", label: companyLabel, icon: Building2 },
    { href: "/trust", label: trustLabel, icon: ShieldCheck },
    { href: "/contact", label: contactLabel, icon: FileCheck2 },
  ] as const;

  return (
    <section className="border-y border-primary/6 bg-white" aria-labelledby="hub-trust-heading">
      <Container className="py-10 sm:py-12">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, ease: easeOutQuart }}
        >
          <p className="text-xs font-bold uppercase tracking-wide text-secondary">{eyebrow}</p>
          <h2
            id="hub-trust-heading"
            className="mt-2 text-xl font-semibold tracking-tight text-primary sm:text-2xl"
          >
            {title}
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted">{body}</p>
        </motion.div>
        <motion.ul
          className="mt-6 grid gap-3 sm:grid-cols-3"
          initial={reduce ? false : "hidden"}
          whileInView="visible"
          viewport={{ once: true }}
          variants={staggerFast}
        >
          {links.map(({ href, label, icon: Icon }) => (
            <motion.li
              key={href}
              variants={fadeUp}
              transition={{ duration: 0.5, ease: easeOutQuart }}
            >
              <Link
                href={href}
                className="flex items-center gap-3 rounded-2xl border border-primary/8 bg-[#F4F6FA] px-4 py-3 text-sm font-medium text-primary transition-colors hover:border-secondary/30 hover:bg-white"
              >
                <motion.span
                  whileHover={reduce ? undefined : { rotate: -8, scale: 1.08 }}
                  transition={springSnappy}
                  className="inline-flex"
                >
                  <Icon className="h-4 w-4 text-secondary" aria-hidden />
                </motion.span>
                {label}
              </Link>
            </motion.li>
          ))}
        </motion.ul>
      </Container>
    </section>
  );
}
