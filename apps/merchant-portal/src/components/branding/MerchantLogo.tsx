type Props = {
  src?: string | null;
  name?: string | null;
  size?: "sm" | "md";
  className?: string;
};

export default function MerchantLogo({ src, name, size = "sm", className = "" }: Props) {
  const box = size === "md" ? "h-12 w-12" : "h-8 w-8";
  const letter = (name || "P").trim().charAt(0).toUpperCase() || "P";
  const alt = name?.trim() ? `${name.trim()} logo` : "Company logo";

  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={alt}
        referrerPolicy="no-referrer"
        className={`${box} rounded-lg object-cover ${className}`.trim()}
      />
    );
  }

  return (
    <span
      className={`flex ${box} items-center justify-center rounded-lg bg-secondary text-sm font-bold text-white shadow-sm ${className}`.trim()}
      aria-hidden={name ? undefined : true}
    >
      {letter}
    </span>
  );
}
