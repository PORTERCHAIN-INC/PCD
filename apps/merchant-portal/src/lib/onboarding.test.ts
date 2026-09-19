import assert from "node:assert/strict";
import test from "node:test";

import { merchantStatusLabel } from "./catalog.ts";
import { askOwnerForCompanyFile, waitCopy } from "./onboarding-copy.ts";
import type { PortalOnboardingStatus } from "./onboarding.ts";

function status(overrides: Partial<PortalOnboardingStatus> = {}): PortalOnboardingStatus {
  return {
    ready: false,
    blockers: [],
    status: "ONBOARDING",
    clerk_linked: true,
    steps: [],
    pending_documents: 0,
    can_access_portal: false,
    ...overrides,
  };
}

const copy = (data: PortalOnboardingStatus) => waitCopy(data, merchantStatusLabel);

test("waiting owner is told they can finish the company file", () => {
  const text = copy(status({ blockers: ["admin_authorization"], can_edit_company: true }));
  assert.match(text, /PorterChain is reviewing this company/);
  assert.match(text, /You can finish the company file/);
  assert.match(text, /Active/);
});

test("waiting dispatcher is not told to fix the company file", () => {
  const text = copy(status({ blockers: ["admin_authorization"], can_edit_company: false }));
  assert.match(text, /Your owner finishes the company file/);
  assert.doesNotMatch(text, /You can finish/);
});

test("seat turned off names the seat, not the company review", () => {
  const text = copy(status({ status: "ACTIVE", blockers: ["team_access"] }));
  assert.match(text, /Your seat is turned off/);
  assert.doesNotMatch(text, /reviewing/);
});

test("no seat yet points at the Team page", () => {
  const text = copy(status({ status: "ACTIVE", blockers: ["merchant_provisioned"] }));
  assert.match(text, /does not have a seat yet/);
  assert.match(text, /Team page/);
});

test("suspended and closed keep the admin glossary words", () => {
  assert.match(copy(status({ status: "SUSPENDED" })), /Suspended/);
  assert.match(copy(status({ status: "CLOSED" })), /Closed/);
});

test("wait copy never leaks internal role or status ids", () => {
  for (const s of ["PENDING", "ONBOARDING", "ACTIVE", "SUSPENDED", "CLOSED"]) {
    const text = copy(status({ status: s }));
    assert.doesNotMatch(text, /merchant_/);
    assert.doesNotMatch(text, new RegExp(s));
  }
});

test("company file nag only fires for a seat that cannot edit an incomplete file", () => {
  const incomplete = {
    complete: false,
    missing: ["hst_number"],
    missing_labels: ["HST number"],
    can_edit: false,
  };
  assert.equal(
    askOwnerForCompanyFile(status({ can_edit_company: false, completeness: incomplete })),
    true
  );
  assert.equal(
    askOwnerForCompanyFile(status({ can_edit_company: true, completeness: incomplete })),
    false
  );
  assert.equal(
    askOwnerForCompanyFile(
      status({
        can_edit_company: false,
        completeness: { complete: true, missing: [], missing_labels: [], can_edit: false },
      })
    ),
    false
  );
  assert.equal(
    askOwnerForCompanyFile(
      status({ blockers: ["team_access"], can_edit_company: false, completeness: incomplete })
    ),
    false
  );
});
