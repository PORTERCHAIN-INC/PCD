"use client";

import { memo } from "react";
import { FlashList, type FlashListProps } from "@shopify/flash-list";
import { DEFAULT_PERFORMANCE_POLICY } from "../config";

export type EnterpriseFlashListProps<T> = FlashListProps<T> & {
  estimatedItemSize?: number;
};

function EnterpriseFlashListInner<T>({
  estimatedItemSize = DEFAULT_PERFORMANCE_POLICY.defaultEstimatedItemSize,
  drawDistance = DEFAULT_PERFORMANCE_POLICY.listDrawDistance,
  removeClippedSubviews = true,
  ...props
}: EnterpriseFlashListProps<T>) {
  return (
    <FlashList
      estimatedItemSize={estimatedItemSize}
      drawDistance={drawDistance}
      removeClippedSubviews={removeClippedSubviews}
      {...props}
    />
  );
}

export const EnterpriseFlashList = memo(EnterpriseFlashListInner) as typeof EnterpriseFlashListInner;
