import { type ReactNode } from "react";
import { PerformanceProvider } from "@porterchain/mobile-performance";

export function PerformanceLayer({ children }: { children: ReactNode }) {
  return <PerformanceProvider>{children}</PerformanceProvider>;
}
