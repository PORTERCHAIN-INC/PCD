/** Public contact card data for porterchain.com/ravi */

export const raviContact = {
  name: "Ravi Chauhan",
  nameDisplay: "RAVI CHAUHAN",
  role: "Head of Marketing",
  company: "Porterchain",
  tagline: "Cognition in Motion",
  phone: "+1 647 619 7951",
  phoneE164: "+16476197951",
  email: "sales@porterchain.com",
  links: {
    instagram: "https://www.instagram.com/porterchain/",
    facebook: "https://www.facebook.com/profile.php?id=61568324733884",
    linkedin: "https://www.linkedin.com/in/porter-chain-aa1951334/",
    youtube: "https://www.youtube.com/@PORTERCHAIN",
    whatsapp: "https://wa.me/16476197951",
    telegram: "https://t.me/+16476197951",
    phone: "tel:+16476197951",
    email: "mailto:sales@porterchain.com",
    website: "https://porterchain.com",
    merchantInquiry: "https://porterchain.com/en/business",
  },
} as const;

export type RaviContactChannel = {
  id: string;
  label: string;
  detail?: string;
  href: string;
  external?: boolean;
};

export const raviContactChannels: RaviContactChannel[] = [
  {
    id: "whatsapp",
    label: "WhatsApp",
    detail: raviContact.phone,
    href: raviContact.links.whatsapp,
    external: true,
  },
  {
    id: "phone",
    label: "Call or text",
    detail: raviContact.phone,
    href: raviContact.links.phone,
  },
  {
    id: "email",
    label: "Email",
    detail: raviContact.email,
    href: raviContact.links.email,
  },
  {
    id: "instagram",
    label: "Instagram",
    detail: "@porterchain",
    href: raviContact.links.instagram,
    external: true,
  },
  {
    id: "linkedin",
    label: "LinkedIn",
    detail: "Ravi Chauhan",
    href: raviContact.links.linkedin,
    external: true,
  },
  {
    id: "facebook",
    label: "Facebook",
    detail: "Porterchain",
    href: raviContact.links.facebook,
    external: true,
  },
  {
    id: "youtube",
    label: "YouTube",
    detail: "@PORTERCHAIN",
    href: raviContact.links.youtube,
    external: true,
  },
  {
    id: "telegram",
    label: "Telegram",
    detail: raviContact.phone,
    href: raviContact.links.telegram,
    external: true,
  },
];
