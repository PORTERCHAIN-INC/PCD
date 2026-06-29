import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import {
  footerNavigation,
  footerSectionOrder,
  type FooterSectionId,
} from "@/data/footer-navigation";

export type FooterVariant = "corporate" | "booking" | "business";

interface OrganizedFooterLinksProps {
  getSectionTitle: (section: FooterSectionId | "legal") => string;
  getLinkLabel: (section: FooterSectionId, id: string) => string;
  getLegalLabel?: (id: string) => string;
  className?: string;
  columnClassName?: string;
  linkClassName?: string;
  titleClassName?: string;
}

export function OrganizedFooterLinks({
  getSectionTitle,
  getLinkLabel,
  getLegalLabel,
  className,
  columnClassName,
  linkClassName,
  titleClassName,
}: OrganizedFooterLinksProps) {
  const sections = footerSectionOrder;

  return (
    <div className={cn("grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-8 lg:gap-6", className)}>
      {sections.map((section) => (
        <FooterColumn
          key={section}
          title={getSectionTitle(section)}
          links={footerNavigation[section].map((link) => ({
            href: link.href,
            label: getLinkLabel(section, link.id),
          }))}
          columnClassName={columnClassName}
          linkClassName={linkClassName}
          titleClassName={titleClassName}
        />
      ))}
      {getLegalLabel && (
        <FooterColumn
          title={getSectionTitle("legal")}
          links={[
            { href: "#", label: getLegalLabel("privacy") },
            { href: "#", label: getLegalLabel("terms") },
            { href: "#", label: getLegalLabel("cookies") },
          ]}
          columnClassName={columnClassName}
          linkClassName={linkClassName}
          titleClassName={titleClassName}
          staticLinks
        />
      )}
    </div>
  );
}

function FooterColumn({
  title,
  links,
  columnClassName,
  linkClassName,
  titleClassName,
  staticLinks,
}: {
  title: string;
  links: { href: string; label: string }[];
  columnClassName?: string;
  linkClassName?: string;
  titleClassName?: string;
  staticLinks?: boolean;
}) {
  return (
    <div className={columnClassName}>
      <h3 className={titleClassName}>{title}</h3>
      <ul className="mt-3 space-y-2.5">
        {links.map((link) => (
          <li key={`${link.href}-${link.label}`}>
            {staticLinks ? (
              <span className={linkClassName}>{link.label}</span>
            ) : (
              <Link href={link.href} className={linkClassName}>
                {link.label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
