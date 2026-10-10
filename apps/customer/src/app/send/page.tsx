import { Suspense } from "react";
import SendClient from "@/components/send/SendClient";

export default function SendPage() {
  return (
    <Suspense fallback={null}>
      <SendClient />
    </Suspense>
  );
}
