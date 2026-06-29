export default function SolutionsIllustration() {
  return (
    <div className="grid grid-cols-2 gap-3 w-full max-w-md">
      {[
        { label: "Wholesale", pct: 85 },
        { label: "Medical", pct: 92 },
        { label: "Food", pct: 78 },
        { label: "Construction", pct: 88 },
      ].map((item) => (
        <div
          key={item.label}
          className="rounded-xl bg-white border border-primary/[0.06] p-4 shadow-sm"
        >
          <p className="text-xs font-semibold text-primary">{item.label}</p>
          <div className="mt-3 h-1.5 rounded-full bg-gray-bg overflow-hidden">
            <div
              className="h-full rounded-full bg-secondary"
              style={{ width: `${item.pct}%` }}
            />
          </div>
          <p className="mt-2 text-[10px] text-muted">SLA {item.pct}%</p>
        </div>
      ))}
    </div>
  );
}
