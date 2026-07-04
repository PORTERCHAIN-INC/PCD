import { Route } from "lucide-react";
import RouteCenterNav from "@/components/routes/RouteCenterNav";

export default function RoutesLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-primary/10 bg-gradient-to-br from-white via-white to-secondary/[0.04] p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
            <Route className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-tight text-primary">Route Center</h1>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted">
              Plan routes, optimize stops, dispatch drivers, and monitor live execution — all in one
              workflow.
            </p>
          </div>
        </div>
      </div>
      <div className="sticky top-0 z-10 rounded-2xl border border-primary/10 bg-gray-bg/90 px-3 py-3 backdrop-blur-md">
        <RouteCenterNav />
      </div>
      {children}
    </div>
  );
}
