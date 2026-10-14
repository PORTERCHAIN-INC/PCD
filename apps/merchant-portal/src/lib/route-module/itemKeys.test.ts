import assert from "node:assert/strict";
import test from "node:test";

import { itemKeys } from "./toRouteImport.ts";
import type { Parcel } from "./types.ts";

const box = (id: string, same = false) => ({ id, sameItemAsPrevious: same }) as unknown as Parcel;

test("boxes marked 'same item as above' share one item_key; others stay separate", () => {
  const keys = itemKeys([box("a"), box("b", true), box("c"), box("d", true), box("e", true)]);
  assert.equal(keys[0], "item-a");
  assert.equal(keys[1], "item-a");
  assert.equal(keys[2], "item-c");
  assert.deepEqual([keys[3], keys[4]], ["item-c", "item-c"]);
  assert.deepEqual(itemKeys([box("x"), box("y")]), [undefined, undefined]);
});
