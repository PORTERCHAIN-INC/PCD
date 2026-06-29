import { cn } from "@/lib/utils";

type ContainerSize = "default" | "narrow" | "wide";

interface ContainerProps {
  children: React.ReactNode;
  size?: ContainerSize;
  className?: string;
  as?: "div" | "section" | "nav" | "footer";
}

const sizeClasses: Record<ContainerSize, string> = {
  default: "max-w-[90rem]",
  narrow: "max-w-3xl",
  wide: "max-w-[100rem]",
};

export default function Container({
  children,
  size = "default",
  className,
  as: Tag = "div",
}: ContainerProps) {
  return (
    <Tag className={cn("page-container mx-auto w-full", sizeClasses[size], className)}>
      {children}
    </Tag>
  );
}
