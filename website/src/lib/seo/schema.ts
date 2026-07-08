/**
 * JSON-LD structured data for SEO.
 * Organization, LocalBusiness, Service, FAQPage. Geographic service areas for discoverability.
 * Delivery-focused so Google understands courier, same-day, and recurring local delivery.
 */

import { siteConfig } from "./config";

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

/** Simple area name list for fallback / Service schema when only names are needed. */
export const SCHEMA_AREA_SERVED_NAMES = SCHEMA_SERVICE_AREAS.map((p) => p.name);

/** Delivery service types for LocalBusiness and Service (helps Google classify). */
export const SCHEMA_DELIVERY_SERVICE_TYPES = [
  "Courier service",
  "Same-day delivery",
  "Recurring delivery",
  "Local delivery",
  "Parcel delivery",
] as const;

/** Description for LocalBusiness schema: delivery-focused for rich results. */
const LOCAL_BUSINESS_DESCRIPTION =
  "Porterchain provides local courier and same-day delivery for merchants in the GTA, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, and Ontario. Recurring and on-demand parcel delivery with tracking.";

export type OrganizationSchema = {
  "@context": "https://schema.org";
  "@type": "Organization";
  name: string;
  url: string;
  description?: string;
  logo?: string;
};

export type LocalBusinessSchema = {
  "@context": "https://schema.org";
  "@type": "LocalBusiness";
  name: string;
  url: string;
  description?: string;
  areaServed: SchemaPlace[] | readonly SchemaPlace[];
  serviceType?: string | string[];
};

export type ServiceSchema = {
  "@context": "https://schema.org";
  "@type": "Service";
  name: string;
  description?: string;
  provider?: { "@type": "Organization"; name: string; url: string };
  areaServed?: string[] | SchemaPlace[] | { "@type": string; name?: string }[];
  serviceType?: string | string[];
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
  author: { "@type": "Organization"; name: string; url: string };
  publisher?: {
    "@type": "Organization";
    name: string;
    url: string;
    logo?: { "@type": "ImageObject"; url: string };
  };
  datePublished?: string;
  dateModified?: string;
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

/**
 * Organization schema (site-wide).
 */
export function buildOrganizationSchema(options?: { baseUrl?: string }): OrganizationSchema {
  const base = (options?.baseUrl ?? BASE).replace(/\/$/, "");
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: siteConfig.name,
    url: base,
    description: siteConfig.description,
    logo: `${base}/icon.svg`,
  };
}

/**
 * LocalBusiness schema with geographic service areas (site-wide).
 * Defines delivery service types and areaServed so Google understands local courier coverage.
 */
export function buildLocalBusinessSchema(options?: { baseUrl?: string }): LocalBusinessSchema {
  const base = (options?.baseUrl ?? BASE).replace(/\/$/, "");
  return {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    name: siteConfig.name,
    url: base,
    description: LOCAL_BUSINESS_DESCRIPTION,
    areaServed: [...SCHEMA_SERVICE_AREAS],
    serviceType: [...SCHEMA_DELIVERY_SERVICE_TYPES],
  };
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
}): ServiceSchema {
  const base = (params.baseUrl ?? BASE).replace(/\/$/, "");
  const areaServed = params.areaServed?.length
    ? params.areaServed.map((name) => ({ "@type": "Place" as const, name }))
    : [...SCHEMA_SERVICE_AREAS];
  return {
    "@context": "https://schema.org",
    "@type": "Service",
    name: params.name,
    description: params.description,
    provider: { "@type": "Organization", name: siteConfig.name, url: base },
    areaServed,
    serviceType: "Courier service",
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
}): ArticleSchema {
  const base = (params.baseUrl ?? BASE).replace(/\/$/, "");
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: params.headline,
    description: params.description,
    author: { "@type": "Organization", name: siteConfig.name, url: base },
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
