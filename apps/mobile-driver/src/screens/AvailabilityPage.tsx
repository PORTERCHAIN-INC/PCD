/** Weekly availability: tap a day to switch it on, pick a preset block. Saves at once (optimistic). */
import { StyleSheet, Text, View } from "react-native";
import { BLOCKS, blockOf, weeklyHours, type BlockKey } from "../account";
import type { DayKey, Schedule } from "../api";
import { useSaveSchedule, useSchedule } from "../data/queries";
import { Skeleton } from "../ui/motion";
import { Section, Segmented, ToggleRow } from "../ui/settings/rows";
import { Sheet } from "../ui/Sheet";
import { color, space } from "../ui/theme";
import { toast } from "../ui/toast";
import { UpdatedAgo } from "../ui/UpdatedAgo";

const DAYS: { k: DayKey; label: string }[] = [
  { k: "mon", label: "Monday" },
  { k: "tue", label: "Tuesday" },
  { k: "wed", label: "Wednesday" },
  { k: "thu", label: "Thursday" },
  { k: "fri", label: "Friday" },
  { k: "sat", label: "Saturday" },
  { k: "sun", label: "Sunday" },
];
export function AvailabilityPage({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  return (
    <Sheet
      visible={visible}
      title="Availability"
      kicker="When dispatch can plan you"
      onClose={onClose}
      testID="page-availability"
    >
      <AvailabilityBody />
    </Sheet>
  );
}

export function AvailabilityBody() {
  const q = useSchedule();
  const save = useSaveSchedule();
  if (!q.data) return <Skeleton width="100%" height={300} />;
  const s = q.data.schedule;
  const put = (next: Schedule) =>
    save.mutate(next, {
      onError: () => toast.show("danger", "Not saved", "Try again with signal."),
    });
  return (
    <View style={st.wrap}>
      <UpdatedAgo at={q.dataUpdatedAt} fetching={q.isFetching} />
      <View>
        <Text style={st.big}>{weeklyHours(s)} h</Text>
        <Text style={st.muted}>available per week · Toronto time</Text>
      </View>
      <Section title="WEEK" testID="availability-week">
        {DAYS.map(({ k, label }) => {
          const on = (s[k] ?? []).length > 0;
          return (
            <View key={k}>
              <ToggleRow
                label={label}
                sub={on ? `${s[k][0].start} – ${s[k][0].end}` : "Off"}
                value={on}
                onChange={(v) =>
                  put({ ...s, [k]: v ? [{ start: BLOCKS.day.start, end: BLOCKS.day.end }] : [] })
                }
                testID={`day-${k}`}
              />
              {on ? (
                <Segmented
                  label=""
                  options={(Object.keys(BLOCKS) as BlockKey[]).map((b) => ({
                    value: b,
                    label: BLOCKS[b].label,
                  }))}
                  value={blockOf(s[k][0])}
                  onChange={(b) =>
                    put({ ...s, [k]: [{ start: BLOCKS[b].start, end: BLOCKS[b].end }] })
                  }
                />
              ) : null}
            </View>
          );
        })}
      </Section>
      <Text style={st.muted}>Going on or off duty for today is on the Today screen.</Text>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { gap: space.lg },
  big: { fontSize: 40, fontWeight: "900", color: color.ink },
  muted: { fontSize: 14, color: color.inkMuted },
});
