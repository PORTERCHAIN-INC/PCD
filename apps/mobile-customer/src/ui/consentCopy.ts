export type ConsentSection = {
  title: string;
  paragraphs: string[];
  list?: string[];
};

export type ConsentDocument = {
  title: string;
  updated: string;
  intro: string;
  sections: ConsentSection[];
};

/** Published site copy from website/messages/legal-en.json (29 Jun 2026). */
export const TERMS_OF_SERVICE: ConsentDocument = {
  title: "Terms of Service",
  updated: "Last updated: June 29, 2026",
  intro:
    'These Terms of Service ("Terms") govern your use of Porterchain Inc.\'s transportation capacity services, website, shipment coordination tools, APIs (where enabled), and dedicated delivery programs. By requesting a quote, booking capacity, or using our services, you agree to these Terms.',
  sections: [
    {
      title: "Services",
      paragraphs: [
        "Porterchain provides commercial logistics services including same-day and scheduled delivery, route optimization, live tracking, and proof of delivery across the Greater Toronto Area and Ontario.",
        "Porterchain is a structured logistics operator — not an ad-hoc driver marketplace. Services are subject to vehicle availability, operational capacity, weather, traffic, and compliance requirements.",
      ],
    },
    {
      title: "Bookings and quotes",
      paragraphs: [
        "Quotes displayed are estimates based on the information you provide. Final pricing may change if shipment details, access requirements, wait times, or route conditions differ from the original quote.",
        "You are responsible for providing accurate pickup and delivery addresses, contact information, shipment dimensions, weight, and handling instructions. Incorrect information may result in delays, additional charges, or refusal of service.",
      ],
    },
    {
      title: "Prohibited goods and conduct",
      paragraphs: [
        "You may not use Porterchain to transport illegal goods, hazardous materials without prior written approval, items that violate carrier insurance terms, or shipments that endanger drivers or the public.",
        "We reserve the right to refuse, hold, or return any shipment that violates these Terms or applicable law.",
      ],
    },
    {
      title: "Liability and claims",
      paragraphs: [
        "Porterchain maintains commercial insurance and WSIB registration for its operations. Liability for loss or damage is limited as set out in your quote, merchant agreement, or applicable tariff, except where prohibited by law.",
        "Claims for loss, damage, or service issues must be reported promptly with shipment references and supporting documentation. Contact ops@porterchain.com for claims assistance.",
      ],
    },
    {
      title: "Cancellations and refunds",
      paragraphs: [
        "Cancellations before dispatch may be eligible for a full or partial refund depending on timing and operational costs incurred. Cancellations after a driver is dispatched may incur fees.",
        "Retail payments processed through Stripe are subject to the refund policies communicated at checkout.",
      ],
    },
    {
      title: "Governing law",
      paragraphs: [
        "These Terms are governed by the laws of the Province of Ontario and the federal laws of Canada applicable therein. Disputes shall be resolved in the courts of Ontario, unless otherwise agreed in a merchant agreement.",
        "Questions about these Terms: driver@porterchain.com · +1 (647) 619-7951",
      ],
    },
  ],
};

/** Published site copy from website/messages/legal-en.json (29 Jun 2026). */
export const PRIVACY_NOTICE: ConsentDocument = {
  title: "Privacy Notice",
  updated: "Last updated: June 29, 2026",
  intro:
    'Porterchain Inc. ("Porterchain", "we", "us") provides commercial delivery and transportation capacity services for businesses in Ontario, using proprietary software to orchestrate professional drivers, vehicles, and logistics operations. This Privacy Policy explains how we collect, use, disclose, and protect personal information when you use our website, request capacity, track shipments, or interact with our support channels.',
  sections: [
    {
      title: "Information we collect",
      paragraphs: [
        "We collect information necessary to quote, dispatch, track, and complete deliveries, and to operate merchant and driver partner accounts.",
      ],
      list: [
        "Contact details: name, email, phone number, and company information",
        "Addresses: pickup and delivery locations for routing and proof of delivery",
        "Shipment details: weight, dimensions, photos, references, and special instructions",
        "Payment information: billing details processed through Stripe (card data is handled by Stripe, not stored by Porterchain)",
        "Account and compliance data: merchant onboarding documents, tax identifiers, and insurance details",
        "Location data: GPS coordinates for driver tracking and proof of delivery",
        "Communications: support inquiries, on-site logistics chat messages, WhatsApp messages, and email correspondence",
        "Technical data: cookies and session identifiers from authentication and third-party services",
      ],
    },
    {
      title: "How we use your information",
      paragraphs: [
        "We use personal information to operate our logistics services, comply with legal obligations, and improve the customer experience.",
      ],
      list: [
        "Provide quotes, bookings, dispatch, tracking, and proof of delivery",
        "Process payments, invoices, and merchant billing",
        "Verify merchant accounts and maintain compliance records",
        "Respond to support requests and operational emergencies",
        "Send service-related notifications (booking confirmations, delivery updates, billing notices)",
        "Improve routing, capacity planning, and platform reliability",
        "Detect fraud, abuse, and security incidents",
      ],
    },
    {
      title: "Third-party service providers",
      paragraphs: [
        "We share information with trusted processors only as needed to deliver our services. These providers are contractually required to protect your data.",
      ],
      list: [
        "Clerk — merchant and customer authentication",
        "Stripe — payment processing",
        "Google Maps — address autocomplete and mapping",
        "Zoho Mail — transactional email delivery",
        "PorterChain API — dispatch, routing, and shipment operations",
      ],
    },
    {
      title: "Retention and security",
      paragraphs: [
        "We retain personal information for as long as needed to fulfill deliveries, meet legal and tax requirements, resolve disputes, and enforce agreements. Shipment and billing records may be retained for several years as required by commercial and regulatory practice.",
        "We implement administrative, technical, and operational safeguards including access controls, encrypted connections, and documented compliance procedures. No method of transmission over the internet is 100% secure; we continuously work to protect your information.",
      ],
    },
    {
      title: "Your rights (Canada)",
      paragraphs: [
        "Under Canada's Personal Information Protection and Electronic Documents Act (PIPEDA) and applicable provincial laws, you may request access to, correction of, or deletion of your personal information, subject to legal exceptions.",
        "To exercise your rights or ask questions about this policy, contact us using the details below. We will respond within a reasonable timeframe.",
      ],
    },
    {
      title: "Contact us",
      paragraphs: [
        "Privacy inquiries: driver@porterchain.com",
        "Operations: ops@porterchain.com",
        "Phone: +1 (647) 619-7951",
      ],
    },
  ],
};

/** The confirmation itself, plus the prohibited-goods rule already in the Terms of Service. */
export const DANGEROUS_GOODS: ConsentDocument = {
  title: "Dangerous goods",
  updated: "Declared in the Terms of Service · Last updated: June 29, 2026",
  intro: "Accepting confirms this shipment does not contain undeclared dangerous goods.",
  sections: [
    {
      title: "What you are confirming",
      paragraphs: [
        "Nothing in this shipment is a dangerous good that Porterchain has not already approved in writing. If you are unsure, do not book it as ordinary freight.",
      ],
    },
    {
      title: "Prohibited goods and conduct",
      paragraphs: [
        "You may not use Porterchain to transport illegal goods, hazardous materials without prior written approval, items that violate carrier insurance terms, or shipments that endanger drivers or the public.",
        "We reserve the right to refuse, hold, or return any shipment that violates these Terms or applicable law.",
      ],
    },
  ],
};
