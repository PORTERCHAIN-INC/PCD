"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  href: string;
  children: React.ReactNode;
  className?: string;
  showArrow?: boolean;
};

export default function ShimmerLink({ href, children, className, showArrow = true }: Props) {
  return (
    <Link
      href={href}
      className={cn(
        "customer-shimmer relative inline-flex min-h-12 w-full items-center justify-center gap-2 overflow-hidden rounded-2xl bg-secondary px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-secondary/25 transition-colors hover:bg-[#1d4ed8] sm:w-auto sm:min-w-[14rem]",
        className
      )}
    >
      <span className="relative z-10 flex items-center gap-2">
        {children}
        {showArrow ? <ArrowRight className="h-4 w-4" aria-hidden /> : null}
      </span>
      <span className="customer-shimmer-glow absolute inset-0" aria-hidden />
    </Link>
  );
}
