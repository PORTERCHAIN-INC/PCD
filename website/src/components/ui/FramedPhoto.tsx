import SiteImage from "@/components/ui/SiteImage";
import type { SiteImageRef } from "@/data/site-images";
import { cn } from "@/lib/utils";

type Props = {
  image: SiteImageRef;
  caption?: string;
  className?: string;
  tilt?: boolean;
  priority?: boolean;
  size?: "default" | "lg";
  aspect?: "portrait" | "landscape" | "wide";
};

/** Gallery-style picture frame for featured local photography. */
export default function FramedPhoto({
  image,
  caption,
  className,
  tilt = true,
  priority = false,
  size = "default",
  aspect = "landscape",
}: Props) {
  const isLarge = size === "lg";
  const aspectClass = {
    portrait: "aspect-[4/5]",
    landscape: "aspect-[4/3]",
    wide: "aspect-[21/9]",
  }[aspect];

  return (
    <figure
      className={cn(
        "relative mx-auto w-full",
        isLarge
          ? "max-w-[min(92vw,840px)] sm:max-w-[min(88vw,900px)] lg:max-w-[960px]"
          : "max-w-[280px] sm:max-w-[320px]",
        tilt && "-rotate-2 hover:rotate-0 transition-transform duration-500 ease-out",
        className
      )}
    >
      {/* Outer frame */}
      <div
        className={cn(
          "rounded-xl bg-gradient-to-br from-primary via-[#152238] to-primary shadow-2xl shadow-primary/25",
          isLarge ? "p-1.5 sm:p-2 rounded-2xl" : "p-[3px]"
        )}
      >
        {/* Mat */}
        <div className={cn("rounded-[10px] bg-[#f8f7f4]", isLarge ? "p-4 sm:p-6" : "p-3 sm:p-4")}>
          {/* Inner lip */}
          <div
            className={cn(
              "rounded-lg bg-white shadow-inner ring-1 ring-primary/[0.06]",
              isLarge ? "p-2 sm:p-3" : "p-1.5"
            )}
          >
            <div className={cn("relative overflow-hidden rounded-md bg-primary/5", aspectClass)}>
              <SiteImage
                image={image}
                fill
                className="object-cover object-center"
                sizes={
                  isLarge
                    ? "(max-width: 640px) 92vw, (max-width: 1024px) 88vw, 960px"
                    : "(max-width: 640px) 70vw, 320px"
                }
                priority={priority}
              />
            </div>
          </div>
          {caption && (
            <figcaption
              className={cn(
                "text-center font-semibold uppercase tracking-[0.18em] text-primary/60",
                isLarge ? "mt-4 text-xs sm:text-sm" : "mt-3 text-[10px] sm:text-xs"
              )}
            >
              {caption}
            </figcaption>
          )}
        </div>
      </div>
      {/* Shelf shadow */}
      <div
        className={cn(
          "absolute left-1/2 -translate-x-1/2 rounded-full bg-primary/15 blur-md",
          isLarge ? "-bottom-5 w-[72%] h-5" : "-bottom-3 w-[72%] h-3"
        )}
        aria-hidden
      />
    </figure>
  );
}
