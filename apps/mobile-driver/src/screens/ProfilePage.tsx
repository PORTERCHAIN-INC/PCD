/**
 * Profile & account: photo, name, home address, emergency contact (from cache, instantly);
 * email/phone change with a 6-digit code (Clerk), password, signed-in devices, sign out.
 * One full-screen page; every edit expands inline. No pop-ups.
 */
import { useEffect, useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import { useClerk, useUser } from "@clerk/expo";
import type { Address, EmergencyContact, MeProfile } from "../api";
import { syncMyIdentity } from "../api";
import { fieldError } from "../account";
import { qk } from "../data/keys";
import { queryClient } from "../data/queryClient";
import { useMyProfile, useSaveProfile } from "../data/queries";
import { haptic } from "../haptics";
import { captureAvatarDataUrl } from "../pod";
import { Button } from "../ui/kit";
import { PressScale, Skeleton } from "../ui/motion";
import { InputRow, Row, Section, Segmented, ToggleRow } from "../ui/settings/rows";
import { Sheet } from "../ui/Sheet";
import { color, radius, space } from "../ui/theme";
import { toast } from "../ui/toast";
import { UpdatedAgo } from "../ui/UpdatedAgo";
import { confirmDeleteAccount } from "../ui/confirmDeleteAccount";

const RELS = ["spouse", "parent", "sibling", "friend", "other"];
function clerkMsg(e: unknown): string {
  const c = (e as { errors?: { longMessage?: string; message?: string }[] })?.errors?.[0];
  return c?.longMessage || c?.message || (e instanceof Error ? e.message : "Something went wrong");
}

export function ProfilePage({
  visible,
  onClose,
  onSignOut,
}: {
  visible: boolean;
  onClose: () => void;
  onSignOut: () => Promise<void>;
}) {
  return (
    <Sheet
      visible={visible}
      title="Profile"
      kicker="You · contact · security"
      onClose={onClose}
      testID="page-profile"
    >
      <ProfileBody onSignOut={onSignOut} />
    </Sheet>
  );
}

export function ProfileBody({
  onSignOut,
  clerk = true,
}: {
  onSignOut: () => Promise<void>;
  clerk?: boolean;
}) {
  const q = useMyProfile();
  const p = q.data;
  if (!p) {
    return (
      <View style={st.wrap}>
        <Skeleton width={96} height={96} />
        <Skeleton width="70%" height={22} />
        <Skeleton width="100%" height={160} />
        {q.isError ? (
          <Text style={st.err}>
            Couldn't load your profile. It will appear when you have signal.
          </Text>
        ) : null}
      </View>
    );
  }
  return (
    <View style={st.wrap}>
      <UpdatedAgo at={q.dataUpdatedAt} fetching={q.isFetching} />
      <Identity p={p} />
      <Personal p={p} />
      <Emergency p={p} />
      {clerk ? (
        <ContactAndSecurity p={p} onSignOut={onSignOut} />
      ) : (
        <SignOutOnly onSignOut={onSignOut} />
      )}
    </View>
  );
}

function Identity({ p }: { p: MeProfile }) {
  const save = useSaveProfile();
  const [pick, setPick] = useState(false);
  const take = async (src: "camera" | "library") => {
    setPick(false);
    try {
      const photo = await captureAvatarDataUrl(src);
      await save.mutateAsync({ photo });
      haptic.success();
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      if (m !== "photo_cancelled")
        toast.show("danger", "Photo not saved", "Try again with signal.");
    }
  };
  const initials = p.full_name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <View style={st.identity} testID="profile-identity">
      <PressScale
        accessibilityRole="button"
        accessibilityLabel="Change photo"
        onPress={() => setPick((v) => !v)}
      >
        {p.photo_url ? (
          <Image source={{ uri: p.photo_url }} style={st.avatar} />
        ) : (
          <View style={[st.avatar, st.avatarEmpty]}>
            <Text style={st.initials}>{initials}</Text>
          </View>
        )}
        <Text style={st.photoHint}>{p.photo_url ? "Change" : "Add photo"}</Text>
      </PressScale>
      <View style={st.flex}>
        <Text style={st.name} numberOfLines={2}>
          {p.full_name}
        </Text>
        <Text style={st.muted} numberOfLines={1}>
          {p.email}
        </Text>
        {p.phone ? <Text style={st.muted}>{p.phone}</Text> : null}
      </View>
      {pick ? (
        <View style={st.pickRow}>
          <Button label="Camera" onPress={() => void take("camera")} />
          <Button label="Library" onPress={() => void take("library")} />
          {p.photo_url ? (
            <Button
              label="Remove"
              tone="danger"
              onPress={() => {
                setPick(false);
                save.mutate({ photo: null });
              }}
            />
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

function Personal({ p }: { p: MeProfile }) {
  const save = useSaveProfile();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(p.full_name);
  const blank: Address = { line1: "", line2: "", city: "", province: "ON", postal_code: "" };
  const [a, setA] = useState<Address>(p.address ?? blank);
  const [err, setErr] = useState<{ field: string; text: string } | null>(null);
  const addr = p.address
    ? `${p.address.line1}${p.address.line2 ? `, ${p.address.line2}` : ""}, ${p.address.city} ${p.address.province} ${p.address.postal_code}`
    : undefined;
  const submit = async () => {
    setErr(null);
    try {
      await save.mutateAsync({ full_name: name, address: { ...a, line2: a.line2 || null } });
      haptic.success();
      setOpen(false);
      toast.show("success", "Saved", "Your details are up to date.");
    } catch (e) {
      setErr(fieldError(e) ?? { field: "", text: "Couldn't save. Try again with signal." });
    }
  };
  const e = (f: string) => (err?.field === f ? err.text : null);
  return (
    <Section title="PERSONAL" testID="profile-personal">
      <Row label="Legal name" value={p.full_name} />
      <Row
        label="Home address"
        sub={addr ?? "Not set"}
        onPress={() => setOpen((o) => !o)}
        testID="profile-edit-personal"
      />
      {open ? (
        <>
          <InputRow
            label="LEGAL NAME"
            value={name}
            onChange={setName}
            autoComplete="name"
            error={e("full_name")}
          />
          <InputRow
            label="STREET"
            value={a.line1}
            onChange={(v) => setA({ ...a, line1: v })}
            autoComplete="address-line1"
            error={e("address.line1")}
          />
          <InputRow
            label="UNIT (OPTIONAL)"
            value={a.line2 ?? ""}
            onChange={(v) => setA({ ...a, line2: v })}
          />
          <InputRow
            label="CITY"
            value={a.city}
            onChange={(v) => setA({ ...a, city: v })}
            error={e("address.city")}
          />
          <InputRow
            label="POSTAL CODE"
            value={a.postal_code}
            onChange={(v) => setA({ ...a, postal_code: v.toUpperCase() })}
            autoCapitalize="characters"
            placeholder="M5E 1W7"
            error={e("address.postal_code")}
          />
          <InputRow
            label="PROVINCE"
            value={a.province}
            onChange={(v) => setA({ ...a, province: v.toUpperCase() })}
            autoCapitalize="characters"
            maxLength={2}
            placeholder="ON"
            error={e("address.province")}
          />
          <View style={st.pad}>
            <Button
              tone="primary"
              label="Save details"
              busy={save.isPending}
              onPress={() => void submit()}
              testID="profile-save-personal"
            />
            {err && !err.field ? <Text style={st.err}>{err.text}</Text> : null}
          </View>
        </>
      ) : null}
    </Section>
  );
}

function Emergency({ p }: { p: MeProfile }) {
  const save = useSaveProfile();
  const [open, setOpen] = useState(false);
  const [c, setC] = useState<EmergencyContact>(
    p.emergency_contact ?? { name: "", relationship: "spouse", phone: "" }
  );
  const [err, setErr] = useState<{ field: string; text: string } | null>(null);
  const ec = p.emergency_contact;
  const submit = async () => {
    setErr(null);
    try {
      await save.mutateAsync({ emergency_contact: c });
      haptic.success();
      setOpen(false);
    } catch (e) {
      setErr(fieldError(e) ?? { field: "", text: "Couldn't save. Try again with signal." });
    }
  };
  return (
    <Section title="EMERGENCY CONTACT" testID="profile-emergency">
      <Row
        label={ec ? ec.name : "Add an emergency contact"}
        sub={
          ec
            ? `${ec.relationship[0].toUpperCase()}${ec.relationship.slice(1)} · ${ec.phone}`
            : "Dispatch calls them only if you're in an incident"
        }
        tone={ec ? undefined : "accent"}
        onPress={() => setOpen((o) => !o)}
      />
      {open ? (
        <>
          <InputRow
            label="NAME"
            value={c.name}
            onChange={(v) => setC({ ...c, name: v })}
            error={err?.field === "emergency_contact.name" ? err.text : null}
          />
          <InputRow
            label="PHONE"
            value={c.phone}
            onChange={(v) => setC({ ...c, phone: v })}
            keyboardType="phone-pad"
            error={err?.field === "emergency_contact.phone" ? err.text : null}
          />
          <Segmented
            label="Relationship"
            options={RELS.map((r) => ({ value: r, label: r[0].toUpperCase() + r.slice(1) }))}
            value={RELS.includes(c.relationship) ? c.relationship : "other"}
            onChange={(v) => setC({ ...c, relationship: v })}
          />
          <View style={st.pad}>
            <Button
              tone="primary"
              label="Save contact"
              busy={save.isPending}
              onPress={() => void submit()}
            />
            {err && !err.field ? <Text style={st.err}>{err.text}</Text> : null}
          </View>
        </>
      ) : null}
    </Section>
  );
}

type Verifiable = { id: string; verification?: { status?: string | null } | null };
type Pending = { attempt: (code: string) => Promise<Verifiable> };

function ContactAndSecurity({ p, onSignOut }: { p: MeProfile; onSignOut: () => Promise<void> }) {
  const { user } = useUser();
  const clerk = useClerk();
  const [editing, setEditing] = useState<null | "email" | "phone" | "password">(null);
  const [value, setValue] = useState("");
  const [code, setCode] = useState("");
  const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [others, setOthers] = useState(true);
  const [sessions, setSessions] = useState<
    {
      id: string;
      revoke: () => Promise<unknown>;
      latestActivity?: { deviceType?: string; browserName?: string; city?: string } | null;
    }[]
  >([]);

  const userId = user?.id;
  useEffect(() => {
    if (!user) return;
    void user
      .getSessions()
      .then((x) => setSessions(x as never))
      .catch(() => undefined);
    // Keyed on the user id: the user object is re-created on every Clerk update.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const reset = () => {
    setEditing(null);
    setValue("");
    setCode("");
    setPending(null);
    setMsg(null);
    setCur("");
    setNext("");
  };

  const sendCode = async (kind: "email" | "phone") => {
    if (!user) return;
    setBusy(true);
    setMsg(null);
    try {
      if (kind === "email") {
        const r = await user.createEmailAddress({ email: value.trim() });
        await r.prepareVerification({ strategy: "email_code" });
        setPending({ attempt: (c) => r.attemptVerification({ code: c }) as Promise<Verifiable> });
      } else {
        const d = value.replace(/[^\d+]/g, "");
        const e164 = d.startsWith("+") ? d : d.length === 10 ? `+1${d}` : `+${d}`;
        const r = await user.createPhoneNumber({ phoneNumber: e164 });
        await r.prepareVerification();
        setPending({ attempt: (c) => r.attemptVerification({ code: c }) as Promise<Verifiable> });
      }
      setMsg(`Code sent to ${value.trim()}`);
    } catch (e) {
      setMsg(clerkMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const verify = async (kind: "email" | "phone") => {
    if (!user || !pending) return;
    setBusy(true);
    try {
      const v = await pending.attempt(code.trim());
      if (v.verification?.status !== "verified") throw new Error("That code didn't work");
      await user.update(
        kind === "email" ? { primaryEmailAddressId: v.id } : { primaryPhoneNumberId: v.id }
      );
      await user.reload();
      const out = await syncMyIdentity();
      queryClient.setQueryData(qk.profile, out.profile);
      haptic.success();
      toast.show("success", kind === "email" ? "Email updated" : "Phone updated", "Verified.");
      reset();
    } catch (e) {
      setMsg(clerkMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const changePassword = async () => {
    if (!user) return;
    if (next.length < 8) return setMsg("Use at least 8 characters");
    setBusy(true);
    try {
      await user.updatePassword({
        ...(user.passwordEnabled ? { currentPassword: cur } : {}),
        newPassword: next,
        signOutOfOtherSessions: others,
      });
      haptic.success();
      toast.show("success", "Password saved", others ? "Other devices were signed out." : "");
      reset();
    } catch (e) {
      setMsg(clerkMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const otherSessions = sessions.filter((s) => s.id !== clerk.session?.id);
  const field = (kind: "email" | "phone") => (
    <>
      {!pending ? (
        <>
          <InputRow
            label={kind === "email" ? "NEW EMAIL" : "NEW MOBILE NUMBER"}
            value={value}
            onChange={setValue}
            keyboardType={kind === "email" ? "email-address" : "phone-pad"}
            autoCapitalize="none"
            autoComplete={kind === "email" ? "email" : "tel"}
          />
          <View style={st.pad}>
            <Button
              tone="primary"
              label="Send code"
              busy={busy}
              disabled={value.trim().length < 5}
              onPress={() => void sendCode(kind)}
            />
          </View>
        </>
      ) : (
        <>
          <InputRow
            label="6-DIGIT CODE"
            value={code}
            onChange={setCode}
            keyboardType="number-pad"
            autoComplete="one-time-code"
            textContentType="oneTimeCode"
            maxLength={6}
          />
          <View style={st.pad}>
            <Button
              tone="primary"
              label="Verify"
              busy={busy}
              disabled={code.trim().length < 6}
              onPress={() => void verify(kind)}
            />
          </View>
        </>
      )}
      {msg ? <Text style={st.msg}>{msg}</Text> : null}
    </>
  );

  return (
    <>
      <Section title="CONTACT · VERIFIED" testID="profile-contact">
        <Row
          label="Email"
          value={p.email}
          onPress={() => (editing === "email" ? reset() : (reset(), setEditing("email")))}
        />
        {editing === "email" ? field("email") : null}
        <Row
          label="Mobile"
          value={p.phone ?? "Add"}
          onPress={() => (editing === "phone" ? reset() : (reset(), setEditing("phone")))}
        />
        {editing === "phone" ? field("phone") : null}
      </Section>

      <Section title="SECURITY" testID="profile-security">
        <Row
          label="Delete account"
          sub="Permanently delete your driver account and data"
          onPress={() => confirmDeleteAccount()}
          testID="profile-delete-account"
        />
        <Row
          label={user?.passwordEnabled ? "Change password" : "Set a password"}
          sub="Optional if you sign in with a code"
          onPress={() => (editing === "password" ? reset() : (reset(), setEditing("password")))}
        />
        {editing === "password" ? (
          <>
            {user?.passwordEnabled ? (
              <InputRow
                label="CURRENT PASSWORD"
                value={cur}
                onChange={setCur}
                secureTextEntry
                autoComplete="current-password"
              />
            ) : null}
            <InputRow
              label="NEW PASSWORD"
              value={next}
              onChange={setNext}
              secureTextEntry
              autoComplete="new-password"
            />
            <ToggleRow label="Sign out other devices" value={others} onChange={setOthers} />
            <View style={st.pad}>
              <Button
                tone="primary"
                label="Save password"
                busy={busy}
                onPress={() => void changePassword()}
              />
            </View>
            {msg ? <Text style={st.msg}>{msg}</Text> : null}
          </>
        ) : null}
        <Row label="Signed-in devices" value={String(sessions.length || 1)} />
        {otherSessions.map((s) => (
          <Row
            key={s.id}
            label={`${s.latestActivity?.deviceType ?? s.latestActivity?.browserName ?? "Device"}`}
            sub={s.latestActivity?.city ?? undefined}
            value="Sign out"
            tone="danger"
            onPress={() =>
              void s.revoke().then(() => setSessions((x) => x.filter((y) => y.id !== s.id)))
            }
          />
        ))}
        {otherSessions.length ? (
          <Row
            label="Sign out all other devices"
            tone="danger"
            onPress={() =>
              void Promise.all(otherSessions.map((s) => s.revoke())).then(() =>
                setSessions((x) => x.filter((y) => y.id === clerk.session?.id))
              )
            }
          />
        ) : null}
      </Section>
      <SignOutOnly onSignOut={onSignOut} />
    </>
  );
}

function SignOutOnly({ onSignOut }: { onSignOut: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      tone="secondary"
      label="Sign out"
      busy={busy}
      testID="profile-sign-out"
      onPress={() => {
        setBusy(true);
        void onSignOut().finally(() => setBusy(false));
      }}
    />
  );
}

const st = StyleSheet.create({
  wrap: { gap: space.lg },
  flex: { flex: 1 },
  identity: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: space.lg },
  avatar: { width: 88, height: 88, borderRadius: 44, borderWidth: 2, borderColor: color.primary },
  avatarEmpty: { backgroundColor: color.surface2, alignItems: "center", justifyContent: "center" },
  initials: { fontSize: 30, fontWeight: "900", color: color.ink },
  photoHint: {
    fontSize: 12,
    fontWeight: "700",
    color: color.primary,
    textAlign: "center",
    marginTop: 4,
  },
  name: { fontSize: 26, lineHeight: 30, fontWeight: "900", color: color.ink },
  muted: { fontSize: 14, color: color.inkMuted, marginTop: 2 },
  pickRow: { flexDirection: "row", gap: space.sm, width: "100%" },
  pad: { padding: space.lg, gap: space.sm },
  err: { color: color.danger, fontSize: 14 },
  msg: {
    color: color.inkMuted,
    fontSize: 14,
    paddingHorizontal: space.lg,
    paddingBottom: space.md,
  },
  card: { borderRadius: radius.lg },
});
