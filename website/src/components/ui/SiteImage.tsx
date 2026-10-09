"use client";

import { useState, type CSSProperties } from "react";
import Image from "next/image";
import { FALLBACK_IMAGE, type SiteImageRef } from "@/data/site-images";
import { cn } from "@/lib/utils";

type Props = {
  image: SiteImageRef;
  fill?: boolean;
  className?: string;
  priority?: boolean;
  sizes?: string;
  style?: CSSProperties;
  /** Override Next/Image quality (1–100). Brand assets default higher. */
  quality?: number;
  /**
   * Skip Next optimizer (AVIF/WebP recompress). Use for MAIN brand photos
   * when maximum sharpness matters more than format conversion.
   */
  unoptimized?: boolean;
};

function defaultQuality(src: string): number {
  // Brand photography: q90 AVIF/WebP stays sharp at a fraction of the bytes.
  if (src.startsWith("/images/brand/")) return 90;
  return 80;
}

export default function SiteImage({
  image,
  fill,
  className,
  priority,
  sizes,
  style,
  quality,
  unoptimized,
}: Props) {
  const [src, setSrc] = useState(image.src);
  const alt = image.alt;
  const q = quality ?? defaultQuality(image.src);
  // Always use the Next optimizer (AVIF/WebP + responsive srcset) unless a caller opts out.
  // Raw 5K JPEGs made mobile LCP 26–37 s in production (readiness audit #2).
  const skipOptimizer = unoptimized ?? false;

  const handleError = () => {
    if (src !== FALLBACK_IMAGE.src) {
      setSrc(FALLBACK_IMAGE.src);
    }
  };

  if (fill) {
    return (
      <Image
        src={src}
        alt={alt}
        fill
        className={cn(className)}
        style={style}
        sizes={sizes ?? "100vw"}
        priority={priority}
        quality={q}
        unoptimized={skipOptimizer}
        onError={handleError}
      />
    );
  }

  return (
    <Image
      src={src}
      alt={alt}
      width={image.width}
      height={image.height}
      className={cn(className)}
      style={style}
      sizes={sizes}
      priority={priority}
      quality={q}
      unoptimized={skipOptimizer}
      onError={handleError}
    />
  );
}
