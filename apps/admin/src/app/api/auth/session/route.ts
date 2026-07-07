import { auth } from "@clerk/nextjs/server";

/** Server-side session probe — used by /sign-in to avoid client/server auth mismatch loops. */
export async function GET() {
  const { userId } = await auth();
  return Response.json({ signedIn: Boolean(userId) });
}
