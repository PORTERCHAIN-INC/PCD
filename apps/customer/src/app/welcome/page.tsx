import { Suspense } from "react";
import WelcomeClient from "./welcome-client";

export const dynamic = "force-dynamic";

export default function WelcomePage() {
  return (
    <Suspense fallback={null}>
      <WelcomeClient />
    </Suspense>
  );
}
