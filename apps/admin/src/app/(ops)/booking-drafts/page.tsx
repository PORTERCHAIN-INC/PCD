"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const BookingDraftsListClient = dynamic(
  () => import("@/components/booking-drafts/BookingDraftsListClient"),
  { loading: () => <Spinner label="Loading drafts…" /> }
);

export default function BookingDraftsPage() {
  return <BookingDraftsListClient />;
}
