"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { driverApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const tokens = await driverApi.login(email);
      localStorage.setItem("driver_access_token", tokens.access_token);
      localStorage.setItem("driver_refresh_token", tokens.refresh_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "login_failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--gray-bg)] p-6">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="text-xl font-bold">Porterchain Driver</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">Sign in with your partner email</p>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="driver@example.com"
          className="mt-6 w-full rounded-xl border px-4 py-3"
        />
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          className="mt-4 w-full rounded-xl bg-[var(--secondary)] py-3 font-semibold text-white"
        >
          Sign in
        </button>
      </form>
    </div>
  );
}
