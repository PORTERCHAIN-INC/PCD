import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const API_BASE = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
  /\/$/,
  ""
);

const ACCESS_COOKIE = "driver_access_token";
const REFRESH_COOKIE = "driver_refresh_token";

type RouteContext = { params: Promise<{ path: string[] }> };

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

async function refreshDriverTokens(refreshToken: string) {
  const res = await fetch(`${API_BASE}/driver-api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) return null;
  return (await res.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in?: number;
  };
}

function applyTokenCookies(
  response: NextResponse,
  tokens: { access_token: string; refresh_token: string; expires_in?: number }
) {
  const accessMaxAge = tokens.expires_in ?? 60 * 60;
  response.cookies.set(ACCESS_COOKIE, tokens.access_token, cookieOptions(accessMaxAge));
  response.cookies.set(REFRESH_COOKIE, tokens.refresh_token, cookieOptions(60 * 60 * 24 * 30));
}

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const jar = await cookies();
  let token = jar.get(ACCESS_COOKIE)?.value;
  const refreshToken = jar.get(REFRESH_COOKIE)?.value;

  if (!token) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }

  const suffix = path.join("/");
  const url = new URL(request.url);
  const target = `${API_BASE}/driver-api/${suffix}${url.search}`;
  const requestBody =
    request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();

  const buildInit = (accessToken: string): RequestInit => {
    const headers = new Headers(request.headers);
    headers.set("Authorization", `Bearer ${accessToken}`);
    headers.delete("host");
    return {
      method: request.method,
      headers,
      body: requestBody,
    };
  };

  let upstream = await fetch(target, buildInit(token));
  let refreshedTokens: { access_token: string; refresh_token: string; expires_in?: number } | null =
    null;

  if (upstream.status === 401 && refreshToken) {
    refreshedTokens = await refreshDriverTokens(refreshToken);
    if (refreshedTokens) {
      token = refreshedTokens.access_token;
      upstream = await fetch(target, buildInit(token));
    }
  }

  const contentType = upstream.headers.get("content-type") ?? "application/json";
  const disposition = upstream.headers.get("content-disposition");
  const body = await upstream.arrayBuffer();
  const responseHeaders: Record<string, string> = { "Content-Type": contentType };
  if (disposition) responseHeaders["Content-Disposition"] = disposition;

  const response = new NextResponse(body, { status: upstream.status, headers: responseHeaders });
  if (refreshedTokens) {
    applyTokenCookies(response, refreshedTokens);
  }
  return response;
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
