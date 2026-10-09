/**
 * JSON-LD structured data for SEO.
 * Organization, LocalBusiness, Service, FAQPage. Geographic service areas for discoverability.
 * Delivery-focused so Google understands courier, same-day, and recurring local delivery.
 */

import { siteConfig } from "./config";
import { buildGoogleSameAsLinks, PUBLIC_CONTACT_PHONE_E164 } from "@/lib/google-business";
import { getHyperlocalGeo, type HyperlocalGeo } from "./hyperlocal-geo";

const BASE = siteConfig.baseUrl.replace(/\/$/, "");

/** Place type for schema.org areaServed (Ontario, Canada). */
type SchemaPlace = {
  "@type": "Place";
  name: string;
  address?: {
    "@type": "PostalAddress";
    addressLocality?: string;
    addressRegion?: string;
    addressCountry?: string;
  };
};

/**
 * Geographic service areas for schema.org areaServed.
 * Defines delivery coverage so Google understands where we operate.
 */
export const SCHEMA_SERVICE_AREAS: readonly SchemaPlace[] = [
  {
    "@type": "Place",
    name: "Greater Toronto Area",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Toronto",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Toronto",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Toronto",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Mississauga",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Mississauga",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Brampton",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Brampton",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Vaughan",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Vaughan",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Markham",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Markham",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Oakville",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Oakville",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Burlington",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Burlington",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Oshawa",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Oshawa",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Kitchener-Waterloo",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Kitchener",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "London",
    address: {
      "@type": "PostalAddress",
      addressLocality: "London",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "St. Catharines",
    address: {
      "@type": "PostalAddress",
      addressLocality: "St. Catharines",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Niagara",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Niagara Falls",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Cambridge",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Cambridge",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Guelph",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Guelph",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Hamilton",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Hamilton",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Ajax",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Ajax",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
  {
    "@type": "Place",
    name: "Pickering",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Pickering",
      addressRegion: "ON",
      addressCountry: "CA",
    },
  },
];

/** Delivery service types for LocalBusiness and Service (helps Google classify). */
export const SCHEMA_DELIVERY_SERVICE_TYPES = [
  "Courier service",
  "Same-day delivery",
  "Recurring delivery",
  "Local delivery",
  "Parcel delivery",
] as const;

/** Description for Organization schema — capacity network (Lane A). */
const ORGANIZATION_DESCRIPTION =
  "Porterchain is a transportation capacity network for Ontario businesses — reliable vehicle-and-driver capacity orchestrated through intelligent operations software.";

/** Description for LocalBusiness schema — delivery capacity. */
const LOCAL_BUSINESS_DESCRIPTION =
  "Porterchain provides transportation capacity for Ontario B2B businesses — professional drivers and commercial vehicles with tracking and proof of delivery.";

export type SoftwareApplicationSchema = {
  "@context": "https://schema.org";
  "@type": "SoftwareApplication";
  name: string;
  applicationCategory: string;
  operatingSystem: string;
  description: string;
  url: string;
  offers?: {
    "@type": "Offer";
    priceCurrency: string;
    description: string;
  };
  provider: { "@type": "Organization"; name: string; url: string };
};

export type OrganizationSchema = {
  "@context": "https://schema.org";
  "@type": "Organization";
  "@id"?: string;
  name: string;
  url: string;
  slogan?: string;
  description?: string;
  logo?: string;
  knowsAbout?: string[];
  sameAs?: string[];
};

export type WebSiteSchema = {
  "@context": "https://schema.org";
  "@type": "WebSite";
  "@id": string;
  name: string;
  url: string;
  publisher: { "@id": string };
  inLanguage?: string[];
};

export type BreadcrumbListSchema = {
  "@context": "https://schema.org";
  "@type": "BreadcrumbList";
  itemListElement: Array<{
    "@type": "ListItem";
    position: number;
    name: string;
    item?: string;
  }>;
};

export type LocalBusinessSchema = {
  "@context": "https://schema.org";
  "@type": ["LocalBusiness", "DeliveryService"];
  "@id"?: string;
  name: string;
  url: string;
  description?: string;
  telephone?: string;
  image?: string;
  sameAs?: string[];
  hasMap?: string;
  areaServed: SchemaPlace[] | readonly SchemaPlace[];
  serviceType?: string | string[];
  address?: {
    "@type": "PostalAddress";
    addressLocality: string;
    addressRegion: string;
    addressCountry: string;
  };
  openingHoursSpecification?: Array<{
    "@type": "OpeningHoursSpecification";
    dayOfWeek: string[];
    opens: string;
    closes: string;
  }>;
};

export type ServiceSchema = {
  "@context": "https://schema.org";
  "@type": "Service";
  "@id"?: string;
  name: string;
  description?: string;
  provider?: { "@type": "Organization"; name: string; url: string } | { "@id": string };
  areaServed?: HyperlocalPlace[] | SchemaPlace[] | string[] | { "@type": string; name?: string }[];
  serviceType?: string | string[];
};

type HyperlocalPlace = {
  "@type": "Place";
  name: string;
  geo?: { "@type": "GeoCoordinates"; latitude: number; longitude: number };
  address?: {
    "@type": "PostalAddress";
    addressLocality: string;
    addressRegion: string;
    addressCountry: string;
    postalCode?: string | string[];
  };
};

export type FAQPageSchema = {
  "@context": "https://schema.org";
  "@type": "FAQPage";
  mainEntity: Array<{
    "@type": "Question";
    name: string;
    acceptedAnswer: { "@type": "Answer"; text: string };
  }>;
};

/** Article schema for success stories and content pages. */
export type ArticleSchema = {
  "@context": "https://schema.org";
  "@type": "Article";
  headline: string;
  description?: string;
  url?: string;
  author:
    | { "@type": "Organization"; name: string; url: string }
    | {
        "@type": "Person";
        name: string;
        jobTitle?: string;
        worksFor?: { "@type": "Organization"; name: string; url: string };
      };
  publisher?: {
    "@type": "Organization";
    name: string;
    url: string;
    logo?: { "@type": "ImageObject"; url: string };
  };
  datePublished?: string;
  dateModified?: string;
};

/** WebPage with speakable CSS selectors for voice / AI search. */
export type SpeakableWebPageSchema = {
  "@context": "https://schema.org";
  "@type": "WebPage";
  name: string;
  url: string;
  speakable: {
    "@type": "SpeakableSpecification";
    cssSelector: string[];
  };
};

/** Review schema for testimonial quotes (trust signal). */
export type ReviewSchema = {
  "@context": "https://schema.org";
  "@type": "Review";
  itemReviewed?: { "@type": "Service"; name: string };
  author?: { "@type": "Organization"; name: string } | { "@type": "Person"; name: string };
  reviewBody: string;
  reviewRating?: { "@type": "Rating"; ratingValue: number; bestRating?: number };
};

export function organizationId(baseUrl?: string): string {
  return `${(baseUrl ?? BASE).replace(/\/$/, "")}/#organization`;
}

export function websiteId(baseUrl?: string): string {
  return `${(baseUrl ?? BASE).replace(/\/$/, "")}/#website`;
}

export function serviceEntityId(baseUrl?: string): string {
  return `${(baseUrl ?? BASE).replace(/\/$/, "")}/#service`;
}

/**
 * Organization schema (site-wide).
 */
export function buildOrganizationSchema(options?: { baseUrl?: string }): OrganizationSchema {
  const base = (options?.baseUrl ?? BASE).replace(/\/$/, "");
  const sameAs = buildGoogleSameAsLinks();
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": organizationId(base),
    name: siteConfig.name,
    url: base,
    slogan: siteConfig.tagline,
    description: ORGANIZATION_DESCRIPTION,
    logo: `${base}/icon.svg`,
    knowsAbout: [
      "B2B delivery",
      "Same-day delivery",
      "Fleet overflow capacity",
      "Construction jobsite delivery",
      "Wholesale distribution delivery",
      "Pharmacy courier delivery",
      "Proof of delivery",
    ],
    ...(sameAs.length > 0 ? { sameAs } : {}),
  };
}

export function buildWebSiteSchema(options?: { baseUrl?: string }): WebSiteSchema {
  const base = (options?.baseUrl ?? BASE).replace(/\/$/, "");
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": websiteId(base),
    name: siteConfig.name,
    url: base,
    publisher: { "@id": organizationId(base) },
    inLanguage: ["en-CA", "fr-CA"],
  };
}

