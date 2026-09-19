import { raviContact } from "./ravi-contact";

function escapeVCard(value: string): string {
  return value
    .replace(/\\/g, "\\\\")
    .replace(/\r\n/g, "\\n")
    .replace(/\n/g, "\\n")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,");
}

function foldLine(line: string): string {
  const max = 75;
  if (line.length <= max) return line;
  const parts: string[] = [line.slice(0, max)];
  let rest = line.slice(max);
  while (rest.length > 0) {
    parts.push(` ${rest.slice(0, max - 1)}`);
    rest = rest.slice(max - 1);
  }
  return parts.join("\r\n");
}

/** vCard 3.0 for Add to Contacts on iPhone and Android. */
export function buildRaviVCard(): string {
  const [firstName, ...rest] = raviContact.name.trim().split(/\s+/);
  const lastName = rest.join(" ") || firstName;
  const lines = [
    "BEGIN:VCARD",
    "VERSION:3.0",
    `N:${escapeVCard(lastName)};${escapeVCard(firstName)};;;`,
    `FN:${escapeVCard(raviContact.name)}`,
    `ORG:${escapeVCard(raviContact.company)}`,
    `TITLE:${escapeVCard(raviContact.role)}`,
    `TEL;TYPE=CELL,VOICE:${raviContact.phoneE164}`,
    `EMAIL;TYPE=INTERNET:${raviContact.email}`,
    `URL:${raviContact.links.website}`,
    `URL:${raviContact.links.linkedin}`,
    `URL:${raviContact.links.instagram}`,
    `NOTE:${escapeVCard(`${raviContact.tagline} · ${raviContact.links.website}/ravi`)}`,
    `UID:ravi-chauhan-porterchain@porterchain.com`,
    "END:VCARD",
  ];
  return `${lines.map(foldLine).join("\r\n")}\r\n`;
}

export const raviVCardFilename = "Ravi-Chauhan-Porterchain.vcf";
