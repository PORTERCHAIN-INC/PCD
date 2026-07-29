import { NextResponse } from "next/server";

/**
 * Cookie JWT exchange retired. Driver portal uses Clerk session like other portals.
 * Kept as no-op so old clients fail closed without minting Porterchain JWTs.
 */
export async function POST() {
  return NextResponse.json(
    { detail: "driver_cookie_jwt_retired", hint: "Use Clerk session + Bearer to driver-api" },
    { status: 410 }
  );
}

export async function DELETE() {
  return NextResponse.json({ ok: true });
}
