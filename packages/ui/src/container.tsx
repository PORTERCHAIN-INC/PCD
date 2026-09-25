import { cn } from "./utils";

type ContainerWidth = "default" | "fluid";

/**
 * Page width rail.
 * - default: marketing/content max (~7xl)
 * - fluid: full viewport width (ops tables / admin shells)
 */
export default function Container({
  children,
  className,
  width = "default",
}: {
  children: React.ReactNode;
  className?: string;
  width?: ContainerWidth;
}) {
  return (
    <div
      className={cn(
        "mx-auto w-full min-w-0 px-3 sm:px-4 lg:px-6 xl:px-8",
        width === "fluid" ? "max-w-none" : "max-w-7xl",
        className
      )}
    >
      {children}
    </div>
  );
}
