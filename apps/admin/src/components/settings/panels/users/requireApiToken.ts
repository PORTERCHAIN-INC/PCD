export async function requireApiToken(getApiToken: () => Promise<string | null>): Promise<string> {
  const token = await getApiToken();
  if (!token) throw new Error("unauthorized");
  return token;
}