export function buildBreadcrumbListSchema(
  items: Array<{ name: string; url?: string }>,
  options?: { baseUrl?: string }
): BreadcrumbListSchema {
  const base = (options?.baseUrl ?? BASE).replace(/\/$/, "");
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      ...(item.url ? { item: item.url.startsWith("http") ? item.url : `${base}${item.url}` } : {}),
    })),
  };
}

function buildHyperlocalPlace(
  geo: HyperlocalGeo,
  label?: string,
  postalCodes?: string[]
): HyperlocalPlace {
  return {
    "@type": "Place",
    name: label ?? `${geo.locality}, ${geo.region}`,
    geo: {
      "@type": "GeoCoordinates",
      latitude: geo.latitude,
      longitude: geo.longitude,
    },
    address: {
      "@type": "PostalAddress",
      addressLocality: geo.locality,
      addressRegion: geo.region,
      addressCountry: "CA",
      ...(postalCodes?.length
        ? { postalCode: postalCodes.length === 1 ? postalCodes[0] : postalCodes }
        : {}),
    },
  };
}

/**
 * LocalBusiness schema with geographic service areas (contact / GBP pages only).
 * Defines delivery service types and areaServed so Google understands local courier coverage.
 */
export function buildLocalBusinessSchema(options?: { baseUrl?: string }): LocalBusinessSchema {
  const base = (options?.baseUrl ?? BASE).replace(/\/$/, "");
  const sameAs = buildGoogleSameAsLinks();
  const schema: LocalBusinessSchema = {
    "@context": "https://schema.org",
    "@type": ["LocalBusiness", "DeliveryService"],
    "@id": `${base}/#localbusiness`,
    name: siteConfig.name,
    url: base,
    description: LOCAL_BUSINESS_DESCRIPTION,
    telephone: PUBLIC_CONTACT_PHONE_E164,
    image: `${base}/icon.svg`,
    areaServed: [...SCHEMA_SERVICE_AREAS],
    serviceType: [...SCHEMA_DELIVERY_SERVICE_TYPES],
    address: {
      "@type": "PostalAddress",
      addressLocality: "Toronto",
      addressRegion: "ON",
      addressCountry: "CA",
    },
    openingHoursSpecification: [
      {
        "@type": "OpeningHoursSpecification",
        dayOfWeek: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        opens: "08:00",
        closes: "18:00",
      },
    ],
  };
  if (sameAs.length > 0) {
    schema.sameAs = sameAs;
    const profileUrl = sameAs.find(
      (url) =>
        url.includes("google.com/maps") || url.includes("g.page") || url.includes("goo.gl/maps")
    );
    if (profileUrl) {
      schema.hasMap = profileUrl;
    }
  }
  return schema;
}

