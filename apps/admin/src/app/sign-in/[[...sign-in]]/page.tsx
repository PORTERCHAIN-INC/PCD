"use client";

import Link from "next/link";
import { SignIn } from "@clerk/nextjs";
import { isClerkConfigured } from "@/lib/env";

export default function SignInPage() {
  if (!isClerkConfigured()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
        <div className="w-full max-w-md rounded-2xl border border-primary/10 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-primary">Porterchain Admin</h1>
          <p className="mt-2 text-sm text-muted">
            Clerk is not configured. Use dev mode locally or add Clerk keys to{" "}
            <code className="rounded bg-gray-bg px-1">apps/admin/.env.local</code>.
          </p>
          <Link
            href="/dashboard"
            className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8]"
          >
            Continue in dev mode
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md text-center">
        <h1 className="mb-6 text-2xl font-bold text-primary">Porterchain Admin</h1>
        <SignIn routing="hash" />
      </div>
    </div>
  );
}
