export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function parseApiError(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const json = JSON.parse(text) as {
      error?: string;
      message?: string;
      detail?: string;
    };
    return json.error ?? json.message ?? json.detail ?? text;
  } catch {
    return text || `HTTP ${res.status}`;
  }
}
