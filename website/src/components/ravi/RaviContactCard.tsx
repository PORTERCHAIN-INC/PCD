import Link from "next/link";
import { raviContact, raviContactChannels } from "@/lib/ravi-contact";
import { RaviChannelIcon } from "./RaviChannelIcon";

function SaveContactIcon() {
  return (
    <svg width={20} height={20} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 12c2.2 0 4-1.8 4-4s-1.8-4-4-4-4 1.8-4 4 1.8 4 4 4zm0 2c-2.7 0-8 1.3-8 4v2h16v-2c0-2.7-5.3-4-8-4z" />
      <path d="M19 13v2h3v3h2v-3h3v-2h-3v-3h-2v3h-3z" opacity="0.95" />
    </svg>
  );
}

export function RaviContactCard() {
  const initials = raviContact.name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="ravi-page">
      <div className="ravi-page__glow ravi-page__glow--one" aria-hidden />
      <div className="ravi-page__glow ravi-page__glow--two" aria-hidden />

      <main className="ravi-card">
        <header className="ravi-card__header">
          <p className="ravi-card__brand">{raviContact.company}</p>
          <p className="ravi-card__tagline">{raviContact.tagline}</p>
        </header>

        <div className="ravi-card__profile">
          <div className="ravi-card__avatar" aria-hidden>
            {initials}
          </div>
          <h1 className="ravi-card__name">{raviContact.nameDisplay}</h1>
          <p className="ravi-card__role">{raviContact.role}</p>
          <p className="ravi-card__company">{raviContact.company}</p>
          <a
            href="/ravi/contact.vcf"
            className="ravi-card__save"
            download="Ravi-Chauhan-Porterchain.vcf"
          >
            <span className="ravi-card__save-icon" aria-hidden>
              <SaveContactIcon />
            </span>
            Save to contacts
          </a>
        </div>

        <nav className="ravi-card__links" aria-label="Contact and social links">
          <ul>
            {raviContactChannels.map((channel) => (
              <li key={channel.id}>
                <a
                  href={channel.href}
                  className="ravi-card__link"
                  {...(channel.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                >
                  <span className="ravi-card__link-icon" aria-hidden>
                    <RaviChannelIcon channel={channel.id} />
                  </span>
                  <span className="ravi-card__link-text">
                    <span className="ravi-card__link-label">{channel.label}</span>
                    {channel.detail ? (
                      <span className="ravi-card__link-detail">{channel.detail}</span>
                    ) : null}
                  </span>
                  <span className="ravi-card__link-arrow" aria-hidden>
                    →
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <footer className="ravi-card__footer">
          <Link href={raviContact.links.merchantInquiry} className="ravi-card__footer-cta">
            Merchant setup
          </Link>
          <Link href={raviContact.links.website} className="ravi-card__footer-link">
            porterchain.com
          </Link>
        </footer>
      </main>
    </div>
  );
}
