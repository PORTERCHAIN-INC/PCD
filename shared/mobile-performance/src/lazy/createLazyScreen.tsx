"use client";

import { lazy, Suspense, type ComponentType } from "react";
import { SkeletonList } from "@porterchain/mobile-ui";

let lazyScreenLoadCount = 0;

export function getLazyScreenLoadCount() {
  return lazyScreenLoadCount;
}

export function createLazyScreen<P extends object = object>(
  loader: () => Promise<{ default: ComponentType<P> } | Record<string, ComponentType<P>>>,
  exportName?: string
): ComponentType<P> {
  const Lazy = lazy(async () => {
    lazyScreenLoadCount += 1;
    const mod = await loader();
    if ("default" in mod && mod.default) {
      return { default: mod.default };
    }
    const name = exportName ?? Object.keys(mod)[0];
    return { default: (mod as Record<string, ComponentType<P>>)[name] };
  });

  function LazyScreen(props: P) {
    const Screen = Lazy as unknown as ComponentType<P>;
    return (
      <Suspense fallback={<SkeletonList />}>
        <Screen {...props} />
      </Suspense>
    );
  }

  return LazyScreen as unknown as ComponentType<P>;
}
