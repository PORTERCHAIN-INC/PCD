"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const BookSuccessClient = dynamic(() => import("@/components/booking/BookSuccessClient"), {
  loading: () => (
    <div className="p-8">
      <PageSkeleton rows={3} />
    </div>
  ),
});

export default function BookSuccessPage() {
  return <BookSuccessClient />;
}
