"use client";

import { Button, Field, Input, Modal, Select } from "@/components/crm/primitives";
import { isLocalDev } from "@/lib/env";
import { ADMIN_ROLES } from "@/lib/settings";

export type EnrollForm = { email: string; role: string; name: string };

export const EMPTY_ENROLL_FORM: EnrollForm = {
  email: "",
  role: "dispatcher",
  name: "",
};

export function EnrollStaffModal({
  open,
  form,
  enrollmentToken,
  error,
  busy,
  onClose,
  onFormChange,
  onEnroll,
}: {
  open: boolean;
  form: EnrollForm;
  enrollmentToken: string | null;
  error: string | null;
  busy: boolean;
  onClose: () => void;
  onFormChange: (form: EnrollForm) => void;
  onEnroll: () => void;
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add staff member"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            {enrollmentToken ? "Done" : "Cancel"}
          </Button>
          {!enrollmentToken && (
            <Button disabled={!form.email || busy} onClick={onEnroll}>
              {busy ? "Enrolling…" : "Enroll"}
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-4">
        {enrollmentToken && (
          <div className="rounded-xl border border-green-200 bg-green-50/80 p-3 text-sm text-green-950">
            <p className="font-medium">{enrollmentToken}</p>
            <p className="mt-2 text-xs text-muted">
              {isLocalDev()
                ? "Mailpit: localhost:8025. Setup happens on the Keycloak page (password + authenticator)."
                : "Setup happens on the Keycloak page. Use “Resend setup email” if the link expires."}
            </p>
          </div>
        )}
        <Field label="Work email">
          <Input
            type="email"
            placeholder="name@porterchain.com"
            value={form.email}
            onChange={(e) => onFormChange({ ...form, email: e.target.value })}
            disabled={Boolean(enrollmentToken)}
          />
        </Field>
        <Field label="Display name">
          <Input
            value={form.name}
            onChange={(e) => onFormChange({ ...form, name: e.target.value })}
          />
        </Field>
        <Field label="Role">
          <Select
            value={form.role}
            onChange={(e) => onFormChange({ ...form, role: e.target.value })}
          >
            {ADMIN_ROLES.map((r) => (
              <option key={r} value={r}>
                {r.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </Field>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}
