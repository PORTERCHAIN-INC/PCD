import { getImageProps } from "next/image";
import { cn } from "@/lib/utils";

/** 1×1 transparent GIF — phones render this instead of downloading the photo. */
const BLANK = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
const DESKTOP = "(min-width: 1024px)";

/**
 * Decorative hero photo for wide screens only (art direction via <picture>).
 * Responsive AVIF/WebP srcset from the Next optimizer, preloaded with high priority — but only
 * for wide screens (`media` on both the preload and the <source>), so phones skip the bytes and
 * their LCP stays the headline text.
 */
export default function DesktopHeroPicture({
  src,
  width,
  height,
  sizes = "60vw",
  alt = "",
  className,
}: {
  src: string;
  width: number;
  height: number;
  sizes?: string;
  alt?: string;
  className?: string;
}) {
  const {
    props: { srcSet },
  } = getImageProps({ src, alt, width, height, sizes, quality: 75 });

  return (
    <>
      <link
        rel="preload"
        as="image"
        imageSrcSet={srcSet}
        imageSizes={sizes}
        media={DESKTOP}
        fetchPriority="high"
      />
      {/* Fills the nearest positioned ancestor (callers wrap it in a relative/absolute box). */}
      <picture className="absolute inset-0 block">
        <source media={DESKTOP} srcSet={srcSet} sizes={sizes} />
        <img
          src={BLANK}
          alt={alt}
          width={width}
          height={height}
          fetchPriority="high"
          decoding="async"
          className={cn("h-full w-full object-cover", className)}
          // globals.css sets an unlayered `img { height: auto }` that beats the h-full utility.
          style={{ height: "100%" }}
        />
      </picture>
    </>
  );
}
