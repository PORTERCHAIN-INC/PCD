/** Electronic Monitoring Policy as a full-screen, readable page (was a cramped system alert). */
import { useState } from "react";
import { StyleSheet, Text } from "react-native";
import { fetchMonitoringPolicy, type MonitoringPolicy } from "../api";
import { Sheet } from "./Sheet";
import { color, space, type } from "./theme";
import { toast } from "./toast";

export function usePolicyPage() {
  const [p, setP] = useState<MonitoringPolicy | null>(null);
  const open = (policy?: MonitoringPolicy | null) => {
    if (policy) return setP(policy);
    void fetchMonitoringPolicy()
      .then(setP)
      .catch(() => toast.show("warn", "Couldn't load the policy", "Try again when you're online."));
  };
  const page = (
    <Sheet
      visible={p != null}
      kicker={p ? `Version ${p.version}` : undefined}
      title={p?.title ?? "Electronic Monitoring Policy"}
      onClose={() => setP(null)}
      testID="page-policy"
    >
      {(p?.sections ?? []).map((s, i) => (
        <Text key={i} style={styles.block}>
          {s.heading ? (
            <Text style={styles.h}>
              {s.heading}
              {"\n"}
            </Text>
          ) : null}
          {s.body ?? ""}
          {(s.items ?? []).map((it) => `\n•  ${it}`).join("")}
        </Text>
      ))}
    </Sheet>
  );
  return { open, page };
}

const styles = StyleSheet.create({
  block: { ...type.body, color: color.inkMuted, marginBottom: space.md },
  h: { ...type.bodyStrong, color: color.ink },
});
