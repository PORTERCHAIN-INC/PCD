import assert from "node:assert/strict";
import { test } from "node:test";
import { portalForClient, portalOrigin, portalRedirect, portalsForRoles } from "./oidc/portals.ts";

test("roles map to portals, staff first", () => {
  assert.deepEqual(portalsForRoles(["customer", "super_admin"]), ["admin"]);
  assert.deepEqual(portalsForRoles(["merchant_viewer", "customer"]), ["merchant"]);
  assert.deepEqual(portalsForRoles(["driver", "offline_access"]), ["driver"]);
  assert.deepEqual(portalsForRoles(["customer", "offline_access"]), ["customer"]);
  assert.deepEqual(portalsForRoles(["offline_access"]), []);
  assert.deepEqual(portalsForRoles(["super_admin", "merchant_owner", "customer"]), [
    "admin",
    "merchant",
  ]);
});

test("stay when allowed; otherwise go to the user's own portal", () => {
  assert.equal(portalRedirect("admin", ["super_admin", "customer"]), null);
  assert.equal(portalRedirect("customer", ["super_admin", "customer"]), "admin");
  assert.equal(portalRedirect("admin", ["customer"]), "customer");
  assert.equal(portalRedirect("customer", ["merchant_owner", "customer"]), "merchant");
  assert.equal(portalRedirect("merchant", ["super_admin", "merchant_owner"]), null);
  assert.equal(portalRedirect("customer", ["driver"]), "driver");
  assert.equal(portalRedirect("driver", ["merchant_owner", "customer"]), "merchant");
  assert.equal(portalRedirect("merchant", ["admin"]), "admin");
  assert.equal(portalRedirect("admin", []), null);
  assert.equal(portalRedirect(null, ["customer"]), null);
  assert.equal(portalForClient("pc-driver-portal"), "driver");
  assert.equal(portalForClient("pc-website"), null);
});

test("portal origin from env or host swap", () => {
  assert.equal(
    portalOrigin("driver", "admin", "https://admin.porterchain.com", {}),
    "https://driver.porterchain.com"
  );
  assert.equal(portalOrigin("driver", "admin", "http://192.168.1.5:53002", {}), null);
  assert.equal(
    portalOrigin("driver", "admin", "http://192.168.1.5:53002", {
      PC_PORTAL_URL_DRIVER: "http://192.168.1.5:53003/",
    }),
    "http://192.168.1.5:53003"
  );
});
