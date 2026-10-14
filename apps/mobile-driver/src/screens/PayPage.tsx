/**
 * Pay & time: earnings at a glance, next payout, statements, payouts and weekly timesheets.
 * Everything renders from the encrypted device cache first; the server copy follows quietly.
 */
import { useState } from "react";
import { Linking, StyleSheet, Text, View } from "react-native";
import { hm } from "../account";
import { driverPortalUrl } from "../config";
import { useEarningsFull, useStatements, useTimesheets } from "../data/queries";
import { money, moneyShort } from "../smart/geo";
import { Skeleton } from "../ui/motion";
import { Row, Section, Segmented } from "../ui/settings/rows";
import { Sheet } from "../ui/Sheet";
import { color, radius, space } from "../ui/theme";
import { UpdatedAgo } from "../ui/UpdatedAgo";

const dayFmt = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString("en-CA", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
const timeFmt = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleTimeString("en-CA", {
        hour: "numeric",
        minute: "2-digit",
        timeZone: "America/Toronto",
      })
    : "now";

export function PayPage({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  return (
    <Sheet
      visible={visible}
      title="Pay & time"
      kicker="Earnings · statements · timesheets"
      onClose={onClose}
      testID="page-pay"
    >
      <PayBody />
    </Sheet>
  );
}

export function PayBody({ initialTab = "pay" }: { initialTab?: "pay" | "time" }) {
  const [tab, setTab] = useState<"pay" | "time">(initialTab);
  const e = useEarningsFull();
  return (
    <View style={st.wrap}>
      <UpdatedAgo at={e.dataUpdatedAt} fetching={e.isFetching} />
      <View style={st.hero} testID="pay-hero">
        <Text style={st.heroL}>THIS WEEK</Text>
        {e.data ? (
          <Text style={st.heroV}>{money(e.data.week_cents)}</Text>
        ) : (
          <Skeleton width={180} height={44} />
        )}
        <View style={st.heroRow}>
          <Mini label="Today" v={e.data ? moneyShort(e.data.today_cents) : "—"} />
          <Mini label="Month" v={e.data ? moneyShort(e.data.month_cents) : "—"} />
          <Mini label="Year" v={e.data?.taxes ? moneyShort(e.data.taxes.ytd_gross_cents) : "—"} />
        </View>
        {e.data?.payment_schedule ? (
          <Text style={st.next}>
            Next payout{" "}
            {new Date(`${e.data.payment_schedule.next_payout_date}T12:00:00`).toLocaleDateString(
              "en-CA",
              { weekday: "long", month: "short", day: "numeric" }
            )}{" "}
            · {e.data.payment_schedule.frequency}
          </Text>
        ) : null}
      </View>
      <Segmented
        label=""
        options={[
          { value: "pay", label: "Pay" },
          { value: "time", label: "Timesheets" },
        ]}
        value={tab}
        onChange={setTab}
        testID="pay-tabs"
      />
      {tab === "pay" ? <PayTab /> : <TimeTab />}
    </View>
  );
}

function Mini({ label, v }: { label: string; v: string }) {
  return (
    <View style={st.mini}>
      <Text style={st.miniV}>{v}</Text>
      <Text style={st.miniL}>{label}</Text>
    </View>
  );
}

function PayTab() {
  const s = useStatements();
  const e = useEarningsFull();
  const payouts = e.data?.payout_history ?? [];
  return (
    <>
      <Section title="STATEMENTS" testID="pay-statements">
        {(s.data?.statements ?? []).slice(0, 8).map((r) => (
          <Row
            key={r.id}
            label={r.period_label}
            sub={`${r.deliveries} deliveries · gross ${money(r.gross_cents)} · fees ${money(r.deductions_cents)}`}
            value={money(r.net_cents)}
            onPress={() =>
              void Linking.openURL(
                `${driverPortalUrl}/earnings?statement=${encodeURIComponent(r.id)}`
              )
            }
          />
        ))}
        {s.data && !s.data.statements.length ? (
          <Row
            label="No statements yet"
            sub="Your first one appears after your first pay period."
          />
        ) : null}
        {!s.data ? <Row label="Loading…" /> : null}
      </Section>
      <Section title="PAYOUTS">
        {payouts.slice(0, 6).map((p) => (
          <Row
            key={p.id}
            label={money(p.amount_cents)}
            sub={
              p.created_at
                ? new Date(p.created_at).toLocaleDateString("en-CA", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })
                : undefined
            }
            value={p.status === "paid" ? "Paid" : p.status[0].toUpperCase() + p.status.slice(1)}
          />
        ))}
        {e.data && !payouts.length ? <Row label="No payouts yet" /> : null}
      </Section>
      <Text style={st.foot}>Tax slips (T4A) and bank details are on the driver portal.</Text>
    </>
  );
}

function TimeTab() {
  const t = useTimesheets();
  if (!t.data) return <Skeleton width="100%" height={180} />;
  if (!t.data.weeks.length)
    return (
      <Section title="TIMESHEETS">
        <Row
          label="No shifts in the last 4 weeks"
          sub="Start a shift from Today and it shows up here."
        />
      </Section>
    );
  return (
    <>
      {t.data.weeks.map((w) => (
        <Section
          key={w.week_start}
          title={`WEEK OF ${dayFmt(w.week_start).toUpperCase()} · ${hm(w.worked_minutes)} · ${w.km} KM`}
          testID={`week-${w.week_start}`}
        >
          {w.shifts.map((s) => (
            <Row
              key={s.id}
              label={dayFmt(s.date)}
              sub={`${timeFmt(s.started_at)} – ${timeFmt(s.ended_at)} · break ${hm(s.break_minutes)} · ${s.km} km`}
              value={hm(s.worked_minutes)}
            />
          ))}
        </Section>
      ))}
      <Text style={st.foot}>Times are Toronto time. Worked time excludes breaks.</Text>
    </>
  );
}

const st = StyleSheet.create({
  wrap: { gap: space.lg },
  hero: {
    backgroundColor: color.surface,
    borderRadius: radius.xl,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.border,
    padding: space.xl,
    gap: space.sm,
  },
  heroL: { fontSize: 12, fontWeight: "800", letterSpacing: 1.2, color: color.inkFaint },
  heroV: {
    fontSize: 44,
    lineHeight: 50,
    fontWeight: "900",
    color: color.ink,
    fontVariant: ["tabular-nums"],
  },
  heroRow: { flexDirection: "row", gap: space.sm, marginTop: space.xs },
  mini: { flex: 1 },
  miniV: { fontSize: 18, fontWeight: "900", color: color.ink, fontVariant: ["tabular-nums"] },
  miniL: { fontSize: 12, fontWeight: "700", color: color.inkMuted },
  next: { fontSize: 14, fontWeight: "700", color: color.primary, marginTop: space.sm },
  foot: { fontSize: 13, color: color.inkFaint, paddingHorizontal: space.xs },
});
