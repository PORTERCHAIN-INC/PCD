/**
 * Two kinds of failure, never mixed:
 * - NetworkError: no HTTP response (offline, DNS, timeout). Safe to queue and replay later.
 * - ApiError: the server answered and said no (4xx/5xx). Show it to the driver; never queue.
 */
export class NetworkError extends Error {
  readonly kind = "network" as const;
  constructor(message = "network_unavailable") {
    super(message);
    this.name = "NetworkError";
  }
}

export class ApiError extends Error {
  readonly kind = "api" as const;
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function isNetworkError(err: unknown): err is NetworkError {
  return err instanceof NetworkError || (err as { kind?: string } | null)?.kind === "network";
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError || (err as { kind?: string } | null)?.kind === "api";
}
