/** Doc 82 §1.2: illustrated step cards from the server flow spec (same props as the driver web). */
import { useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";
import { flowView } from "@porterchain/driver-flows";
import { fetchJob } from "../../api";
import { flowFor } from "../../flowContext";
import { useSettings } from "../../settings";
import { Body, Card, Label, Muted } from "../kit";
import type { DriverJobDetail } from "../../types";

export function GuidedFlowCard({ orderId }: { orderId: string }) {
  const { language } = useSettings();
  const [job, setJob] = useState<DriverJobDetail | null>(null);
  useEffect(() => {
    let live = true;
    fetchJob(orderId)
      .then((j) => live && setJob(j))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [orderId]);
  if (!job) return null;
  const { spec, ctx, completed } = flowFor(job);
  if (!spec) return null;
  const cards = flowView(spec, ctx, language, completed);
  return (
    <Card testID="guided-flow">
      <Label>{language === "fr" ? "Étapes" : "Steps"}</Label>
      {cards.map((c, i) => (
        <View key={c.id} style={styles.row} accessible accessibilityLabel={`${i + 1}. ${c.title}`}>
          <Body
            style={c.state === "current" ? styles.current : undefined}
          >{`${i + 1}. ${c.title}`}</Body>
          {c.state === "current" ? (
            <>
              <Muted>{`✓ ${c.doText}`}</Muted>
              {c.dontText ? <Muted>{`✕ ${c.dontText}`}</Muted> : null}
              {c.blockers.map((b) => (
                <Muted key={b}>{`⚠ ${b}`}</Muted>
              ))}
            </>
          ) : null}
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { minHeight: 44, paddingVertical: 4 },
  current: { fontWeight: "700" },
});
