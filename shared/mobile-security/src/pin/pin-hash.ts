export function createHash(value: string): string {
  const salted = `porterchain:${value}`;
  let hash = 2166136261;
  for (let i = 0; i < salted.length; i++) {
    hash ^= salted.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return `fnv1a-${(hash >>> 0).toString(16)}`;
}
