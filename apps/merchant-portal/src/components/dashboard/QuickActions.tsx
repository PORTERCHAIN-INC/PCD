import Button from "@/components/ui/Button";
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
          <Link href="/book">
            <Button className="w-full justify-center gap-2" size="sm">
              <PackagePlus className="h-4 w-4" />
              Request capacity
            </Button>
          </Link>
        ) : null}
        {canRoutes ? (
          <Link href="/routes">
            <Button className="w-full justify-center gap-2" size="sm" variant="outline">
              <MapPinned className="h-4 w-4" />
              Route Planner
            </Button>
          </Link>
        ) : null}
        {canOrders ? (
          <Link href="/orders">
            <Button className="w-full justify-center gap-2" size="sm" variant="outline">
              <Package className="h-4 w-4" />
              Orders
            </Button>
          </Link>
        ) : null}
        {canTrack ? (
          <Link href="/track">
            <Button className="w-full justify-center gap-2" size="sm" variant="outline">
              <Search className="h-4 w-4" />
              Track
            </Button>
          </Link>
        ) : null}
        {canClaims && job !== "viewer" ? (
          <Link href="/help">
            <Button className="w-full justify-center gap-2" size="sm" variant="outline">
              <LifeBuoy className="h-4 w-4" />
              Claims
            </Button>
          </Link>
        ) : null}
        {invoiceUrl ? (
          <a href={invoiceUrl} target="_blank" rel="noopener noreferrer">
            <Button className="w-full justify-center gap-2" size="sm" variant="outline">
              View invoice
            </Button>
          </a>
        ) : canBilling ? (
          <Link href="/billing">
            <Button className="w-full justify-center gap-2" size="sm" variant="outline">
              <CreditCard className="h-4 w-4" />
              View Invoices
            </Button>
          </Link>
        ) : null}
        {job === "owner" ? (
          <Link href="/referrals">
            <Button className="w-full justify-center gap-2" size="sm" variant="outline">
              Refer a business
            </Button>
          </Link>
        ) : null}
      </div>
    </section>
  );
}
