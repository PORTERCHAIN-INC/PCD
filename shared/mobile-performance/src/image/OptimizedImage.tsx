"use client";

import { Image, type ImageProps } from "expo-image";
import { DEFAULT_PERFORMANCE_POLICY } from "../config";

export type OptimizedImageProps = ImageProps & {
  width?: number;
  height?: number;
};

export function OptimizedImage({
  cachePolicy = DEFAULT_PERFORMANCE_POLICY.imageCachePolicy,
  contentFit = "cover",
  transition = 200,
  recyclingKey,
  ...props
}: OptimizedImageProps) {
  return (
    <Image
      cachePolicy={cachePolicy}
      contentFit={contentFit}
      transition={transition}
      recyclingKey={
        recyclingKey ??
        (typeof props.source === "object" && props.source && "uri" in props.source
          ? props.source.uri
          : undefined)
      }
      {...props}
    />
  );
}

export async function clearImageCache() {
  await Image.clearMemoryCache();
  await Image.clearDiskCache();
}
