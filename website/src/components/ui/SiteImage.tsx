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
  // Local brand photography — keep sharp (Next default is 75).
  if (src.startsWith("/images/brand/")) return 98;
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
        unoptimized={unoptimized}
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
      unoptimized={unoptimized}
      onError={handleError}
    />
  );
}
