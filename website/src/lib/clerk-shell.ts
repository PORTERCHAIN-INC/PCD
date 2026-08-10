/** Client routes that need the Clerk browser SDK (~300KB). Marketing pages skip it. */
export function isClerkClientShellPath(pathname: string): boolean {
  return /\/login(\/|$)/.test(pathname) || /\/sign-up(\/|$)/.test(pathname);
}
