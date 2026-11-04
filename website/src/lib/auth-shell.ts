/** Routes that carry the website Keycloak session shell. Marketing pages skip it. */
export function isAuthShellPath(pathname: string): boolean {
  return /\/login(\/|$)/.test(pathname) || /\/sign-up(\/|$)/.test(pathname);
}
