/**
 * Validate in-app return paths for Clerk forceRedirectUrl / middleware.
 * Rejects protocol-relative and external URLs.
 */
export function safeAppRedirect(
  raw: string | null | undefined,
  options: {
    fallback: string;
    blockPrefixes?: string[];
  }
): string {
  const { fallback, blockPrefixes = ["/sign-in", "/sign-up", "/login"] } = options;
  if (!raw) return fallback;
  const trimmed = raw.trim();
  if (!trimmed.startsWith("/") || trimmed.startsWith("//") || trimmed.startsWith("/\\")) {
    return fallback;
  }
  // Disallow scheme-ish paths
  if (trimmed.includes("://")) return fallback;

  const pathOnly = trimmed.split("?")[0]?.split("#")[0] ?? trimmed;
  for (const prefix of blockPrefixes) {
    if (pathOnly === prefix || pathOnly.startsWith(`${prefix}/`)) {
      return fallback;
    }
  }
  return trimmed;
}
