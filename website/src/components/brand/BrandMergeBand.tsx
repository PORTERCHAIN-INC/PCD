import Container from "@/components/ui/Container";
import SiteImage from "@/components/ui/SiteImage";
import BlurFade from "@/components/magic/blur-fade";
import type { SiteImageRef } from "@/data/site-images";
import { cn } from "@/lib/utils";

type Props = {
  eyebrow: string;
  title: string;
  body: string;
  /** Prefer image-on-right for LTR reading flow (copy first, then photo). */
  imageSide?: "left" | "right";
  /** Page-exclusive brand photo — do not reuse the same asset on another route. */
  image: SiteImageRef;
  /** CSS object-position for the photo crop. */
  objectPosition?: string;
  className?: string;
  priority?: boolean;
};

/**
 * Brand photo with soft blur merge into copy.
 * Each caller must pass a unique `image` owned by that page.
 */
export default function BrandMergeBand({
  eyebrow,
  title,
  body,
  imageSide = "right",
  image,
  objectPosition = "center 55%",
  className,
  priority = false,
}: Props) {
  const imageFirst = imageSide === "left";

  return (
    <section className={cn("relative overflow-hidden bg-white", className)}>
      <div className="grid lg:grid-cols-2 min-h-[min(56svh,520px)]">
        <div
          className={cn(
            "relative z-20 flex items-center",
            imageFirst ? "order-2 lg:order-2" : "order-2 lg:order-1"
          )}
        >
          <div
            className="absolute inset-0 grid-pattern opacity-30 pointer-events-none"
            aria-hidden
          />
          <div
            className={cn(
              "absolute inset-0 pointer-events-none brand-merge-panel hidden lg:block",
              imageFirst && "brand-merge-panel--from-left"
            )}
            aria-hidden
          />
          <div
            className={cn(
              "absolute inset-y-0 z-10 hidden w-24 lg:block brand-merge-blur pointer-events-none",
              imageFirst ? "-left-4 brand-merge-blur--from-left" : "-right-4"
            )}
            aria-hidden
          />

          <Container
            className={cn(
              "relative z-10 w-full py-10 sm:py-12 lg:py-14",
              imageFirst ? "lg:pl-8 xl:pl-12" : "lg:pr-8 xl:pr-12"
            )}
          >
            <BlurFade>
              <p className="pc-eyebrow">{eyebrow}</p>
            </BlurFade>
            <BlurFade delay={0.06}>
              <h2 className="mt-4 pc-display text-primary text-balance max-w-xl">{title}</h2>
            </BlurFade>
            <BlurFade delay={0.12}>
              <p className="mt-5 max-w-lg text-lg text-muted leading-relaxed">{body}</p>
            </BlurFade>
          </Container>
        </div>

        <div
          className={cn(
            "relative order-1 min-h-[36svh] sm:min-h-[42svh] lg:min-h-0",
            imageFirst ? "lg:order-1" : "lg:order-2"
          )}
        >
          <div className="absolute inset-0 overflow-hidden">
            <SiteImage
              image={image}
              fill
              priority={priority}
              className="object-cover scale-[1.02]"
              style={{ objectPosition }}
              sizes="(max-width: 1024px) 100vw, 50vw"
            />
            <div
              className="absolute inset-0 pointer-events-none"
              aria-hidden
              style={{
                background:
                  "radial-gradient(ellipse 70% 55% at 70% 80%, rgba(132,204,22,0.14) 0%, transparent 65%)",
              }}
            />
          </div>

          <div
            className={cn(
              "absolute inset-y-0 hidden w-[48%] pointer-events-none lg:block",
              imageFirst ? "right-0 brand-image-fade-right" : "left-0 brand-image-fade-left"
            )}
            aria-hidden
          />
          <div
            className={cn(
              "absolute inset-y-0 hidden w-[24%] brand-merge-blur pointer-events-none lg:block",
              imageFirst ? "right-0 brand-merge-blur--from-left" : "left-0"
            )}
            aria-hidden
          />

          <div
            className="absolute inset-0 pointer-events-none lg:hidden"
            aria-hidden
            style={{
              background:
                "linear-gradient(to bottom, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.55) 70%, white 100%)",
            }}
          />
        </div>
      </div>
    </section>
  );
}
