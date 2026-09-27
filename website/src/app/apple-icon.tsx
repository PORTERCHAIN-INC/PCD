import { readFileSync } from "node:fs";
import { join } from "node:path";
import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

const markSrc = `data:image/png;base64,${readFileSync(
  join(process.cwd(), "public/brand/porterchain-mark-white.png")
).toString("base64")}`;

/** White knot centered on navy. Width follows the mark's 298×267 ratio so it is not stretched. */
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
      }}
    >
      <img src={markSrc} width={124} height={111} alt="" />
    </div>,
    { ...size }
  );
}
