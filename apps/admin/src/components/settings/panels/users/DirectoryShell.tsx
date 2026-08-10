"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { Button, Spinner } from "@/components/crm/primitives";
import {
  settingsApi,
  type PlatformUser,
  type StaffUser,
  type UserDirectoryFilters,
  type UserDirectoryTab,
} from "@/lib/settings";
import { SettingsCard } from "../../ui/SettingsPrimitives";
import { tabMeta } from "./constants";
import { CreateDriverModal } from "./driver/CreateDriverModal";
import { AddMerchantSeatModal } from "./merchant/AddMerchantSeatModal";
import { requireApiToken } from "./requireApiToken";
import { ChangeRoleModal } from "./staff/ChangeRoleModal";
import { EMPTY_ENROLL_FORM, EnrollStaffModal, type EnrollForm } from "./staff/EnrollStaffModal";
import { EMPTY_FILTERS, filterChromeFor, UserFiltersBar } from "./UserFiltersBar";
import { UserDirectoryTable } from "./UserDirectoryTable";
import { useUserDirectory, usersQueryKey } from "./useUserDirectory";

function staffFromPlatform(user: PlatformUser): StaffUser {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role ?? "read_only",
    created_at: user.created_at,
  };
}

function cardDescription(tab: UserDirectoryTab): string {
  if (tab === "customer") {
    return "Retail customers self SignUp on PorterChain Platform — Admin cannot create or invite them.";
  }
  if (tab === "staff") {
    return "Provisioned admin users — enroll via staff IdP; reissue activation link if session expired";
  }
  if (tab === "merchant") {
    return "B2B portal seats by organization — teammates self SignUp; no Clerk invites";
  }
  return tabMeta(tab).description;
}

export function DirectoryShell({
  tab,
  enabled,
  getApiToken,
  onRefetch,
}: {
  tab: UserDirectoryTab;
  enabled: boolean;
  getApiToken: () => Promise<string | null>;
  onRefetch?: () => void;
}) {
  const qc = useQueryClient();
  const [filters, setFilters] = useState<UserDirectoryFilters>(EMPTY_FILTERS);
  const [createOpen, setCreateOpen] = useState(false);
  const [roleModal, setRoleModal] = useState<StaffUser | null>(null);
  const [enrollOpen, setEnrollOpen] = useState(false);
  const [enrollForm, setEnrollForm] = useState<EnrollForm>(EMPTY_ENROLL_FORM);
  const [enrollError, setEnrollError] = useState<string | null>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [enrollmentToken, setEnrollmentToken] = useState<string | null>(null);
  const [reissueBusy, setReissueBusy] = useState<string | null>(null);

  const meta = tabMeta(tab);
  const chrome = filterChromeFor(tab);
  const { data, isLoading } = useUserDirectory(tab, filters, enabled, getApiToken);
  const users = data?.items ?? [];
  const facets = data?.facets;

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: usersQueryKey(tab) });
    onRefetch?.();
  };

  async function submitEnroll() {
    setEnrolling(true);
    setEnrollError(null);
    setEnrollmentToken(null);
    try {
      const result = await settingsApi.enrollStaff(await requireApiToken(getApiToken), {
        email: enrollForm.email.trim(),
        role: enrollForm.role,
        name: enrollForm.name.trim() || undefined,
      });
      setEnrollmentToken(result.enrollment_token ?? null);
      refresh();
    } catch (e) {
      setEnrollError(e instanceof Error ? e.message : "Enrollment failed");
    } finally {
      setEnrolling(false);
    }
  }

  async function reissueEnrollment(userId: string) {
    setReissueBusy(userId);
    setEnrollError(null);
    setEnrollmentToken(null);
    setEnrollOpen(true);
    try {
      const result = await settingsApi.reissueStaffEnrollment(
        await requireApiToken(getApiToken),
        userId
      );
      setEnrollmentToken(result.enrollment_token ?? null);
      setEnrollForm({ email: result.email, role: result.role, name: "" });
    } catch (e) {
      setEnrollError(e instanceof Error ? e.message : "Reissue failed");
    } finally {
      setReissueBusy(null);
    }
  }

  function closeEnroll() {
    setEnrollOpen(false);
    setEnrollmentToken(null);
    setEnrollError(null);
    setEnrollForm(EMPTY_ENROLL_FORM);
  }

  const actionButton =
    tab === "customer" ? undefined : tab === "staff" ? (
      <Button
        onClick={() => {
          setEnrollmentToken(null);
          setEnrollError(null);
          setEnrollForm(EMPTY_ENROLL_FORM);
          setEnrollOpen(true);
        }}
      >
        <UserPlus className="h-4 w-4" /> Add staff
      </Button>
    ) : (
      <Button onClick={() => setCreateOpen(true)}>
        <UserPlus className="h-4 w-4" /> {tab === "merchant" ? "Add seat" : "Add user"}
      </Button>
    );

  return (
    <>
      <SettingsCard title={meta.label} description={cardDescription(tab)} action={actionButton}>
        <UserFiltersBar
          filters={filters}
          facets={facets}
          showAccountFilter={chrome.showAccountFilter}
          showInviteFilter={chrome.showInviteFilter}
          showClerkFilters={chrome.showClerkFilters}
          onChange={setFilters}
          onClear={() => setFilters(EMPTY_FILTERS)}
        />
        {isLoading ? (
          <Spinner />
        ) : (
          <>
            <p className="mb-3 text-xs text-muted">
              Showing {data?.total ?? 0}{" "}
              {tab === "staff"
                ? `staff member${(data?.total ?? 0) === 1 ? "" : "s"}`
                : `user${(data?.total ?? 0) === 1 ? "" : "s"}`}
              {tab === "driver"
                ? data?.clerk_synced
                  ? ` · ${data.clerk_total ?? 0} in Clerk`
                  : " · Clerk sync unavailable"
                : null}
            </p>
            <UserDirectoryTable
              users={users}
              tab={tab}
              getApiToken={getApiToken}
              onMutate={refresh}
              rowActions={
                tab === "staff"
                  ? (user) => (
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="outline"
                          onClick={() => setRoleModal(staffFromPlatform(user))}
                        >
                          Change role
                        </Button>
                        {user.provisioned && !user.id.startsWith("clerk:") && (
                          <Button
                            variant="ghost"
                            className="text-xs"
                            disabled={reissueBusy === user.id}
                            onClick={() => void reissueEnrollment(user.id)}
                          >
                            {reissueBusy === user.id ? "Reissuing…" : "Reissue activate link"}
                          </Button>
                        )}
                      </div>
                    )
                  : undefined
              }
            />
          </>
        )}
      </SettingsCard>

      {tab === "staff" && (
        <>
          <EnrollStaffModal
            open={enrollOpen}
            form={enrollForm}
            enrollmentToken={enrollmentToken}
            error={enrollError}
            busy={enrolling}
            onClose={closeEnroll}
            onFormChange={setEnrollForm}
            onEnroll={() => void submitEnroll()}
          />
          {roleModal && (
            <ChangeRoleModal
              user={roleModal}
              onClose={() => setRoleModal(null)}
              onSaved={() => onRefetch?.()}
            />
          )}
        </>
      )}

      {tab === "driver" && (
        <CreateDriverModal
          open={createOpen}
          getApiToken={getApiToken}
          onClose={() => setCreateOpen(false)}
          onCreated={refresh}
        />
      )}

      {tab === "merchant" && (
        <AddMerchantSeatModal
          open={createOpen}
          getApiToken={getApiToken}
          onClose={() => setCreateOpen(false)}
          onCreated={refresh}
        />
      )}
    </>
  );
}
