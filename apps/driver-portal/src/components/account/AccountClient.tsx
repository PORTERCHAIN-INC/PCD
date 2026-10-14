"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useClerk, useUser } from "@clerk/nextjs";
import {
  Camera,
  Check,
  ChevronRight,
  KeyRound,
  Languages,
  Laptop,
  LogOut,
  Mail,
  MapPin,
  Phone,
  ShieldCheck,
  Siren,
  User,
} from "lucide-react";
import DriverShell from "@/components/DriverShell";
import {
  accountApi,
  type DriverAddress,
  type DriverAppSettings,
  type DriverEmergencyContact,
  type DriverMeProfile,
} from "@/lib/api";
import { isClerkConfigured } from "@/lib/env";
import { cn, initials } from "@/lib/utils";

const PROVINCES = ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"];
const RELATIONSHIPS = ["spouse", "partner", "parent", "child", "sibling", "friend", "other"];
const FIELD_ERRORS: Record<string, string> = {
  required: "Required",
  invalid: "Check this value",
  too_long: "Too long",
  too_short: "Too short",
  too_large: "Photo is too large",
};

type Section = "personal" | "contact" | "security" | "preferences" | "privacy";
const SECTIONS: Array<{ id: Section; label: string; icon: typeof User }> = [
  { id: "personal", label: "Personal", icon: User },
  { id: "contact", label: "Email & phone", icon: Mail },
  { id: "security", label: "Security", icon: KeyRound },
  { id: "preferences", label: "Preferences", icon: Languages },
  { id: "privacy", label: "Privacy & legal", icon: ShieldCheck },
];

function errText(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e);
  try {
    const parsed = JSON.parse(msg) as { field?: string; code?: string };
    if (parsed.field) return `${parsed.field}: ${FIELD_ERRORS[parsed.code ?? ""] ?? parsed.code}`;
  } catch {
    /* plain */
  }
  const clerk = (e as { errors?: Array<{ longMessage?: string; message?: string }> })?.errors?.[0];
  return clerk?.longMessage || clerk?.message || msg || "Something went wrong";
}

