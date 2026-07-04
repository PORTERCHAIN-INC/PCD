"use client";

import Link from "next/link";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-bg p-4">
      <div className="w-full max-w-md rounded-2xl border border-primary/10 bg-white p-8 shadow-sm text-center">
        <h1 className="text-2xl font-bold text-primary">Invitation required</h1>
        <p className="mt-3 text-sm text-muted leading-relaxed">
          Merchant accounts are invite-only. A Porterchain administrator or your account owner must
          send you a Clerk invitation before you can access the merchant portal.
        </p>
        <p className="mt-4 text-sm text-muted">
          Retail customers can sign up on{" "}
          <a href="https://porterchain.com" className="font-medium text-secondary hover:underline">
            porterchain.com
          </a>{" "}
          to book deliveries.
        </p>
        <Link
          href="/sign-in"
          className="mt-8 inline-flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8]"
        >
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
