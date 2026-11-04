/**
 * Profile & account: photo, name, home address, emergency contact (from cache, instantly);
 * email/password/passkeys/devices via the Keycloak account console, sign out.
 * One full-screen page; every edit expands inline. No pop-ups.
 */
import { useEffect, useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { useSessionView } from "../auth/SessionGate";
import type { Address, EmergencyContact, MeProfile } from "../api";
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
  account = true,
}: {
  onSignOut: () => Promise<void>;
  account?: boolean;
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
      {account ? (
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

/** Email, password, passkeys and signed-in devices live in the Keycloak account console (L36). */
function ContactAndSecurity({ p, onSignOut }: { p: MeProfile; onSignOut: () => Promise<void> }) {
  const { accountUrl } = useSessionView();
  const openAccount = () => {
    if (accountUrl) void WebBrowser.openBrowserAsync(accountUrl);
  };
  return (
    <>
      <Section title="CONTACT · VERIFIED" testID="profile-contact">
        <Row label="Email" value={p.email} onPress={accountUrl ? openAccount : undefined} />
        <Row label="Mobile" value={p.phone ?? "Add"} />
      </Section>

      <Section title="SECURITY" testID="profile-security">
        <Row
          label="Delete account"
          sub="Permanently delete your driver account and data"
          onPress={() => confirmDeleteAccount()}
          testID="profile-delete-account"
        />
        {accountUrl ? (
          <Row
            label="Password, passkeys and devices"
            sub="Change email or password, add a passkey, sign out other devices"
            onPress={openAccount}
            testID="profile-account-security"
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
