/** Every stop of a multi-stop order, in order, with where the driver is now. */
import { StyleSheet, View } from "react-native";

import { orderStopRows, type OrderStop } from "../../stop/multiStop";
import { Body, Card, Label, Muted, Strong } from "../kit";
import { color, space } from "../theme";

export function OrderStopsCard({
  stops,
  currentStopId,
}: {
  stops: OrderStop[] | null | undefined;
  currentStopId: string | null;
}) {
  const rows = orderStopRows(stops, currentStopId);
  if (!rows.length) return null;
  return (
    <Card testID="order-stops">
      <Label>All stops ({rows.length})</Label>
      {rows.map((r) => (
        <View
          key={r.stopId}
          style={[styles.row, r.current ? styles.current : null]}
          accessibilityLabel={`${r.title}, ${r.address}, ${r.status}`}
          testID={`order-stop-${r.stopId}`}
        >
          <View style={styles.text}>
            {r.current ? <Strong>{r.title}</Strong> : <Body>{r.title}</Body>}
            <Muted>{r.address}</Muted>
          </View>
          <Muted style={r.done ? styles.done : undefined}>
            {r.done ? `✓ ${r.status}` : r.status}
          </Muted>
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: space.sm,
    paddingVertical: space.xs,
  },
  current: { borderLeftWidth: 3, borderLeftColor: color.primary, paddingLeft: space.sm },
  text: { flex: 1, gap: 2 },
  done: { color: color.successInk },
});
