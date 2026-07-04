"use client";

import Link from "next/link";
import { SignIn } from "@clerk/nextjs";
import { Shield } from "lucide-react";
import { isClerkConfigured } from "@/lib/env";

export default function SignInPage() {
  if (!isClerkConfigured()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
        <div className="w-full max-w-md rounded-2xl border border-primary/10 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-primary">Porterchain Admin</h1>
          <p className="mt-2 text-sm text-muted">
            Clerk is not configured. Local dev uses API bypass — add staff in{" "}
            <code className="rounded bg-gray-bg px-1">admin_users</code> for production-like
            testing.
          </p>
          <Link
            href="/dashboard"
            className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-secondary/90"
          >
            Continue in dev mode
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-bg p-4">
      <div className="mb-6 max-w-md text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/10">
          <Shield className="h-7 w-7 text-secondary" />
        </div>
        <h1 className="text-2xl font-bold text-primary">Porterchain Admin</h1>
        <p className="mt-2 text-sm text-muted">
          Staff-only access. You must be provisioned in Admin Settings → Staff before you can use
          this console. Creating a Clerk account alone does not grant access.
        </p>
      </div>
      <SignIn
        routing="hash"
        appearance={{
          elements: {
            footerAction: { display: "none" },
            footerActionLink: { display: "none" },
          },
        }}
      />
      <p className="mt-6 max-w-sm text-center text-xs text-muted">
        Need access? Ask a super admin to add your work email to the staff list.
      </p>
    </div>
  );
}
