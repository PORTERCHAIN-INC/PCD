/**
 * PorterChain Logistics Intelligence — research content model.
 * Placeholder entries stay draft + noindex until real operational data exists.
 */

import type { PublishableContent } from "./publishable";

export type ResearchReport = PublishableContent & {
  title: string;
  description: string;
  researchQuestion: string;
  dataSource: string;
  methodology: string;
  sampleSize?: string;
  dateRange?: string;
  limitations: string;
  keyFindings: string[];
  citationGuidance: string;
  /** Download path under /downloads/research/ when available */
  downloadPath?: string;
};

/** Draft scaffold only — non-indexable until [REQUIRES REAL CUSTOMER METRIC] data exists. */
export const RESEARCH_REPORTS: ResearchReport[] = [
  {
    slug: "gta-delivery-benchmark",
    title: "GTA B2B Delivery Benchmark Report",
    description:
      "[REQUIRES REAL CUSTOMER METRIC] Future benchmark report for response times and delivery performance across the GTA.",
    researchQuestion:
      "How do B2B same-day and scheduled delivery response times compare across GTA corridors?",
    dataSource: "[REQUIRES REAL OPERATIONAL DATA] PorterChain dispatch and completion timestamps.",
    methodology:
      "[REQUIRES FOUNDER APPROVAL] Documented sampling and aggregation method before publication.",
    limitations: "Report will not publish until sample size and date range are verified.",
    keyFindings: [],
    citationGuidance:
      "Cite as PorterChain Logistics Intelligence with report slug and published date when available.",
    status: "draft",
    index: false,
  },
];

export function getResearchReportBySlug(slug: string): ResearchReport | undefined {
  return RESEARCH_REPORTS.find((r) => r.slug === slug);
}

export function getIndexableResearchReports(): ResearchReport[] {
  return RESEARCH_REPORTS.filter((r) => r.status === "published" && r.index);
}
