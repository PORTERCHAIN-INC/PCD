import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const API_BASE = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
  /\/$/,
  ""
);

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const { getToken, userId } = await auth();
  if (!userId) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }
  const token = await getToken();
  if (!token) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }

  const parts = path[0] === "v1" ? path.slice(1) : path;
  const url = new URL(request.url);
  const target = `${API_BASE}/driver-api/v1/${parts.join("/")}${url.search}`;
  const requestBody =
    request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();

  const headers = new Headers(request.headers);
  headers.set("Authorization", `Bearer ${token}`);
  headers.delete("host");

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
