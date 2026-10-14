import { StyleSheet, View } from "react-native";
import type { RailStep } from "../../stop/stopFlow";
import { Label } from "../kit";
import { color, radius, space } from "../theme";

/** Arrive → Scan → Proof → Done, so the driver always knows where they are in the stop. */
export function StepRail({ steps }: { steps: RailStep[] }) {
  if (!steps.length) return null;
  const now = steps.find((s) => s.state === "now");
  return (
    <View
      style={styles.row}
      accessibilityRole="progressbar"
      accessibilityLabel={`Stop progress: ${now ? `now ${now.label}` : "all done"}`}
    >
      {steps.map((s) => (
        <View key={s.id} style={styles.item}>
          <View
            style={[styles.bar, s.state === "done" && styles.done, s.state === "now" && styles.now]}
          />
          <Label style={s.state === "todo" ? styles.todoText : styles.text}>
            {s.state === "done" ? `✓ ${s.label}` : s.label}
          </Label>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: space.xs },
  item: { flex: 1, gap: space.xs },
  bar: { height: 8, borderRadius: radius.pill, backgroundColor: color.disabled },
  done: { backgroundColor: color.primary },
  now: { backgroundColor: color.ink },
  text: { color: color.ink },
  todoText: { color: color.inkMuted },
});