/**
 * Service schema for a specific page (e.g. local delivery, city-industry).
 * Use page-specific name/description/areaServed; provider and serviceType reinforce delivery.
 */
export function buildServiceSchema(params: {
  name: string;
  description?: string;
  areaServed?: string[];
  baseUrl?: string;
  /** service-area or city URL slug for hyperlocal geo Place */
  geoSlug?: string;
  regionLabel?: string;
  /** FSA / postal prefixes for near-me schema on the same city URL (not zip landings) */
  postalCodes?: string[];
}): ServiceSchema {
  const base = (params.baseUrl ?? BASE).replace(/\/$/, "");
  let areaServed: ServiceSchema["areaServed"];
  if (params.geoSlug) {
    const geo = getHyperlocalGeo(params.geoSlug);
    areaServed = geo
      ? [
          buildHyperlocalPlace(
            geo,
            params.regionLabel ?? `${geo.locality}, Ontario`,
            params.postalCodes
          ),
        ]
      : [...SCHEMA_SERVICE_AREAS];
  } else if (params.areaServed?.length) {
    areaServed = params.areaServed.map((name) => ({ "@type": "Place" as const, name }));
  } else {
    areaServed = [...SCHEMA_SERVICE_AREAS];
  }
  return {
    "@context": "https://schema.org",
    "@type": "Service",
    "@id": serviceEntityId(base),
    name: params.name,
    description: params.description,
    provider: { "@id": organizationId(base) },
    areaServed,
    serviceType: [...SCHEMA_DELIVERY_SERVICE_TYPES],
  };
}

export type HowToSchema = {
  "@context": "https://schema.org";
  "@type": "HowTo";
  name: string;
  description?: string;
  step: Array<{ "@type": "HowToStep"; name: string; text: string; position: number }>;
};

export type CorporationSchema = {
  "@context": "https://schema.org";
  "@type": "Corporation";
  "@id": string;
  name: string;
  url: string;
  description?: string;
  logo?: string;
  parentOrganization?: { "@id": string };
};

