// Extract UI strings (JSX text, text-like attributes and string literals) from app sources.
// Usage: node scripts/i18n/extract.mjs apps/customer/src packages/ui/src > strings.json
import fs from "fs";
import path from "path";
import { createRequire } from "module";
const ts = createRequire(import.meta.url)(
  "/home/pcd/PCD/apps/customer/node_modules/typescript/lib/typescript.js"
);
const SKIP_ATTR = new Set([
  "className",
  "href",
  "src",
  "id",
  "key",
  "type",
  "name",
  "value",
  "style",
  "role",
  "htmlFor",
  "method",
  "action",
  "target",
  "rel",
  "as",
  "variant",
  "size",
  "tone",
  "color",
  "icon",
  "autoComplete",
  "inputMode",
  "pattern",
  "accept",
  "lang",
  "dir",
  "form",
  "testId",
  "sizes",
  "fetchPriority",
  "loading",
  "mode",
  "align",
  "side",
  "kind",
  "status",
  "tab",
  "intent",
  "returnTo",
  "redirectUrl",
]);
const norm = (s) => s.replace(/\s+/g, " ").trim();
const texty = (s) => {
  const t = norm(s);
  if (t.length < 2 || t.length > 400 || !/[A-Za-z]{2}/.test(t)) return false;
  if (/^(https?:|mailto:|tel:|\/|#|\.|@)/.test(t)) return false;
  if (/^[a-z0-9_.:\-\/\[\]]+$/.test(t)) return false;
  if (/^[A-Z0-9_]+$/.test(t) && t.includes("_")) return false;
  if (/^[a-z]+[A-Z][A-Za-z0-9]*$/.test(t)) return false; // L31: camelCase code identifiers
  if (/[{}<>;=]|=>|\bvar\(--/.test(t)) return false;
  if (
    /^(bg|text|border|flex|grid|rounded|px|py|mt|mb|w|h|min|max|inline|hidden|block|items|justify|gap|font|shadow|ring|hover|focus|sm|md|lg)[-:]/.test(
      t
    )
  )
    return false;
  return true;
};
const CALL_SKIP =
  /^(fetch|apiFetch|get|post|put|del|patch|request|cn|clsx|twMerge|startsWith|endsWith|includes|split|join|replace|getItem|setItem|removeItem|querySelector|querySelectorAll|addEventListener|get|has|set|delete|push|replaceState|useState|require|toLocaleString|toLocaleDateString|toLocaleTimeString|DateTimeFormat|NumberFormat|createElement|getElementById|matchMedia|error|warn|log|debug|info)$/;
const out = new Set();
const pairs = {}; // authored { en, fr } objects (packages/types) win over machine translation
function visit(f) {
  const src = fs.readFileSync(f, "utf8");
  const sf = ts.createSourceFile(
    f,
    src,
    ts.ScriptTarget.Latest,
    true,
    f.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );
  const walk = (n) => {
    if (ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) return;
    if (ts.isObjectLiteralExpression(n)) {
      const get = (k) =>
        n.properties.find(
          (x) =>
            ts.isPropertyAssignment(x) &&
            x.name.getText() === k &&
            ts.isStringLiteralLike(x.initializer)
        );
      const en = get("en"),
        fr = get("fr");
      if (en && fr) pairs[norm(en.initializer.text)] = norm(fr.initializer.text);
    }
    if (ts.isJsxText(n)) {
      const t = norm(n.getText());
      if (texty(t)) out.add(t);
    } else if (ts.isJsxAttribute(n)) {
      const name = n.name.getText();
      if (SKIP_ATTR.has(name) || name.startsWith("data-") || /^on[A-Z]/.test(name)) return;
    } else if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) {
      const p = n.parent;
      if (p && ts.isPropertyAssignment(p) && p.name === n) return;
      if (p && ts.isElementAccessExpression(p)) return;
      if (p && ts.isBinaryExpression(p) && /=/.test(p.operatorToken.getText())) return;
      if (p && (ts.isCaseClause(p) || ts.isLiteralTypeNode(p))) return;
      if (
        p &&
        (ts.isCallExpression(p) || ts.isNewExpression(p)) &&
        CALL_SKIP.test(p.expression.getText().split(".").pop() ?? "")
      )
        return;
      if (texty(n.text)) out.add(norm(n.text));
    } else if (ts.isTemplateExpression(n)) {
      let s = n.head.text;
      n.templateSpans.forEach((sp, i) => {
        s += `{${i}}` + sp.literal.text;
      });
      const bare = s.replace(/\{\d+\}/g, " ");
      if (texty(bare) && !/[\/=?&]/.test(bare)) out.add(norm(s));
    }
    ts.forEachChild(n, walk);
  };
  walk(sf);
}
function rec(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) {
      if (!/^(node_modules|\.next|__tests__|i18n)$/.test(e.name)) rec(p);
    } else if (/\.(tsx|ts)$/.test(e.name) && !/\.(test|spec|d)\.tsx?$/.test(e.name)) visit(p);
  }
}
for (const d of process.argv.slice(2)) rec(d);
for (const k of Object.keys(pairs)) out.add(k);
if (process.env.PAIRS_OUT) fs.writeFileSync(process.env.PAIRS_OUT, JSON.stringify(pairs));
console.log(JSON.stringify([...out].sort()));
