"use client";

import type { ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type LoginStatusCardProps = {
  title: string;
  description?: string;
  children?: ReactNode;
  loading?: boolean;
  variant?: "default" | "error";
};

export default function LoginStatusCard({
  title,
  description,
  children,
  loading = false,
  variant = "default",
}: LoginStatusCardProps) {
  return (
    <div className="w-full max-w-md mx-auto">
      <div
        className={cn(
          "rounded-2xl border bg-white p-8 shadow-premium",
          variant === "error" ? "border-red-200/80" : "border-primary/8"
        )}
      >
        {loading && (
          <div className="mb-5 flex justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-secondary" aria-hidden />
          </div>
        )}
        <h1 className="text-xl font-semibold tracking-tight text-primary text-center">{title}</h1>
        {description && (
          <p
            className={cn(
              "mt-3 text-sm text-center leading-relaxed",
              variant === "error" ? "text-red-700" : "text-muted"
            )}
          >
            {description}
          </p>
        )}
        {children && <div className="mt-6 flex flex-col gap-3">{children}</div>}
      </div>
    </div>
  );
}
