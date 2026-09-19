/**
 * SEO content expansion — centralized data model and config.
 *
 * Use for:
 * - City pages, city-industry pages, service pages, campaign pages
 * - AI-assisted content generation (explicit schemas and variant keys)
 * - Resolving message keys and entity config by slug
 *
 * Copy remains in messages (en.json, fr-ca.json); this layer provides
 * structure, variant registries, and page templates.
 */

// Types and block schemas
export type {
  ContentId,
  Slug,
  MessageKey,
  LocaleCode,
  MarketCode,
  MetaBlock,
  HeroBlock,
  PainPointsBlock,
  SolutionBlock,
  WorkflowStep,
  WorkflowBlock,
  CoverageBlock,
  IndustriesBlock,
  FAQItem,
  FAQBlock,
  FAQVariantKey,
  CTABlock,
  CTAVariantKey,
  OnboardingStep,
  OnboardingBlock,
  OnboardingVariantKey,
  InquiryBlock,
  GenerationHints,
  IndustryConfig,
  ServiceAreaConfig,
  CampaignSegmentConfig,
  FAQVariantConfig,
  CTAVariantConfig,
  OnboardingVariantConfig,
  PageType,
  PageTemplate,
} from "./types";

// Industries
export { INDUSTRY_CONFIGS, getIndustryConfig, getIndustryConfigByMessageKey } from "./industries";

// Service areas
export {
  SERVICE_AREA_CONFIGS,
  getServiceAreaConfig,
  getServiceAreaConfigByMessageKey,
} from "./service-areas";

// Campaign segments
export {
  CAMPAIGN_SEGMENT_CONFIGS,
  getCampaignSegmentConfig,
  getCampaignSegmentConfigByMessageKey,
} from "./campaigns";

// FAQ variants
export {
  FAQ_VARIANT_CONFIGS,
  getFAQVariantConfig,
  getFAQVariantConfigForEntity,
} from "./faq-variants";

// CTA variants
export {
  CTA_VARIANT_CONFIGS,
  getCTAVariantConfig,
  getCTAVariantConfigForEntity,
} from "./cta-variants";

// Onboarding messaging
export {
  ONBOARDING_VARIANT_CONFIGS,
  getOnboardingVariantConfig,
  getOnboardingVariantConfigForEntity,
} from "./onboarding-messaging";

// Page templates
export { PAGE_TEMPLATES, getPageTemplate, getPageTemplatesForEntitySlot } from "./page-templates";

// Article topics (logistics content framework)
export type { ArticlePillar, ArticleTopicLinks, ArticleTopic } from "./article-topics";
export {
  ARTICLE_TOPICS,
  ARTICLE_PILLAR_LABELS,
  getArticleTopicBySlug,
  getArticleTopicsByPillar,
} from "./article-topics";
