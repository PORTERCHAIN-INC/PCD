import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0a1628",
        borderRadius: 40,
      }}
    >
      <div
        style={{
          color: "#ffffff",
          fontSize: 28,
          fontWeight: 600,
          letterSpacing: "0.04em",
          fontFamily: "system-ui, sans-serif",
          lineHeight: 1,
        }}
      >
        Porterchain
      </div>
    </div>,
    { ...size }
  );
}
