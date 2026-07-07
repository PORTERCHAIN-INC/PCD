interface DeliveryVanProps {
  className?: string;
}

export default function DeliveryVan({ className = "" }: DeliveryVanProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 320 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <defs>
        <linearGradient id="vanBody" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#1e3a5f" />
          <stop offset="100%" stopColor="#0f2744" />
        </linearGradient>
        <linearGradient id="vanStripe" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#2563eb" />
          <stop offset="100%" stopColor="#38bdf8" />
        </linearGradient>
      </defs>

      {/* Shadow */}
      <ellipse cx="160" cy="148" rx="120" ry="8" fill="#0a1628" opacity="0.3" />

      {/* Van body */}
      <rect x="30" y="55" width="220" height="78" rx="10" fill="url(#vanBody)" />
      <rect x="250" y="68" width="48" height="65" rx="8" fill="#152238" />

      {/* Cab window */}
      <rect
        x="258"
        y="76"
        width="32"
        height="28"
        rx="4"
        fill="#1e3a5f"
        stroke="#2563eb"
        strokeWidth="1"
        opacity="0.6"
      />

      {/* Brand stripe */}
      <rect x="38" y="68" width="204" height="6" rx="2" fill="url(#vanStripe)" opacity="0.9" />

      {/* Logo area */}
      <rect x="50" y="82" width="100" height="36" rx="4" fill="#0a1628" opacity="0.4" />
      <text
        x="100"
        y="105"
        textAnchor="middle"
        fill="white"
        fontSize="11"
        fontWeight="700"
        fontFamily="system-ui, sans-serif"
        opacity="0.9"
      >
        PORTERCHAIN
      </text>

      {/* Package icon on side */}
      <rect
        x="170"
        y="88"
        width="28"
        height="22"
        rx="3"
        fill="#2563eb"
        opacity="0.25"
        stroke="#38bdf8"
        strokeWidth="1"
      />
      <path
        d="M178 94 L184 90 L190 94 L190 104 L178 104 Z"
        stroke="#60a5fa"
        strokeWidth="1"
        fill="none"
      />

      {/* Wheels */}
      <circle cx="85" cy="133" r="16" fill="#0a1628" />
      <circle cx="85" cy="133" r="9" fill="#1e3354" />
      <circle cx="85" cy="133" r="4" fill="#2563eb" opacity="0.5" />
      <circle cx="220" cy="133" r="16" fill="#0a1628" />
      <circle cx="220" cy="133" r="9" fill="#1e3354" />
      <circle cx="220" cy="133" r="4" fill="#2563eb" opacity="0.5" />

      {/* Headlight */}
      <circle cx="296" cy="108" r="4" fill="#38bdf8" opacity="0.7" />

      {/* Motion lines */}
      <line
        x1="8"
        y1="90"
        x2="22"
        y2="90"
        stroke="#38bdf8"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.4"
      />
      <line
        x1="4"
        y1="100"
        x2="18"
        y2="100"
        stroke="#2563eb"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.3"
      />
      <line
        x1="10"
        y1="110"
        x2="20"
        y2="110"
        stroke="#38bdf8"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.25"
      />
    </svg>
  );
}
