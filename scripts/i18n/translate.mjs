// en strings json -> fr dictionary via self-hosted LibreTranslate (+ glossary, + existing fr kept).
// Usage: node scripts/i18n/translate.mjs strings.json out-fr.json
import fs from "fs";
const [inF, outF] = process.argv.slice(2);
const LT = process.env.LT_URL ?? "http://127.0.0.1:58090";
const strs = JSON.parse(fs.readFileSync(inF, "utf8"));
const gl = JSON.parse(fs.readFileSync(new URL("./glossary-fr.json", import.meta.url), "utf8"));
const pairs =
  process.env.PAIRS_IN && fs.existsSync(process.env.PAIRS_IN)
    ? JSON.parse(fs.readFileSync(process.env.PAIRS_IN, "utf8"))
    : {};
const prev = fs.existsSync(outF) ? JSON.parse(fs.readFileSync(outF, "utf8")) : {};
const out = { ...prev };
const todo = strs.filter((s) => !(s in out) && !(s in gl) && !(s in pairs));
const ph = (s) => (s.match(/\{\d+\}/g) || []).sort().join();
for (let i = 0; i < todo.length; i += 40) {
  const q = todo.slice(i, i + 40);
  const r = await fetch(`${LT}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ q, source: "en", target: "fr", format: "text" }),
  });
  const j = await r.json();
  q.forEach((s, k) => {
    const t = j.translatedText?.[k];
    if (t && ph(t) === ph(s)) out[s] = t;
  });
  process.stderr.write(`${Math.min(i + 40, todo.length)}/${todo.length}\r`);
}
Object.assign(out, pairs, gl);
// Brand and product names are never translated.
for (const k of Object.keys(out)) {
  out[k] = out[k]
    .replace(
      /Porte[- ]cha[iî]ne|Cha[iî]ne de porteurs?/gi,
      /PorterChain/.test(k) ? "PorterChain" : "Porterchain"
    )
    .replace(/PorterChain de le/g, "PorterChain du")
    // Courier vocabulary: a driver is a "chauffeur", never a "pilote" / "conducteur".
    .replace(/\bpilotes\b/g, "chauffeurs")
    .replace(/\bpilote\b/g, "chauffeur")
    .replace(/\bPilote\b/g, "Chauffeur");
}
const sorted = Object.fromEntries(
  Object.keys(out)
    .sort()
    .map((k) => [k, out[k]])
);
fs.writeFileSync(outF, JSON.stringify(sorted, null, 1) + "\n");
console.error(`\n${Object.keys(sorted).length} entries -> ${outF}`);
