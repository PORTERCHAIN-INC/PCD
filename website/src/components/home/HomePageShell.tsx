"use client";

import type { ReactNode } from "react";
import { BookingProvider } from "@/context/BookingContext";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";

export default function HomePageShell({ children }: { children: ReactNode }) {
  return (
    <GoogleMapsProvider>
      <BookingProvider>{children}</BookingProvider>
    </GoogleMapsProvider>
  );
}