export type DatasetSchema = {
  "@context": "https://schema.org";
  "@type": "Dataset";
  name: string;
  description?: string;
  creator?: { "@id": string };
  license?: string;
  isAccessibleForFree?: boolean;
  keywords?: string[];
};

/** HowTo for operational guides with ordered steps. */
export function buildHowToSchema(params: {
  name: string;
  description?: string;
  steps: Array<{ name: string; text: string }>;
}): HowToSchema | null {
  const steps = params.steps.filter((s) => s.name?.trim() && s.text?.trim());
  if (!steps.length) return null;
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: params.name,
    description: params.description,
    step: steps.map((s, i) => ({
      "@type": "HowToStep",
      position: i + 1,
      name: s.name,
      text: s.text,
    })),
  };
}

/** Corporation entity — use when legal entity differs from brand Organization. */
export function buildCorporationSchema(options?: {
  baseUrl?: string;
  legalName?: string;
}): CorporationSchema {
  const base = (options?.baseUrl ?? BASE).replace(/\/$/, "");
  return {
    "@context": "https://schema.org",
    "@type": "Corporation",
    "@id": `${base}/#corporation`,
    name: options?.legalName ?? siteConfig.name,
    url: base,
    description: ORGANIZATION_DESCRIPTION,
    logo: `${base}/icon.svg`,
    parentOrganization: { "@id": organizationId(base) },
  };
}

/** Dataset for research/intelligence reports once published (keep draft reports unpublished). */
export function buildDatasetSchema(params: {
  name: string;
  description?: string;
  keywords?: string[];
  baseUrl?: string;
  license?: string;
}): DatasetSchema {
  const base = (params.baseUrl ?? BASE).replace(/\/$/, "");
  return {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: params.name,
    description: params.description,
    creator: { "@id": organizationId(base) },
    isAccessibleForFree: true,
    keywords: params.keywords,
    license: params.license,
  };
}

/**
 * Article schema for success stories and content (SEO).
 */
export function buildArticleSchema(params: {
  headline: string;
  description?: string;
  datePublished?: string;
  dateModified?: string;
  baseUrl?: string;
  url?: string;
  /** Person author for E-E-A-T on guides; defaults to Organization. */
  authorPerson?: { name: string; jobTitle?: string };
}): ArticleSchema {
  const base = (params.baseUrl ?? BASE).replace(/\/$/, "");
  const author = params.authorPerson
    ? {
        "@type": "Person" as const,
        name: params.authorPerson.name,
        jobTitle: params.authorPerson.jobTitle,
        worksFor: { "@type": "Organization" as const, name: siteConfig.name, url: base },
      }
    : { "@type": "Organization" as const, name: siteConfig.name, url: base };
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: params.headline,
    description: params.description,
    url: params.url,
    author,
    publisher: {
      "@type": "Organization",
      name: siteConfig.name,
      url: base,
      logo: { "@type": "ImageObject", url: `${base}/icon.svg` },
    },
    datePublished: params.datePublished,
    dateModified: params.dateModified,
  };
}

/**
 * WebPage schema with speakable FAQ selectors (voice / AI search).
 */
export function buildSpeakableWebPageSchema(params: {
  name: string;
  url: string;
  cssSelectors?: string[];
}): SpeakableWebPageSchema {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: params.name,
    url: params.url,
    speakable: {
      "@type": "SpeakableSpecification",
      cssSelector: params.cssSelectors ?? [".speakable-faq-q", ".speakable-faq-a"],
    },
  };
}

/**
 * Review schema for success story quote (trust signal).
 */
export function buildReviewSchema(params: {
  reviewBody: string;
  authorName?: string;
  serviceName?: string;
}): ReviewSchema {
  return {
    "@context": "https://schema.org",
    "@type": "Review",
    itemReviewed: params.serviceName ? { "@type": "Service", name: params.serviceName } : undefined,
    author: params.authorName ? { "@type": "Person", name: params.authorName } : undefined,
    reviewBody: params.reviewBody,
  };
}

/**
 * FAQPage schema for pages with FAQ sections.
 */
export function buildFAQPageSchema(
  items: Array<{ question: string; answer: string }>
): FAQPageSchema | null {
  const filtered = items.filter((i) => i.question?.trim() && i.answer?.trim());
  if (!filtered.length) return null;
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: filtered.map((item) => ({
      "@type": "Question" as const,
      name: item.question,
      acceptedAnswer: { "@type": "Answer" as const, text: item.answer },
    })),
  };
}
