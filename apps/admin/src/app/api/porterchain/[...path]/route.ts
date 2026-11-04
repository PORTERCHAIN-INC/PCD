import { NextRequest, NextResponse } from "next/server";
import { auth } from "@porterchain/auth/oidc/next";

/**
 * Admin BFF — attach the Keycloak `pc-admin` access token from the HttpOnly session.
 * The browser never holds the token for HTTP calls.
 */
// Server-side BFF: prefer the in-cluster URL (containers may not reach the public/LAN host).
const API_BASE = (
  process.env.PORTERCHAIN_API_INTERNAL_URL ??
  process.env.PORTERCHAIN_API_URL ??
  process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ??
  "http://localhost:8001"
).replace(/\/$/, "");

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  if (!path?.length) {
    return NextResponse.json({ detail: "path_required" }, { status: 400 });
  }

  const url = new URL(request.url);
  const target = `${API_BASE}/${path.join("/")}${url.search}`;
  const incomingAuth = (request.headers.get("authorization") || "").trim();
  const isDevBearer = incomingAuth === "Bearer dev";
  const token = isDevBearer ? null : await (await auth()).getToken();

  if (!isDevBearer && !token) {
    return NextResponse.json({ detail: "missing_bearer_token" }, { status: 401 });
  }

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  const accept = request.headers.get("accept");
  if (accept) headers.set("Accept", accept);
  const xRole = request.headers.get("x-admin-role");
  if (xRole) headers.set("X-Admin-Role", xRole);

  if (isDevBearer) {
    headers.set("Authorization", "Bearer dev");
  } else {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const requestBody =
    request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: requestBody,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "porterchain_api_unreachable" }, { status: 502 });
  }

  const responseType = upstream.headers.get("content-type") ?? "application/json";
  const disposition = upstream.headers.get("content-disposition");
  const body = await upstream.arrayBuffer();
  const responseHeaders: Record<string, string> = { "Content-Type": responseType };
  if (disposition) responseHeaders["Content-Disposition"] = disposition;

  return new NextResponse(body, { status: upstream.status, headers: responseHeaders });
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
