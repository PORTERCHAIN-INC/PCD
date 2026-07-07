export default function ArchitectureIllustration() {
  return (
    <div className="w-full rounded-2xl border border-primary/[0.06] bg-white shadow-premium overflow-hidden">
      <div className="p-6 sm:p-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { layer: "Data", nodes: 3 },
            { layer: "Planning", nodes: 4 },
            { layer: "Execution", nodes: 5 },
            { layer: "Proof", nodes: 2 },
          ].map((col, i) => (
            <div key={col.layer} className="relative">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-secondary mb-3">
                {col.layer}
              </p>
              <div className="space-y-2">
                {Array.from({ length: col.nodes }).map((_, j) => (
                  <div
                    key={j}
                    className="h-10 rounded-lg bg-gray-bg border border-primary/[0.04] flex items-center px-3"
                  >
                    <div className="w-2 h-2 rounded-full bg-secondary/40" />
                  </div>
                ))}
              </div>
              {i < 3 && (
                <div
                  className="hidden md:block absolute top-1/2 -right-2 w-4 h-px bg-secondary/30"
                  aria-hidden
                />
              )}
            </div>
          ))}
        </div>
        <div className="mt-6 h-24 rounded-xl bg-primary/[0.03] border border-primary/[0.04] grid-pattern flex items-center justify-center">
          <svg viewBox="0 0 300 60" className="w-4/5 max-w-md" aria-hidden>
            <path
              d="M10 30 H290"
              stroke="#2563eb"
              strokeWidth="1.5"
              strokeDasharray="4 3"
              opacity="0.5"
            />
            <circle cx="75" cy="30" r="4" fill="#2563eb" />
            <circle cx="150" cy="30" r="4" fill="#2563eb" />
            <circle cx="225" cy="30" r="4" fill="#2563eb" />
          </svg>
        </div>
      </div>
    </div>
  );
}
