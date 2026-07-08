import { ImageResponse } from "next/og";
import { raviContact } from "@/lib/ravi-contact";

export const alt = `${raviContact.name} — ${raviContact.role} at ${raviContact.company}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function RaviOpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "72px",
        background: "linear-gradient(145deg, #0a2f22 0%, #124835 55%, #1a5c44 100%)",
        color: "#ffffff",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <div
        style={{
          fontSize: 28,
          fontWeight: 800,
          letterSpacing: "0.22em",
          textTransform: "uppercase",
          opacity: 0.9,
        }}
      >
        {raviContact.company}
      </div>
      <div style={{ fontSize: 22, marginTop: 12, opacity: 0.85 }}>{raviContact.tagline}</div>
      <div
        style={{
          marginTop: 48,
          fontSize: 64,
          fontWeight: 800,
          letterSpacing: "0.04em",
          lineHeight: 1.1,
        }}
      >
        {raviContact.nameDisplay}
      </div>
      <div style={{ marginTop: 20, fontSize: 34, fontWeight: 700 }}>{raviContact.role}</div>
      <div style={{ marginTop: 28, fontSize: 28, opacity: 0.92 }}>{raviContact.phone}</div>
      <div style={{ marginTop: 12, fontSize: 24, opacity: 0.85 }}>{raviContact.email}</div>
      <div style={{ marginTop: 40, fontSize: 22, opacity: 0.75 }}>porterchain.com/ravi</div>
    </div>,
    { ...size }
  );
}
