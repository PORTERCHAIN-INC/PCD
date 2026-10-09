"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type LottiePlayer = {
  play: () => void;
  pause: () => void;
  goToAndStop: (value: number, isFrame?: boolean) => void;
  destroy: () => void;
  totalFrames: number;
};

type Props = {
  /** JSON under /public/lottie (e.g. "/lottie/van-route.json"). */
  src: string;
  /** Width / height of the animation canvas — the box reserves this ratio (no layout shift). */
  aspect: number;
  /** Frame shown when motion is reduced (default: last frame). */
  stillFrame?: number;
  loop?: boolean;
  /** Start as soon as it is visible (default) or wait for `play` to flip true. */
  play?: boolean;
  className?: string;
  /** Accessible description; omit for purely decorative motion. */
  label?: string;
  testId?: string;
};

const cache = new Map<string, Promise<unknown>>();
function loadJson(src: string) {
  if (!cache.has(src))
    cache.set(
      src,
      fetch(src).then((r) => r.json())
    );
  return cache.get(src)!;
}

/**
 * Lightweight Lottie: the SVG-only `lottie_light` player (≈47 KB gz) is imported on demand when
 * the box nears the viewport, plays only while visible and pauses offscreen. With
 * prefers-reduced-motion it renders one still frame and never animates. The box has a fixed
 * aspect ratio, so nothing shifts while the player loads; it is never in the LCP path.
 */
export default function LottieMotion({
  src,
  aspect,
  stillFrame,
  loop = true,
  play = true,
  className,
  label,
  testId,
}: Props) {
  const box = useRef<HTMLDivElement>(null);
  const player = useRef<LottiePlayer | null>(null);
  const visible = useRef(false);
  const [mode, setMode] = useState<"idle" | "motion" | "still">("idle");

  useEffect(() => {
    const el = box.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cancelled = false;

    const start = async () => {
      const [{ default: lottie }, animationData] = await Promise.all([
        import("lottie-web/build/player/lottie_light"),
        loadJson(src),
      ]);
      if (cancelled || !box.current) return;
      const anim = lottie.loadAnimation({
        container: box.current,
        renderer: "svg",
        loop: reduced ? false : loop,
        autoplay: false,
        animationData,
        rendererSettings: { preserveAspectRatio: "xMidYMid meet", progressiveLoad: true },
      }) as unknown as LottiePlayer;
      player.current = anim;
      if (reduced) {
        anim.goToAndStop(stillFrame ?? Math.max(0, anim.totalFrames - 1), true);
        setMode("still");
      } else {
        setMode("motion");
        if (visible.current && play) anim.play();
      }
    };

    const io = new IntersectionObserver(
      ([entry]) => {
        visible.current = entry.isIntersecting;
        if (!player.current) {
          if (entry.isIntersecting || entry.intersectionRatio > 0) void start();
          return;
        }
        if (reduced) return;
        if (entry.isIntersecting && play) player.current.play();
        else player.current.pause();
      },
      { rootMargin: "200px 0px" }
    );
    io.observe(el);
    return () => {
      cancelled = true;
      io.disconnect();
      player.current?.destroy();
      player.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- player is created once per src
  }, [src]);

  useEffect(() => {
    const anim = player.current;
    if (!anim || mode !== "motion") return;
    if (play && visible.current) anim.play();
    else if (!play) anim.goToAndStop(0, true);
  }, [play, mode]);

  return (
    <div
      ref={box}
      className={cn("relative w-full overflow-hidden [&>svg]:block", className)}
      style={{ aspectRatio: String(aspect) }}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      data-motion={mode}
      data-testid={testId}
    />
  );
}
