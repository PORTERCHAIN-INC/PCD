import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";
import { DRIVER_DEV_COOKIE } from "@/lib/driver-dev-cookie";

const API_BASE = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
  /\/$/,
  ""
);
const IMP_COOKIE = "pc_imp_bearer";

type RouteContext = { params: Promise<{ path: string[] }> };

function isDevLoginEnabled(): boolean {
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "false") return false;
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "true") return true;
  const appEnv = (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? "").trim();
  return appEnv === "local" || appEnv === "development";
}

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const { getToken, userId } = await auth();

  const parts = path[0] === "v1" ? path.slice(1) : path;
  const url = new URL(request.url);
  const target = `${API_BASE}/driver-api/v1/${parts.join("/")}${url.search}`;
  const requestBody =
    request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();

  const headers = new Headers(request.headers);
  headers.delete("host");

  const impBearer = request.cookies.get(IMP_COOKIE)?.value?.trim();
  if (impBearer?.startsWith("pc_imp_")) {
    headers.set("Authorization", `Bearer ${impBearer}`);
  } else if (userId) {
    const token = await getToken();
    if (!token) {
      return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
    }
    headers.set("Authorization", `Bearer ${token}`);
  } else if (isDevLoginEnabled()) {
    const driverId = request.cookies.get(DRIVER_DEV_COOKIE)?.value?.trim();
    if (!driverId) {
      return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
    }
    headers.delete("Authorization");
    headers.set("X-Driver-Id", driverId);
  } else {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }

  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: requestBody,
  });

  const contentType = upstream.headers.get("content-type") ?? "application/json";
  const disposition = upstream.headers.get("content-disposition");
  const body = await upstream.arrayBuffer();
  const responseHeaders: Record<string, string> = { "Content-Type": contentType };
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
