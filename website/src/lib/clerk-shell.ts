/** Client routes that need the Clerk browser SDK (~300KB). Marketing pages skip it. */
export function isClerkClientShellPath(pathname: string): boolean {
  return /\/(login|book)(\/|$)/.test(pathname);
}
