/** Clerk session tokens live ~60s: fetch one per request, never cache it in state. */
export async function withFreshToken<T>(
  getToken: () => Promise<string>,
  call: (token: string) => Promise<T>
): Promise<T> {
  return call(await getToken());
}
