import { ImageResponse } from "next/og";

export type OgTone = "navy" | "blue" | "slate";

const TONES: Record<OgTone, { bg: string; accent: string }> = {
  navy: { bg: "linear-gradient(135deg, #0a1628 0%, #132743 100%)", accent: "#38bdf8" },
  blue: { bg: "linear-gradient(135deg, #0c1a33 0%, #1e3a5f 55%, #0ea5e9 160%)", accent: "#7dd3fc" },
  slate: { bg: "linear-gradient(135deg, #111827 0%, #1f2937 100%)", accent: "#94a3b8" },
};

/** Shared OG canvas for hub opengraph-image routes. */
export function ogImageResponse(opts: {
  eyebrow?: string;
  title: string;
  subtitle: string;
  tone?: OgTone;
}) {
  const tone = TONES[opts.tone ?? "navy"];
  const brand = opts.eyebrow ? `PorterChain · ${opts.eyebrow}` : "PorterChain";
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: 64,
        background: tone.bg,
        color: "#f8fafc",
      }}
    >
      <div
        style={{
          display: "flex",
          fontSize: 28,
          fontWeight: 600,
          color: tone.accent,
          marginBottom: 12,
        }}
      >
        {brand}
      </div>
      <div
        style={{
          display: "flex",
          fontSize: 52,
          fontWeight: 700,
          maxWidth: 980,
          lineHeight: 1.15,
        }}
      >
        {opts.title}
      </div>
      <div
        style={{
          display: "flex",
          fontSize: 24,
          marginTop: 20,
          opacity: 0.88,
          maxWidth: 920,
          lineHeight: 1.35,
        }}
      >
        {opts.subtitle}
      </div>
    </div>,
    { width: 1200, height: 630 }
  );
}
