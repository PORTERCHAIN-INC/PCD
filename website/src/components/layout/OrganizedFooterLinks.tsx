import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { customerPortalDashboardUrl, driverPortalUrl } from "@/data/portal-links";
import {
  footerNavigation,
  footerSectionOrder,
  type FooterSectionId,
} from "@/data/footer-navigation";

export type FooterVariant = "corporate" | "booking" | "business";

interface OrganizedFooterLinksProps {
  getSectionTitle: (section: FooterSectionId) => string;
  getLinkLabel: (section: FooterSectionId, id: string) => string;
  className?: string;
  columnClassName?: string;
  linkClassName?: string;
  titleClassName?: string;
}

export function OrganizedFooterLinks({
  getSectionTitle,
  getLinkLabel,
  className,
  columnClassName,
  linkClassName,
  titleClassName,
}: OrganizedFooterLinksProps) {
  return (
    <div className={cn("grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-6", className)}>
      {footerSectionOrder.map((section) => (
        <FooterColumn
          key={section}
          title={getSectionTitle(section)}
          links={footerNavigation[section].map((link) => ({
            href:
              link.href === "__CUSTOMER_PORTAL__"
                ? customerPortalDashboardUrl
                : link.href === "__DRIVER_PORTAL__"
                  ? driverPortalUrl
                  : link.href,
            label: getLinkLabel(section, link.id),
          }))}
          columnClassName={columnClassName}
          linkClassName={linkClassName}
          titleClassName={titleClassName}
        />
      ))}
    </div>
  );
}

function FooterColumn({
  title,
  links,
  columnClassName,
  linkClassName,
  titleClassName,
}: {
  title: string;
  links: { href: string; label: string }[];
  columnClassName?: string;
  linkClassName?: string;
  titleClassName?: string;
}) {
  return (
    <div className={columnClassName}>
      <h3 className={titleClassName}>{title}</h3>
      <ul className="mt-3 space-y-2.5">
        {links.map((link) => (
          <li key={`${link.href}-${link.label}`}>
            {link.href.startsWith("http") ? (
              <a href={link.href} className={linkClassName}>
                {link.label}
              </a>
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
