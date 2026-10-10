import { describe, expect, it } from "vitest";
import { isTypingTarget, shortcutFor } from "./dispatch-shortcuts";

describe("dispatch shortcuts", () => {
  it("maps digits to tabs and letters to actions", () => {
    expect(shortcutFor("1")).toEqual({ kind: "tab", index: 0 });
    expect(shortcutFor("5")).toEqual({ kind: "tab", index: 4 });
    expect(shortcutFor("6")).toBeNull();
    expect(shortcutFor("a")).toEqual({ kind: "approve" });
    expect(shortcutFor("P")).toEqual({ kind: "plan" });
    expect(shortcutFor("n")).toEqual({ kind: "new" });
    expect(shortcutFor("r")).toEqual({ kind: "refresh" });
    expect(shortcutFor("?")).toEqual({ kind: "help" });
    expect(shortcutFor("Escape")).toEqual({ kind: "close" });
    expect(shortcutFor("x")).toBeNull();
  });

  it("ignores keys while typing", () => {
    expect(isTypingTarget({ tagName: "INPUT" } as unknown as EventTarget)).toBe(true);
    expect(
      isTypingTarget({ tagName: "DIV", isContentEditable: false } as unknown as EventTarget)
    ).toBe(false);
    expect(isTypingTarget(null)).toBe(false);
  });
});
