"use client";

import { useState } from "react";
import Image from "next/image";
import { FALLBACK_IMAGE, type SiteImageRef } from "@/data/site-images";
import { cn } from "@/lib/utils";

type Props = {
  image: SiteImageRef;
  fill?: boolean;
  className?: string;
  priority?: boolean;
  sizes?: string;
};

export default function SiteImage({ image, fill, className, priority, sizes }: Props) {
  const [src, setSrc] = useState(image.src);
  const alt = image.alt;

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
        sizes={sizes ?? "100vw"}
        priority={priority}
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
      sizes={sizes}
      priority={priority}
      onError={handleError}
    />
  );
}
