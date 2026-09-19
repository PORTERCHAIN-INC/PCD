/**
 * SEO content expansion data model — types and block schemas.
 * Used for city pages, city-industry pages, service pages, and campaign pages.
 * Structure is explicit and AI-generation-safe: clear field names, no ambiguous nesting.
 */

/** Stable identifier for content entities (e.g. for AI generation or CMS). */
export type ContentId = string;

/** URL-safe slug. Must match route param patterns (e.g. industry/[slug], service-areas/[slug]). */
export type Slug = string;

/** Message key used in i18n (e.g. nicheLanding.coffeeRoasters, serviceAreaLanding.toronto). CamelCase. */
export type MessageKey = string;

/** Locale code. Aligns with config.Locale. */
export type LocaleCode = string;

/** Market code. Aligns with config.Market. */
export type MarketCode = string;

// ——— Meta & SEO ———

export type MetaBlock = {
  title: string;
  description?: string;
};

// ——— Section blocks (mirror message shapes for type safety) ———

export type HeroBlock = {
  title: string;
  subtitle?: string;
};

export type PainPointsBlock = {
  title: string;
  item1: string;
  item2: string;
  item3: string;
};

export type SolutionBlock = {
  title: string;
  description: string;
  bullet1?: string;
  bullet2?: string;
  bullet3?: string;
};

export type WorkflowStep = {
  title: string;
  description: string;
};

export type WorkflowBlock = {
  title: string;
  description?: string;
  step1Title: string;
  step1Description: string;
  step2Title: string;
  step2Description: string;
  step3Title: string;
  step3Description: string;
};

export type CoverageBlock = {
  title: string;
  description?: string;
};

export type IndustriesBlock = {
  title: string;
  description?: string;
};

// ——— FAQ variants ———

export type FAQItem = {
  question: string;
  answer: string;
};

export type FAQBlock = {
  title: string;
  items: FAQItem[];
};

/** FAQ variant key: which context (default, industry, service-area, campaign). Used to select or generate copy. */
export type FAQVariantKey = string;

// ——— CTA variants ———

export type CTABlock = {
  title: string;
  description?: string;
  primary: string;
  secondary: string;
};

/** CTA variant key. Used to select or generate copy. */
export type CTAVariantKey = string;

// ——— Onboarding messaging ———

export type OnboardingStep = {
  title: string;
  description: string;
};

export type OnboardingBlock = {
  title: string;
  description: string;
  steps: OnboardingStep[];
};

/** Onboarding variant key. Used to select or generate copy. */
export type OnboardingVariantKey = string;

// ——— Inquiry (form / wizard) ———

export type InquiryBlock = {
  heading: string;
  subheadline?: string;
};

// ——— Entity configs (identity + optional generation hints) ———

/** Hints for AI-assisted content generation. Keep instructions short and deterministic. */
export type GenerationHints = {
  /** Keywords to include in meta and headings (e.g. "Toronto", "GTA", "recurring delivery"). */
  keywords?: string[];
  /** Audience or use case (e.g. "coffee roasters", "pharmacy", "B2B"). */
  audience?: string[];
  /** Tone or constraint (e.g. "local", "same-day", "temperature-controlled"). */
  tone?: string[];
  /** Optional instruction for generators (one line). */
  instruction?: string;
};

export type IndustryConfig = {
  id: ContentId;
  slug: Slug;
  messageKey: MessageKey;
  /** Short display name (e.g. "Coffee roasters"). */
  label: string;
  /** Optional hints for generating city-industry or expanded content. */
  generationHints?: GenerationHints;
};

export type ServiceAreaConfig = {
  id: ContentId;
  slug: Slug;
  messageKey: MessageKey;
  /** Display name (e.g. "Toronto", "Kitchener-Waterloo"). */
  label: string;
  /** Region or grouping (e.g. "GTA", "Peel", "Halton", "Niagara"). */
  region?: string;
  /** Whether this area has full content in messages (vs. fallback to default). */
  hasFullContent?: boolean;
  generationHints?: GenerationHints;
};

export type CampaignSegmentConfig = {
  id: ContentId;
  slug: Slug;
  messageKey: MessageKey;
  /** Short display name. */
  label: string;
  /** Optional link to industry slug when campaign aligns with an industry. */
  industrySlug?: Slug;
  generationHints?: GenerationHints;
};

// ——— Content variant registries (key → schema only; copy lives in messages or generated) ———

export type FAQVariantConfig = {
  variantKey: FAQVariantKey;
  /** Context: default | industry | service-area | campaign | city-industry. */
  context: "default" | "industry" | "service-area" | "campaign" | "city-industry";
  /** Optional: which entity slug this variant is for (e.g. coffee-roasters, toronto). */
  entitySlug?: Slug;
  /** Number of FAQ items expected. Used for validation and generation. */
  itemCount: number;
  generationHints?: GenerationHints;
};

export type CTAVariantConfig = {
  variantKey: CTAVariantKey;
  context: "default" | "industry" | "service-area" | "campaign" | "city-industry";
  entitySlug?: Slug;
  generationHints?: GenerationHints;
};

export type OnboardingVariantConfig = {
  variantKey: OnboardingVariantKey;
  context: "default" | "industry" | "service-area" | "campaign" | "city-industry";
  entitySlug?: Slug;
  stepCount: number;
  generationHints?: GenerationHints;
};

// ——— Page templates (for future city, city-industry, service, campaign pages) ———

export type PageType =
  | "home"
  | "industry"
  | "service-area"
  | "service-area-index"
  | "campaign"
  | "city"
  | "city-industry"
  | "service";

/** Which content blocks a page type typically uses. AI can use this to know what to generate. */
export type PageTemplate = {
  pageType: PageType;
  /** Human-readable description for generators. */
  description: string;
  /** Entities required: e.g. [ "industry" ], [ "serviceArea" ], [ "serviceArea", "industry" ]. */
  entitySlots: ("industry" | "serviceArea" | "campaign" | "service")[];
  /** Section blocks this page type should include. Order implies display order. */
  sectionBlocks: (
    | "meta"
    | "hero"
    | "painPoints"
    | "solution"
    | "vehicleFit"
    | "workflow"
    | "coverage"
    | "industries"
    | "onboarding"
    | "faq"
    | "cta"
    | "inquiry"
  )[];
  /** Which content variants to use: context + optional entity. */
  variantContext: "default" | "industry" | "service-area" | "campaign" | "city-industry";
};
