import { siteImages } from "@/data/site-images";
import DesktopHeroPicture from "@/components/marketing/ui/DesktopHeroPicture";

/** Home hero fleet photo — desktop only (see DesktopHeroPicture). */
export default function HomeHeroImage() {
  const image = siteImages.hero.welcome;
  return (
    <DesktopHeroPicture
      src={image.src}
      width={image.width}
      height={image.height}
      sizes="60vw"
      className="object-[center_45%]"
    />
  );
}
