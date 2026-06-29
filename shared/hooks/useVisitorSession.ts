/**
 * Visitor session hook — anonymous tracking before Clerk auth.
 * Infrastructure stub; website uses website/src/lib/anonymous-session.ts today.
 */
export function useVisitorSession(): {
  sessionId: string;
  isReady: boolean;
} {
  return { sessionId: "", isReady: false };
}
