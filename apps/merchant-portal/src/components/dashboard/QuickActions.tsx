import Button from "@/components/ui/Button";
import { Download, FileSpreadsheet, Search, Truck } from "lucide-react";
import Link from "next/link";

interface QuickActionsProps {
  invoiceUrl?: string | null;
}

export function QuickActions({ invoiceUrl }: QuickActionsProps) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="text-lg font-semibold text-primary">Quick Actions</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Link href="/book">
          <Button className="w-full justify-center gap-2" size="sm">
            <Truck className="h-4 w-4" />
            Book Delivery
          </Button>
        </Link>
        <Link href="/bulk">
          <Button className="w-full justify-center gap-2" size="sm" variant="outline">
            <FileSpreadsheet className="h-4 w-4" />
            Bulk Upload
          </Button>
        </Link>
        <Link href="/track">
          <Button className="w-full justify-center gap-2" size="sm" variant="outline">
            <Search className="h-4 w-4" />
            Track Shipment
          </Button>
        </Link>
        {invoiceUrl ? (
          <a href={invoiceUrl} target="_blank" rel="noopener noreferrer">
            <Button className="w-full justify-center gap-2" size="sm" variant="outline">
              <Download className="h-4 w-4" />
              Download Invoice
            </Button>
          </a>
        ) : (
          <Link href="/billing">
            <Button className="w-full justify-center gap-2" size="sm" variant="outline">
              <Download className="h-4 w-4" />
              View Invoices
            </Button>
          </Link>
        )}
      </div>
    </section>
  );
}
