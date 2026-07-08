import SiteImage from "@/components/ui/SiteImage";
import type { SiteImageRef } from "@/data/site-images";
import { cn } from "@/lib/utils";

type Props = {
  image: SiteImageRef;
  className?: string;
  aspect?: "wide" | "cinematic" | "card";
  priority?: boolean;
};

export default function HeroPhoto({ image, className, aspect = "wide", priority = false }: Props) {
  const aspectClass = {
    wide: "aspect-[21/9] sm:aspect-[2.35/1]",
    cinematic: "aspect-[16/9]",
    card: "aspect-[4/3] sm:aspect-[3/2]",
  }[aspect];

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl shadow-xl shadow-primary/10 ring-1 ring-primary/[0.08]",
        aspectClass,
        className
      )}
    >
      <SiteImage
        image={image}
        fill
        className="object-cover"
        sizes="(max-width: 768px) 100vw, 80vw"
        priority={priority}
      />
      <div
        className="absolute inset-0 bg-gradient-to-t from-primary/35 via-primary/5 to-transparent pointer-events-none"
        aria-hidden
      />
    </div>
  );
}
