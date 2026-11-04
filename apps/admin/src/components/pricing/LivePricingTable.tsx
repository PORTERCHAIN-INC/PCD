/** The live PorterChain pricing (Ravi 2026-10-31). Prices before HST. Code-defined, read only. */
export const RETIRED_NOTE =
  "Retired 2026-10-31: read only, kept for history. These settings no longer set any price.";

export function RetiredBanner({ what }: { what: string }) {
  return (
    <p
      role="note"
      className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
    >
      {what} — {RETIRED_NOTE} Live pricing: see “Live pricing”.
    </p>
  );
}

export default function LivePricingTable() {
  const rows: [string, string][] = [
    ["Small parcel (fits 20 × 14 × 14 in, ≤ 100 lb)", "$6 each"],
    ["Van parcel (anything larger)", "$9 each"],
    ["101–125 lb, or up to 80 × 45 in", "+$30 handling per parcel"],
    ["126–150 lb, or up to 90 × 50 in", "+$60 handling per parcel"],
    ["Over 150 lb or over 90 × 50 in", "Custom quote"],
  ];
  const hourly: [string, string][] = [
    ["Sedan / SUV / pickup", "$40 / h"],
    ["Cargo van / small van", "$60 / h"],
    ["16 ft+ box / cube van", "$70 / h"],
    ["Load help, per stop where requested", "+$30"],
  ];
  const T = ({ title, data, note }: { title: string; data: [string, string][]; note: string }) => (
    <section className="rounded-xl border p-4">
      <h3 className="font-semibold">{title}</h3>
      <p className="text-xs text-muted">{note}</p>
      <table className="mt-2 w-full text-sm">
        <tbody>
          {data.map(([a, b]) => (
            <tr key={a} className="border-t border-primary/5">
              <td className="py-1">{a}</td>
              <td className="py-1 text-right font-medium">{b}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
  return (
    <div className="space-y-4" aria-label="Live pricing">
      <T
        title="1 · Parcels (merchants and customers)"
        data={rows}
        note="The higher of weight and size decides the handling tier; tiers do not stack."
      />
      <T
        title="2 · Hourly vehicle (merchants only)"
        data={hourly}
        note="3 h minimum, from arrival at pickup to the last drop."
      />
      <section className="rounded-xl border p-4 text-sm">
        <h3 className="font-semibold">3 · Admin custom merchant price</h3>
        <p>
          Set per merchant (Merchant → Pricing, or Rate card → organisation). It overrides models 1
          and 2.
        </p>
      </section>
      <p className="text-xs text-muted">All prices before 13% HST.</p>
    </div>
  );
}
