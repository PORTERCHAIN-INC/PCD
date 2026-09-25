"use client";

import dynamic from "next/dynamic";

const BookSuccessClient = dynamic(() => import("@/components/booking/BookSuccessClient"), {
  loading: () => <p className="p-8 text-sm text-muted">Loading…</p>,
});

export default function BookSuccessPage() {
  return <BookSuccessClient />;
}
