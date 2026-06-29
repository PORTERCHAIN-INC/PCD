interface LogisticsPatternProps {
  className?: string;
}

/** Subtle background pattern — route nodes & connections */
export default function LogisticsPattern({ className = "" }: LogisticsPatternProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 400 400"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <defs>
        <pattern id="logisticsGrid" x="0" y="0" width="80" height="80" patternUnits="userSpaceOnUse">
          <circle cx="40" cy="40" r="1.5" fill="#2563eb" opacity="0.15" />
          <path d="M40 40 L80 40 M40 40 L40 80" stroke="#2563eb" strokeWidth="0.5" opacity="0.08" />
        </pattern>
      </defs>
      <rect width="400" height="400" fill="url(#logisticsGrid)" />
      <path
        d="M40 200 Q120 120 200 200 T360 200"
        stroke="#2563eb"
        strokeWidth="1"
        strokeDasharray="4 6"
        opacity="0.12"
        fill="none"
      />
      <circle cx="40" cy="200" r="4" fill="#2563eb" opacity="0.2" />
      <circle cx="200" cy="200" r="4" fill="#38bdf8" opacity="0.25" />
      <circle cx="360" cy="200" r="4" fill="#2563eb" opacity="0.2" />
    </svg>
  );
}
