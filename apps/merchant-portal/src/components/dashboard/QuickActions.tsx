import { buttonClasses } from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { hasMerchantModule, merchantPortalJob } from "@/lib/merchant-nav";
import { CreditCard, LifeBuoy, MapPinned, Package, PackagePlus, Search } from "lucide-react";
import Link from "next/link";

interface QuickActionsProps {
  invoiceUrl?: string | null;
}

export function QuickActions({ invoiceUrl }: QuickActionsProps) {
  const { modules } = useMerchantAuth();
  const job = merchantPortalJob(modules);
  const canBook = hasMerchantModule(modules, "book");
  const canRoutes = hasMerchantModule(modules, "routes");
  const canTrack = hasMerchantModule(modules, "tracking");
  const canBilling = hasMerchantModule(modules, "billing");
  const canClaims = hasMerchantModule(modules, "claims");
  const canOrders = hasMerchantModule(modules, "orders");

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-4 sm:p-6">
      <h2 className="text-lg font-semibold text-primary">Quick Actions</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {canBook ? (
          <Link
            href="/book"
            className={buttonClasses("primary", "sm", "w-full justify-center gap-2")}
          >
            <PackagePlus className="h-4 w-4" />
            Request capacity
          </Link>
        ) : null}
        {canRoutes ? (
          <Link
            href="/routes"
            className={buttonClasses("outline", "sm", "w-full justify-center gap-2")}
          >
            <MapPinned className="h-4 w-4" />
            Route Planner
          </Link>
        ) : null}
        {canOrders ? (
          <Link
            href="/orders"
            className={buttonClasses("outline", "sm", "w-full justify-center gap-2")}
          >
            <Package className="h-4 w-4" />
            Orders
          </Link>
        ) : null}
        {canTrack ? (
          <Link
            href="/track"
            className={buttonClasses("outline", "sm", "w-full justify-center gap-2")}
          >
            <Search className="h-4 w-4" />
            Track
          </Link>
        ) : null}
        {canClaims && job !== "viewer" ? (
          <Link
            href="/help"
            className={buttonClasses("outline", "sm", "w-full justify-center gap-2")}
          >
            <LifeBuoy className="h-4 w-4" />
            Claims
          </Link>
        ) : null}
        {invoiceUrl ? (
          <a
            href={invoiceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonClasses("outline", "sm", "w-full justify-center gap-2")}
          >
            View invoice
          </a>
        ) : canBilling ? (
          <Link
            href="/billing"
            className={buttonClasses("outline", "sm", "w-full justify-center gap-2")}
          >
            <CreditCard className="h-4 w-4" />
            View Invoices
          </Link>
        ) : null}
        {job === "owner" ? (
          <Link
            href="/referrals"
            className={buttonClasses("outline", "sm", "w-full justify-center gap-2")}
          >
            Refer a business
          </Link>
        ) : null}
      </div>
    </section>
  );
}
