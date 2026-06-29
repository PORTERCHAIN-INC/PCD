"use client";

import Link from "next/link";
import { SignIn } from "@clerk/nextjs";
import { isClerkConfigured } from "@/lib/env";

export default function SignInPage() {
  if (!isClerkConfigured()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
        <div className="w-full max-w-md rounded-2xl border border-primary/10 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-primary">Porterchain Merchant Portal</h1>
          <p className="mt-2 text-sm text-muted">
            Clerk is not configured for local development, so the sign-in widget cannot load.
          </p>
          <div className="mt-6 space-y-3 rounded-xl bg-gray-bg p-4 text-sm text-primary/80">
            <p className="font-medium text-primary">To enable Clerk sign-in:</p>
            <ol className="list-decimal space-y-1 pl-5">
              <li>
                Copy <code className="rounded bg-white px-1">env/merchant-portal.env.example</code>{" "}
                to <code className="rounded bg-white px-1">apps/merchant-portal/.env.local</code>
              </li>
              <li>
                Set <code className="rounded bg-white px-1">NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code>{" "}
                and <code className="rounded bg-white px-1">CLERK_SECRET_KEY</code>
              </li>
              <li>
                In Clerk dashboard, allow{" "}
                <code className="rounded bg-white px-1">http://localhost:3001</code>
              </li>
              <li>
                Restart <code className="rounded bg-white px-1">pnpm dev:merchant</code>
              </li>
            </ol>
          </div>
          <Link
            href="/dashboard"
            className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8]"
          >
            Continue in dev mode (no auth)
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-primary">Porterchain Merchant Portal</h1>
          <p className="mt-2 text-sm text-muted">Sign in with your approved business account</p>
        </div>
        <SignIn routing="hash" signUpUrl="/sign-in" />
      </div>
    </div>
  );
}
