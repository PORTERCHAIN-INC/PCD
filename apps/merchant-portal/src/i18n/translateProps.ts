import { getLocale, tr } from "./core";

/** Text-bearing props translated at element creation. */
const TEXT_PROPS = [
  "placeholder",
  "title",
  "aria-label",
  "alt",
  "label",
  "description",
  "subtitle",
  "heading",
  "hint",
  "helperText",
  "emptyText",
  "emptyTitle",
  "emptyDescription",
  "eyebrow",
  "action",
  "actionLabel",
  "confirmLabel",
  "cancelLabel",
  "message",
  "caption",
  "tooltip",
];
const SKIP_TYPES = new Set(["code", "pre", "script", "style", "textarea", "kbd"]);

function child(c: unknown): unknown {
  if (typeof c === "string") return tr(c);
  if (Array.isArray(c)) {
    let changed = false;
    const next = c.map((x) => {
      const y = child(x);
      if (y !== x) changed = true;
      return y;
    });
    return changed ? next : c;
  }
  return c;
}

export function translateProps(type: unknown, props: Record<string, unknown> | null | undefined) {
  if (getLocale() === "en" || !props) return props;
  if (typeof type === "string" && SKIP_TYPES.has(type)) return props;
  if (props["data-no-i18n"] !== undefined || props.translate === "no") return props;
  let out: Record<string, unknown> | null = null;
  const set = (k: string, v: unknown) => {
    out ??= { ...props };
    out[k] = v;
  };
  if ("children" in props) {
    const c = child(props.children);
    if (c !== props.children) set("children", c);
  }
  for (const k of TEXT_PROPS) {
    const v = props[k];
    if (typeof v === "string") {
      const t = tr(v);
      if (t !== v) set(k, t);
    }
  }
  return out ?? props;
}
