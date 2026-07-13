"use client";

import dynamic from "next/dynamic";
import LazyWhenVisible from "@/components/ui/LazyWhenVisible";

function SectionSkeleton({ minHeight = "320px" }: { minHeight?: string }) {
  return (
    <div className="pc-section bg-white" aria-hidden style={{ minHeight }}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="h-8 w-48 max-w-full rounded-lg bg-primary/5 animate-pulse" />
        <div className="mt-4 h-12 w-2/3 max-w-full rounded-lg bg-primary/5 animate-pulse" />
      </div>
    </div>
  );
}

const StoryProblems = dynamic(() => import("@/components/home/story/StoryProblems"), {
  loading: () => <SectionSkeleton minHeight="420px" />,
});
const StoryFlow = dynamic(() => import("@/components/home/story/StoryFlow"), {
  loading: () => <SectionSkeleton />,
});
const StoryFleet = dynamic(() => import("@/components/home/story/StoryFleet"), {
  loading: () => <SectionSkeleton minHeight="480px" />,
});
const StoryPlatform = dynamic(() => import("@/components/home/story/StoryPlatform"), {
  loading: () => <SectionSkeleton />,
});
const StoryIndustries = dynamic(() => import("@/components/home/story/StoryIndustries"), {
  loading: () => <SectionSkeleton minHeight="400px" />,
});
const StoryEnterprise = dynamic(() => import("@/components/home/story/StoryEnterprise"), {
  loading: () => <SectionSkeleton />,
});
const StoryCta = dynamic(() => import("@/components/home/story/StoryCta"), {
  loading: () => <SectionSkeleton minHeight="280px" />,
});

export default function HomeDeferredStorySections() {
  return (
    <>
      <LazyWhenVisible minHeight="420px">
        <StoryProblems />
      </LazyWhenVisible>
      <LazyWhenVisible>
        <StoryFlow />
      </LazyWhenVisible>
      <LazyWhenVisible minHeight="480px">
        <StoryFleet />
      </LazyWhenVisible>
      <LazyWhenVisible>
        <StoryPlatform />
      </LazyWhenVisible>
      <LazyWhenVisible minHeight="400px">
        <StoryIndustries />
      </LazyWhenVisible>
      <LazyWhenVisible>
        <StoryEnterprise />
      </LazyWhenVisible>
      <LazyWhenVisible minHeight="280px">
        <StoryCta />
      </LazyWhenVisible>
    </>
  );
}
