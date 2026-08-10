"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Field, Input, Modal, Select } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { ADMIN_ROLES, settingsApi, type StaffUser } from "@/lib/settings";
import { usersQueryKey } from "../useUserDirectory";

export function ChangeRoleModal({
  user,
  onClose,
  onSaved,
}: {
  user: StaffUser;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const qc = useQueryClient();
  const [role, setRole] = useState(user.role);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await settingsApi.updateStaffRole(await getApiToken(), user.id, role, reason || undefined);
      void qc.invalidateQueries({ queryKey: usersQueryKey("staff") });
      onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Change role — ${user.email}`}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={saving} onClick={() => void save()}>
            {saving ? "Saving…" : "Update role"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="New role">
          <Select value={role} onChange={(e) => setRole(e.target.value)}>
            {ADMIN_ROLES.map((r) => (
              <option key={r} value={r}>
                {r.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Reason (audit)">
          <Input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Optional"
          />
        </Field>
      </div>
    </Modal>
  );
}
