"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import FinanceInvoiceDetailView from "@/components/finance/FinanceInvoiceDetailView";
import { financeApi } from "@/lib/finance";

export default function FinanceInvoicePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();

  const { data: detail, isLoading } = useQuery({
    queryKey: ["finance-invoice", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => financeApi.invoiceDetail(await getApiToken(), id),
  });

  return <FinanceInvoiceDetailView detail={detail ?? null} loading={isLoading} />;
}
