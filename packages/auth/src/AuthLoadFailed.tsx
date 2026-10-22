"use client";

/** Clear failure card with a retry, shown instead of an endless sign-in spinner. */
export function AuthLoadFailed({
  title = "Sign-in could not load",
  body = "The secure sign-in form did not load. Check your connection, turn off ad blockers or strict tracking protection for this page, then try again. Need help? support@porterchain.com",
  retry = "Try again",
}: {
  title?: string;
  body?: string;
  retry?: string;
}) {
  const offline = typeof navigator !== "undefined" && navigator.onLine === false;
  return (
    <div
      role="alert"
      data-testid="auth-load-failed"
      className="mx-auto mt-6 max-w-md rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
    >
      <p className="font-semibold">{offline ? "You are offline" : title}</p>
      <p className="mt-1 leading-relaxed">
        {offline ? "Reconnect to the internet, then try again." : body}
      </p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="mt-3 rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-700"
      >
        {retry}
      </button>
    </div>
  );
}
