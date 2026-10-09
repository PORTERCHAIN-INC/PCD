import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LeadAttributionView from "@/components/leads/LeadAttributionView";

describe("LeadAttributionView", () => {
  it("renders source / industry / FSA breakdowns", () => {
    render(
      <LeadAttributionView
        data={{
          window_days: 30,
          total: 4,
          calculator_leads: 3,
          marketing_opt_in: 1,
          by_source: [{ key: "website_calculator", count: 3 }],
          by_industry: [{ key: "pharmacy", count: 2 }],
          by_fsa: [{ key: "M5V", count: 2 }],
          by_utm_source: [{ key: "google", count: 2 }],
          by_utm_campaign: [],
        }}
      />
    );
    expect(screen.getByText("website_calculator")).toBeInTheDocument();
    expect(screen.getByText("pharmacy")).toBeInTheDocument();
    expect(screen.getByText("M5V")).toBeInTheDocument();
    expect(screen.getByText("1 (25%)")).toBeInTheDocument();
    expect(screen.getByText("No leads in this window.")).toBeInTheDocument();
  });

  it("explains when data is unavailable", () => {
    render(<LeadAttributionView data={null} />);
    expect(screen.getByText(/Lead attribution is unavailable/)).toBeInTheDocument();
  });
});
