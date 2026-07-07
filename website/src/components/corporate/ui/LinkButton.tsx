import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { ArrowRight } from "lucide-react";

type LinkButtonVariant = "primary" | "secondary" | "outline" | "ghost";
type LinkButtonSize = "sm" | "md" | "lg";

interface LinkButtonProps {
  href: string;
  children: React.ReactNode;
  variant?: LinkButtonVariant;
  size?: LinkButtonSize;
  className?: string;
  showArrow?: boolean;
  external?: boolean;
}

const variants: Record<LinkButtonVariant, string> = {
  primary:
    "bg-secondary text-white hover:bg-[#1d4ed8] shadow-lg shadow-secondary/20 hover:shadow-secondary/35",
  secondary: "bg-primary text-white hover:bg-[#152238] shadow-lg shadow-primary/15",
  outline:
    "border border-primary/15 text-primary bg-white hover:bg-gray-bg hover:border-secondary/30",
  ghost: "text-primary hover:bg-gray-bg",
};

const sizes: Record<LinkButtonSize, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-6 py-3 text-sm",
  lg: "px-8 py-3.5 text-base",
};

export default function LinkButton({
  href,
  children,
  variant = "primary",
  size = "md",
  className,
  showArrow = false,
  external = false,
}: LinkButtonProps) {
  const classes = cn(
    "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all duration-200",
    variants[variant],
    sizes[size],
    className
  );

  if (external || href.startsWith("mailto:") || href.startsWith("tel:")) {
    return (
      <a href={href} className={classes}>
        {children}
        {showArrow && <ArrowRight className="w-4 h-4" />}
      </a>
    );
  }

  return (
    <Link href={href} className={classes}>
      {children}
      {showArrow && <ArrowRight className="w-4 h-4" />}
    </Link>
  );
}
