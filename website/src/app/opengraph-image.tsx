import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "PorterChain — B2B transportation capacity in the GTA and Ontario";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: 64,
        background: "linear-gradient(135deg, #0a1628 0%, #132743 100%)",
        color: "#f8fafc",
      }}
    >
      <div style={{ fontSize: 56, fontWeight: 700, marginBottom: 16 }}>PorterChain</div>
      <div style={{ fontSize: 32, fontWeight: 500, maxWidth: 900, lineHeight: 1.3 }}>
        B2B transportation capacity — GTA &amp; Ontario
      </div>
      <div style={{ fontSize: 22, marginTop: 24, opacity: 0.85 }}>
        Vehicle + driver capacity · tracking · proof of delivery
      </div>
    </div>,
    { ...size }
  );
}