export default function AccountClient({ version }: { version: string }) {
  const qc = useQueryClient();
  const [section, setSection] = useState<Section>("personal");
  const profileQ = useQuery({ queryKey: ["driver-me-profile"], queryFn: accountApi.profile });
  const settingsQ = useQuery({
    queryKey: ["driver-app-settings"],
    queryFn: async () => (await accountApi.settings()).settings,
  });
  const profile = profileQ.data;
  const setProfile = (p: DriverMeProfile) => qc.setQueryData(["driver-me-profile"], p);

  return (
    <DriverShell>
      <div className="mx-auto w-full max-w-5xl">
        <header className="flex items-center gap-5 pb-8">
          <Avatar profile={profile} size={72} />
          <div className="min-w-0">
            <h1 className="truncate text-3xl font-bold tracking-tight text-[var(--primary)]">
              {profile?.full_name ?? "Account"}
            </h1>
            <p className="mt-1 truncate text-sm text-[var(--muted)]">
              {profile?.email}
              {profile?.phone ? ` · ${profile.phone}` : ""}
            </p>
          </div>
          {profileQ.isFetching && profile ? (
            <span className="ml-auto text-xs text-[var(--muted)]" aria-live="polite">
              Syncing…
            </span>
          ) : null}
        </header>

        <div className="grid gap-6 md:grid-cols-[220px_1fr]">
          <nav aria-label="Account sections" className="flex gap-1 overflow-x-auto md:flex-col">
            {SECTIONS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setSection(id)}
                aria-current={section === id ? "page" : undefined}
                className={cn(
                  "flex shrink-0 items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-semibold transition",
                  section === id
                    ? "bg-[var(--primary)] text-white"
                    : "text-[var(--primary)] hover:bg-[var(--primary)]/5"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </nav>

          <main className="min-w-0">
            {!profile && profileQ.isLoading ? (
              <div className="h-72 animate-pulse rounded-2xl bg-white" />
            ) : !profile ? (
              <Card title="Account unavailable">
                <p className="text-sm text-[var(--muted)]">{errText(profileQ.error)}</p>
              </Card>
            ) : section === "personal" ? (
              <PersonalSection profile={profile} onSaved={setProfile} />
            ) : section === "contact" ? (
              <ContactSection profile={profile} onSynced={setProfile} />
            ) : section === "security" ? (
              <SecuritySection />
            ) : section === "preferences" ? (
              <PreferencesSection
                settings={settingsQ.data ?? {}}
                onSaved={(s) => qc.setQueryData(["driver-app-settings"], s)}
              />
            ) : (
              <PrivacySection version={version} />
            )}
          </main>
        </div>
      </div>
    </DriverShell>
  );
}

function Avatar({ profile, size }: { profile?: DriverMeProfile; size: number }) {
  if (profile?.photo_url) {
    return (
      // Data-URL avatar: next/image adds nothing here.
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={profile.photo_url}
        alt=""
        width={size}
        height={size}
        className="shrink-0 rounded-full object-cover ring-2 ring-[var(--accent)]"
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full bg-[var(--primary)] text-xl font-bold text-white"
      style={{ width: size, height: size }}
    >
      {initials(profile?.full_name ?? "")}
    </div>
  );
}

function Card({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="mb-5 rounded-2xl border border-[var(--primary)]/8 bg-white p-6">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-base font-bold text-[var(--primary)]">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  autoComplete,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  autoComplete?: string;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        {label}
      </span>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="h-11 w-full rounded-xl border border-[var(--primary)]/12 bg-[var(--gray-bg)] px-3.5 text-sm text-[var(--primary)] outline-none focus:border-[var(--secondary)] focus:bg-white"
      />
    </label>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-11 w-full rounded-xl border border-[var(--primary)]/12 bg-[var(--gray-bg)] px-3 text-sm text-[var(--primary)]"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function SaveBar({
  busy,
  msg,
  onSave,
  label = "Save",
}: {
  busy: boolean;
  msg: string | null;
  onSave: () => void;
  label?: string;
}) {
  return (
    <div className="mt-5 flex items-center gap-4">
      <button
        type="button"
        disabled={busy}
        onClick={onSave}
        className="h-11 rounded-xl bg-[var(--secondary)] px-6 text-sm font-bold text-white disabled:opacity-50"
      >
        {busy ? "Saving…" : label}
      </button>
      {msg ? (
        <span role="status" className="text-sm text-[var(--muted)]">
          {msg}
        </span>
      ) : null}
    </div>
  );
}

async function resizePhoto(file: File): Promise<string> {
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, 512 / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bmp.width * scale);
  canvas.height = Math.round(bmp.height * scale);
  canvas.getContext("2d")!.drawImage(bmp, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.85);
}

function PersonalSection({
  profile,
  onSaved,
}: {
  profile: DriverMeProfile;
  onSaved: (p: DriverMeProfile) => void;
}) {
  const [name, setName] = useState(profile.full_name);
  const blank: DriverAddress = { line1: "", line2: "", city: "", province: "ON", postal_code: "" };
  const [addr, setAddr] = useState<DriverAddress>(profile.address ?? blank);
  const blankEc: DriverEmergencyContact = { name: "", relationship: "spouse", phone: "" };
  const [ec, setEc] = useState<DriverEmergencyContact>(profile.emergency_contact ?? blankEc);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const save = async (body: Parameters<typeof accountApi.updateProfile>[0]) => {
    setBusy(true);
    setMsg(null);
    try {
      const out = await accountApi.updateProfile(body);
      onSaved(out.profile);
      setMsg(out.changed.length ? "Saved" : "No changes");
    } catch (e) {
      setMsg(errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Card title="Photo & name">
        <div className="flex items-center gap-5">
          <Avatar profile={profile} size={88} />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="inline-flex h-10 items-center gap-2 rounded-xl border border-[var(--primary)]/12 px-4 text-sm font-semibold"
            >
              <Camera className="h-4 w-4" /> Change photo
            </button>
            {profile.photo_url ? (
              <button
                type="button"
                onClick={() => save({ photo: null })}
                className="h-10 px-3 text-sm text-[var(--muted)]"
              >
                Remove
              </button>
            ) : null}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (f) await save({ photo: await resizePhoto(f) });
              e.target.value = "";
            }}
          />
        </div>
        <div className="mt-5 max-w-md">
          <Field label="Full legal name" value={name} onChange={setName} autoComplete="name" />
        </div>
        <SaveBar busy={busy} msg={msg} onSave={() => save({ full_name: name })} />
      </Card>

      <Card title="Home address">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Field
              label="Street"
              value={addr.line1}
              onChange={(v) => setAddr({ ...addr, line1: v })}
              autoComplete="address-line1"
            />
          </div>
          <Field
            label="Unit (optional)"
            value={addr.line2 ?? ""}
            onChange={(v) => setAddr({ ...addr, line2: v })}
            autoComplete="address-line2"
          />
          <Field
            label="City"
            value={addr.city}
            onChange={(v) => setAddr({ ...addr, city: v })}
            autoComplete="address-level2"
          />
          <Select
            label="Province"
            value={addr.province}
            options={PROVINCES.map((p) => ({ value: p, label: p }))}
            onChange={(v) => setAddr({ ...addr, province: v })}
          />
          <Field
            label="Postal code"
            value={addr.postal_code}
            onChange={(v) => setAddr({ ...addr, postal_code: v })}
            autoComplete="postal-code"
            placeholder="M5E 1W7"
          />
        </div>
        <SaveBar
          busy={busy}
          msg={msg}
          onSave={() => save({ address: { ...addr, line2: addr.line2 || null } })}
        />
      </Card>

      <Card title="Emergency contact" action={<Siren className="h-4 w-4 text-[var(--muted)]" />}>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Name" value={ec.name} onChange={(v) => setEc({ ...ec, name: v })} />
          <Select
            label="Relationship"
            value={ec.relationship}
            options={RELATIONSHIPS.map((r) => ({
              value: r,
              label: r[0].toUpperCase() + r.slice(1),
            }))}
            onChange={(v) => setEc({ ...ec, relationship: v })}
          />
          <Field
            label="Phone"
            type="tel"
            value={ec.phone}
            onChange={(v) => setEc({ ...ec, phone: v })}
            placeholder="+1 416 555 0199"
          />
        </div>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Only used by dispatch if you are in an incident or unreachable on a route.
        </p>
        <SaveBar busy={busy} msg={msg} onSave={() => save({ emergency_contact: ec })} />
      </Card>
    </>
  );
}

/** Email/phone change: add in Clerk -> 6-digit code -> make primary -> API copies verified value. */
function ContactSection({
  profile,
  onSynced,
}: {
  profile: DriverMeProfile;
  onSynced: (p: DriverMeProfile) => void;
}) {
  if (!isClerkConfigured()) {
    return (
      <Card title="Email & phone">
        <p className="text-sm text-[var(--muted)]">
          Sign-in is not configured in this environment.
        </p>
      </Card>
    );
  }
  return (
    <>
      <VerifiedChange kind="email" current={profile.email} onSynced={onSynced} />
      <VerifiedChange kind="phone" current={profile.phone} onSynced={onSynced} />
    </>
  );
}

type Pending = {
  prepare: () => Promise<unknown>;
  attempt: (
    code: string
  ) => Promise<{ id: string; verification?: { status?: string | null } | null }>;
};

function VerifiedChange({
  kind,
  current,
  onSynced,
}: {
  kind: "email" | "phone";
  current: string | null;
  onSynced: (p: DriverMeProfile) => void;
}) {
  const { user } = useUser();
  const [value, setValue] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"idle" | "code">("idle");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const pending = useRef<Pending | null>(null);
  const Icon = kind === "email" ? Mail : Phone;

  const start = async () => {
    if (!user) return;
    setBusy(true);
    setMsg(null);
    try {
      if (kind === "email") {
        const res = await user.createEmailAddress({ email: value.trim() });
        pending.current = {
          prepare: () => res.prepareVerification({ strategy: "email_code" }),
          attempt: (c) => res.attemptVerification({ code: c }),
        };
      } else {
        const digits = value.replace(/[^\d+]/g, "");
        const e164 = digits.startsWith("+")
          ? digits
          : digits.length === 10
            ? `+1${digits}`
            : `+${digits}`;
        const res = await user.createPhoneNumber({ phoneNumber: e164 });
        pending.current = {
          prepare: () => res.prepareVerification(),
          attempt: (c) => res.attemptVerification({ code: c }),
        };
      }
      await pending.current.prepare();
      setStep("code");
      setMsg(`We sent a 6-digit code to ${value.trim()}`);
    } catch (e) {
      setMsg(errText(e));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    if (!user || !pending.current) return;
    setBusy(true);
    setMsg(null);
    try {
      const verified = await pending.current.attempt(code.trim());
      if (verified.verification?.status !== "verified") throw new Error("Code not accepted");
      await user.update(
        kind === "email"
          ? { primaryEmailAddressId: verified.id }
          : { primaryPhoneNumberId: verified.id }
      );
      await user.reload();
      const out = await accountApi.syncIdentity();
      onSynced(out.profile);
      setStep("idle");
      setValue("");
      setCode("");
      setMsg(`${kind === "email" ? "Email" : "Phone"} verified and updated`);
    } catch (e) {
      setMsg(errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card
      title={kind === "email" ? "Email" : "Mobile phone"}
      action={<Icon className="h-4 w-4 text-[var(--muted)]" />}
    >
      <p className="mb-4 text-sm text-[var(--primary)]">
        <span className="text-[var(--muted)]">Current: </span>
        {current || "Not set"}
        {current ? (
          <Check className="ml-1.5 inline h-4 w-4 text-emerald-600" aria-label="verified" />
        ) : null}
      </p>
      {step === "idle" ? (
        <div className="flex max-w-lg gap-2">
          <div className="flex-1">
            <Field
              label={kind === "email" ? "New email" : "New phone"}
              type={kind === "email" ? "email" : "tel"}
              value={value}
              onChange={setValue}
              autoComplete={kind === "email" ? "email" : "tel"}
            />
          </div>
          <button
            type="button"
            disabled={busy || value.trim().length < 5}
            onClick={start}
            className="mt-6 h-11 rounded-xl bg-[var(--secondary)] px-5 text-sm font-bold text-white disabled:opacity-50"
          >
            {busy ? "Sending…" : "Send code"}
          </button>
        </div>
      ) : (
        <div className="flex max-w-lg gap-2">
          <div className="flex-1">
            <Field
              label="6-digit code"
              value={code}
              onChange={setCode}
              autoComplete="one-time-code"
            />
          </div>
          <button
            type="button"
            disabled={busy || code.trim().length < 6}
            onClick={confirm}
            className="mt-6 h-11 rounded-xl bg-[var(--secondary)] px-5 text-sm font-bold text-white disabled:opacity-50"
          >
            {busy ? "Checking…" : "Verify"}
          </button>
          <button
            type="button"
            onClick={() => setStep("idle")}
            className="mt-6 h-11 px-3 text-sm text-[var(--muted)]"
          >
            Cancel
          </button>
        </div>
      )}
      {msg ? (
        <p role="status" className="mt-3 text-sm text-[var(--muted)]">
          {msg}
        </p>
      ) : null}
    </Card>
  );
}

type SessionRow = {
  id: string;
  status: string;
  lastActiveAt: Date;
  latestActivity?: {
    browserName?: string;
    deviceType?: string;
    city?: string;
    country?: string;
    isMobile?: boolean;
  } | null;
  revoke: () => Promise<unknown>;
};

function SecuritySection() {
  if (!isClerkConfigured()) {
    return (
      <Card title="Security">
        <p className="text-sm text-[var(--muted)]">
          Sign-in is not configured in this environment.
        </p>
      </Card>
    );
  }
  return (
    <>
      <PasswordCard />
      <SessionsCard />
    </>
  );
}

function PasswordCard() {
  const { user } = useUser();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [signOutOthers, setSignOutOthers] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const hasPassword = Boolean(user?.passwordEnabled);

  const save = async () => {
    if (!user) return;
    if (next.length < 8) return setMsg("Use at least 8 characters");
    if (next !== confirm) return setMsg("Passwords do not match");
    setBusy(true);
    setMsg(null);
    try {
      await user.updatePassword({
        ...(hasPassword ? { currentPassword: current } : {}),
        newPassword: next,
        signOutOfOtherSessions: signOutOthers,
      });
      setCurrent("");
      setNext("");
      setConfirm("");
      setMsg(hasPassword ? "Password changed" : "Password set");
    } catch (e) {
      setMsg(errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card
      title={hasPassword ? "Change password" : "Set a password"}
      action={<KeyRound className="h-4 w-4 text-[var(--muted)]" />}
    >
      {!hasPassword ? (
        <p className="mb-4 text-sm text-[var(--muted)]">
          You sign in with a code or Google today. A password is optional.
        </p>
      ) : null}
      <div className="grid max-w-md gap-4">
        {hasPassword ? (
          <Field
            label="Current password"
            type="password"
            value={current}
            onChange={setCurrent}
            autoComplete="current-password"
          />
        ) : null}
        <Field
          label="New password"
          type="password"
          value={next}
          onChange={setNext}
          autoComplete="new-password"
        />
        <Field
          label="Confirm new password"
          type="password"
          value={confirm}
          onChange={setConfirm}
          autoComplete="new-password"
        />
        <label className="flex items-center gap-2 text-sm text-[var(--primary)]">
          <input
            type="checkbox"
            checked={signOutOthers}
            onChange={(e) => setSignOutOthers(e.target.checked)}
          />
          Sign out of all other devices
        </label>
      </div>
      <SaveBar
        busy={busy}
        msg={msg}
        onSave={save}
        label={hasPassword ? "Change password" : "Set password"}
      />
    </Card>
  );
}

function SessionsCard() {
  const { user } = useUser();
  const { session: currentSession, signOut } = useClerk();
  const [rows, setRows] = useState<SessionRow[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useMemo(
    () => async () => {
      if (!user) return;
      setRows((await user.getSessions()) as unknown as SessionRow[]);
    },
    [user]
  );
  useEffect(() => {
    void load();
  }, [load]);

  const others = (rows ?? []).filter((s) => s.id !== currentSession?.id && s.status === "active");
  return (
    <Card title="Signed-in devices" action={<Laptop className="h-4 w-4 text-[var(--muted)]" />}>
      <ul className="divide-y divide-[var(--primary)]/8">
        {(rows ?? []).map((s) => (
          <li key={s.id} className="flex items-center justify-between py-3 text-sm">
            <div>
              <p className="font-semibold text-[var(--primary)]">
                {s.latestActivity?.browserName ?? "Device"} ·{" "}
                {s.latestActivity?.deviceType ??
                  (s.latestActivity?.isMobile ? "Mobile" : "Computer")}
                {s.id === currentSession?.id ? (
                  <span className="ml-2 text-xs text-[var(--secondary)]">This device</span>
                ) : null}
              </p>
              <p className="text-xs text-[var(--muted)]">
                {[s.latestActivity?.city, s.latestActivity?.country].filter(Boolean).join(", ")} ·
                active {new Date(s.lastActiveAt).toLocaleString()}
              </p>
            </div>
            {s.id !== currentSession?.id ? (
              <button
                type="button"
                onClick={async () => {
                  await s.revoke();
                  await load();
                }}
                className="text-sm font-semibold text-red-600"
              >
                Sign out
              </button>
            ) : null}
          </li>
        ))}
        {rows === null ? <li className="h-12 animate-pulse rounded bg-[var(--gray-bg)]" /> : null}
      </ul>
      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={!others.length}
          onClick={async () => {
            await Promise.all(others.map((s) => s.revoke()));
            await load();
            setMsg("Signed out of all other devices");
          }}
          className="h-11 rounded-xl border border-[var(--primary)]/12 px-5 text-sm font-semibold disabled:opacity-40"
        >
          Sign out other devices
        </button>
        <button
          type="button"
          onClick={() => signOut({ redirectUrl: "/login" })}
          className="inline-flex h-11 items-center gap-2 rounded-xl bg-[var(--primary)] px-5 text-sm font-bold text-white"
        >
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </div>
      {msg ? (
        <p role="status" className="mt-3 text-sm text-[var(--muted)]">
          {msg}
        </p>
      ) : null}
    </Card>
  );
}

function Toggle({
  label,
  hint,
  on,
  onChange,
}: {
  label: string;
  hint?: string;
  on: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={() => onChange(!on)}
      className="flex w-full items-center justify-between py-3 text-left"
    >
      <span>
        <span className="block text-sm font-semibold text-[var(--primary)]">{label}</span>
        {hint ? <span className="block text-xs text-[var(--muted)]">{hint}</span> : null}
      </span>
      <span
        className={cn(
          "relative h-6 w-11 rounded-full transition",
          on ? "bg-[var(--secondary)]" : "bg-[var(--primary)]/15"
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition",
            on ? "left-[22px]" : "left-0.5"
          )}
        />
      </span>
    </button>
  );
}

function PreferencesSection({
  settings,
  onSaved,
}: {
  settings: DriverAppSettings;
  onSaved: (s: DriverAppSettings) => void;
}) {
  const [msg, setMsg] = useState<string | null>(null);
  const set = async (patch: DriverAppSettings) => {
    onSaved({ ...settings, ...patch }); // optimistic
    try {
      onSaved((await accountApi.updateSettings(patch)).settings);
      setMsg("Saved");
    } catch (e) {
      onSaved(settings);
      setMsg(errText(e));
    }
  };
  const flag = (k: keyof DriverAppSettings) => settings[k] !== false;
  return (
    <>
      <Card title="Language & navigation">
        <div className="grid max-w-md gap-4 sm:grid-cols-2">
          <Select
            label="Language"
            value={settings.language ?? "en"}
            options={[
              { value: "en", label: "English" },
              { value: "fr", label: "Français" },
            ]}
            onChange={(v) => set({ language: v as "en" | "fr" })}
          />
          <Select
            label="Navigation app"
            value={settings.nav_app ?? "google"}
            options={[
              { value: "google", label: "Google Maps" },
              { value: "apple", label: "Apple Maps" },
              { value: "waze", label: "Waze" },
            ]}
            onChange={(v) => set({ nav_app: v as "google" | "apple" | "waze" })}
          />
        </div>
      </Card>
      <Card title="Notifications">
        <div className="divide-y divide-[var(--primary)]/8">
          <Toggle
            label="New jobs & offers"
            on={flag("notify_jobs")}
            onChange={(v) => set({ notify_jobs: v })}
          />
          <Toggle
            label="Messages from dispatch"
            on={flag("notify_messages")}
            onChange={(v) => set({ notify_messages: v })}
          />
          <Toggle
            label="Route changes"
            on={flag("notify_route_changes")}
            onChange={(v) => set({ notify_route_changes: v })}
          />
          <Toggle
            label="Document expiry"
            hint="Licence, insurance and permit reminders"
            on={flag("notify_documents")}
            onChange={(v) => set({ notify_documents: v })}
          />
        </div>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Safety and account-security alerts are always on. Settings sync to your phone.
        </p>
      </Card>
      {msg ? (
        <p role="status" className="text-sm text-[var(--muted)]">
          {msg}
        </p>
      ) : null}
    </>
  );
}

function PrivacySection({ version }: { version: string }) {
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const request = async (kind: "access" | "correction" | "deletion") => {
    setBusy(true);
    try {
      const out = await accountApi.privacyRequest(kind);
      setMsg(
        `Request received${out.reference ? ` (ref ${out.reference.slice(0, 8)})` : ""}. We respond within ${out.sla_days} days.`
      );
    } catch (e) {
      setMsg(errText(e));
    } finally {
      setBusy(false);
    }
  };
  const links = [
    { href: "/monitoring-policy", label: "GPS monitoring policy", icon: MapPin, internal: true },
    { href: "https://porterchain.com/privacy", label: "Privacy policy", icon: ShieldCheck },
    { href: "https://porterchain.com/terms", label: "Terms of service", icon: ShieldCheck },
    { href: "/documents", label: "My documents", icon: ShieldCheck, internal: true },
  ];
  return (
    <>
      <Card title="Your data (PIPEDA)">
        <p className="mb-4 text-sm text-[var(--muted)]">
          Ask for a copy of your data, a correction, or deletion. Records we must keep by law
          (payouts, tax, incidents) are retained for the legal period.
        </p>
        <div className="flex flex-wrap gap-2">
          {(["access", "correction", "deletion"] as const).map((k) => (
            <button
              key={k}
              type="button"
              disabled={busy}
              onClick={() => request(k)}
              className={cn(
                "h-11 rounded-xl border px-5 text-sm font-semibold disabled:opacity-50",
                k === "deletion"
                  ? "border-red-200 text-red-600"
                  : "border-[var(--primary)]/12 text-[var(--primary)]"
              )}
            >
              {k === "access"
                ? "Download my data"
                : k === "correction"
                  ? "Correct my data"
                  : "Delete my account"}
            </button>
          ))}
        </div>
        {msg ? (
          <p role="status" className="mt-3 text-sm text-[var(--muted)]">
            {msg}
          </p>
        ) : null}
      </Card>
      <Card title="Legal">
        <ul className="divide-y divide-[var(--primary)]/8">
          {links.map((l) => (
            <li key={l.href}>
              {l.internal ? (
                <Link
                  href={l.href}
                  className="flex items-center justify-between py-3 text-sm font-semibold text-[var(--primary)]"
                >
                  {l.label} <ChevronRight className="h-4 w-4 text-[var(--muted)]" />
                </Link>
              ) : (
                <a
                  href={l.href}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between py-3 text-sm font-semibold text-[var(--primary)]"
                >
                  {l.label} <ChevronRight className="h-4 w-4 text-[var(--muted)]" />
                </a>
              )}
            </li>
          ))}
        </ul>
      </Card>
      <p className="px-1 text-xs text-[var(--muted)]">Porterchain Driver web · v{version}</p>
    </>
  );
}
