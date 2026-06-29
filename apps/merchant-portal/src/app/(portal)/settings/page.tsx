"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { getProfile, updateProfile, type MerchantProfile } from "@/lib/api";
import { useEffect, useState } from "react";

export default function SettingsPage() {
  const { getApiToken, orgId, isSignedIn, isLoaded } = useMerchantAuth();
  const [profile, setProfile] = useState<MerchantProfile | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getApiToken();
      setProfile(await getProfile(token, orgId));
    })();
  }, [getApiToken, orgId, isLoaded, isSignedIn]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!profile) return;
    const token = await getApiToken();
    const updated = await updateProfile(
      token,
      {
        company_name: profile.company_name,
        phone: profile.phone || undefined,
        hst_number: profile.hst_number || undefined,
        business_number: profile.business_number || undefined,
      },
      orgId
    );
    setProfile(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  if (!profile) return <p className="text-muted">Loading profile…</p>;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-primary">Business Profile</h1>
      <form
        onSubmit={onSave}
        className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6"
      >
        <Field
          label="Company name"
          value={profile.company_name}
          onChange={(v) => setProfile({ ...profile, company_name: v })}
        />
        <Field label="Email" value={profile.email} onChange={() => {}} disabled />
        <Field
          label="Phone"
          value={profile.phone || ""}
          onChange={(v) => setProfile({ ...profile, phone: v })}
        />
        <Field
          label="HST number"
          value={profile.hst_number || ""}
          onChange={(v) => setProfile({ ...profile, hst_number: v })}
        />
        <Field
          label="Business number"
          value={profile.business_number || ""}
          onChange={(v) => setProfile({ ...profile, business_number: v })}
        />
        <div>
          <p className="text-sm font-medium text-primary">Payment terms</p>
          <p className="mt-1 text-sm text-muted">{profile.payment_terms.replace("_", " ")}</p>
        </div>
        <div>
          <p className="text-sm font-medium text-primary">Status</p>
          <p className="mt-1 text-sm text-muted">{profile.status}</p>
        </div>
        <Button type="submit">Save changes</Button>
        {saved && <p className="text-sm text-green-700">Profile saved</p>}
      </form>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-primary">{label}</label>
      <input
        disabled={disabled}
        className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm disabled:bg-gray-bg"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
