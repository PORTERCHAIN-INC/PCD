import Link from "next/link";

export type CompletenessBannerData = {
  complete: boolean;
  missing_labels: string[];
  can_edit: boolean;
};

export default function CompanyCompletenessBanner({
  completeness,
}: {
  completeness?: CompletenessBannerData | null;
}) {
  if (!completeness || completeness.complete || !completeness.can_edit) return null;
  const labels = completeness.missing_labels.filter(Boolean);
  if (!labels.length) return null;
  const list =
    labels.length === 1
      ? labels[0]
      : `${labels.slice(0, -1).join(", ")}, and ${labels[labels.length - 1]}`;

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
      The company file is missing {list}.{" "}
      <Link href="/settings?tab=profile" className="font-semibold underline">
        Finish it in Settings
      </Link>
      .
    </div>
  );
}
