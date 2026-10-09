// Run: cd website && pnpm test:seo   (tsx --test …/client-messages.test.mts)
//
// Contract: every next-intl namespace a client component translates is shipped to the browser.
// Walks the client module graph ("use client" files + everything they import, which also runs
// in the browser) and checks each `useTranslations("ns")` against CLIENT_MESSAGE_NAMESPACES.
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, normalize, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { CLIENT_MESSAGE_NAMESPACES, pickMessages } from "./client-messages";

const SRC = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.(tsx|ts)$/.test(name) && !/\.test\./.test(name)) out.push(normalize(full));
  }
  return out;
}

const files = new Map(walk(SRC).map((f) => [f, readFileSync(f, "utf8")]));

function resolveImport(spec: string, from: string): string | undefined {
  let base: string;
  if (spec.startsWith("@/")) base = join(SRC, spec.slice(2));
  else if (spec.startsWith(".")) base = resolve(dirname(from), spec);
  else return undefined;
  for (const candidate of [
    `${base}.tsx`,
    `${base}.ts`,
    join(base, "index.tsx"),
    join(base, "index.ts"),
  ]) {
    const n = normalize(candidate);
    if (files.has(n)) return n;
  }
  return existsSync(base) && files.has(normalize(base)) ? normalize(base) : undefined;
}

const IMPORT_RE =
  /(?:import|export)\s[^'"]*?from\s*["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)/g;
const USE_T_RE = /useTranslations\(\s*([^)]*)\)/g;

function clientGraph(): string[] {
  const seen = new Set<string>();
  const stack = [...files.entries()]
    .filter(([, text]) => /^\s*["']use client["']/.test(text))
    .map(([file]) => file);
  while (stack.length) {
    const file = stack.pop()!;
    if (seen.has(file)) continue;
    seen.add(file);
    for (const m of files.get(file)!.matchAll(IMPORT_RE)) {
      const target = resolveImport(m[1] ?? m[2], file);
      if (target && !seen.has(target)) stack.push(target);
    }
  }
  return [...seen];
}

function covered(namespace: string): boolean {
  return CLIENT_MESSAGE_NAMESPACES.some(
    (allowed) => namespace === allowed || namespace.startsWith(`${allowed}.`)
  );
}

test("every client useTranslations namespace is shipped to the browser", () => {
  const missing: string[] = [];
  for (const file of clientGraph()) {
    for (const m of files.get(file)!.matchAll(USE_T_RE)) {
      const arg = m[1].trim();
      if (!arg) {
        missing.push(`${file}: useTranslations() without a namespace needs every message`);
        continue;
      }
      const literal = /^["'`]([^"'`$]*)/.exec(arg)?.[1];
      if (literal === undefined) {
        missing.push(`${file}: non-literal namespace ${arg}`);
        continue;
      }
      // Template literals (`legal.${id}`) must be covered by their static prefix.
      const namespace =
        arg.startsWith("`") && arg.includes("${") ? literal.replace(/\.$/, "") : literal;
      if (!covered(namespace)) missing.push(`${file}: ${namespace}`);
    }
  }
  assert.deepEqual(missing, []);
});

test("pickMessages keeps nesting and drops everything else", () => {
  const picked = pickMessages({ a: { b: { c: 1 }, d: 2 }, e: 3, f: { g: 4 } }, [
    "a.b",
    "f",
    "missing.ns",
  ]);
  assert.deepEqual(picked, { a: { b: { c: 1 } }, f: { g: 4 } });
});
