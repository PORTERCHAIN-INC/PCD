"use client";

import { ScrollView, View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Caption, Card, CardHeader, Screen } from "@porterchain/mobile-ui";
import { DEFAULT_PERFORMANCE_POLICY } from "../config";
import { usePerformance } from "../provider/PerformanceProvider";

function MetricRow({ label, value }: { label: string; value: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: theme.spacing.xs }}>
      <Caption>{label}</Caption>
      <Body style={{ fontWeight: "600" }}>{value}</Body>
    </View>
  );
}

export function PerformanceDashboard() {
  const { theme } = useTheme();
  const { metrics, refreshMetrics, clearCaches } = usePerformance();

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.md }}>
        <Body style={{ fontSize: 28, fontWeight: "700" }}>Performance</Body>
        <Caption>Enterprise mobile runtime metrics</Caption>

        <Card>
          <CardHeader title="Runtime" subtitle={`Updated ${metrics.updatedAt.slice(11, 19)}`} />
          <MetricRow label="App state" value={metrics.appState} />
          <MetricRow label="Battery optimizations" value={metrics.batteryOptimizationsActive ? "Active" : "Idle"} />
          <MetricRow label="Lazy screens loaded" value={String(metrics.lazyScreensLoaded)} />
        </Card>

        <Card>
          <CardHeader title="Network" />
          <MetricRow label="WebSocket" value={metrics.websocketConnected ? "Connected" : "Disconnected"} />
          <MetricRow label="WS paused (background)" value={metrics.websocketPaused ? "Yes" : "No"} />
          <MetricRow label="Last sync latency" value={metrics.lastSyncLatencyMs != null ? `${metrics.lastSyncLatencyMs}ms` : "—"} />
        </Card>

        <Card>
          <CardHeader title="Cache" />
          <MetricRow label="React Query entries" value={String(metrics.queryCacheEntries)} />
          <MetricRow label="Prefetch operations" value={String(metrics.prefetchCount)} />
          <MetricRow
            label="Image cache cleared"
            value={metrics.imageCacheClearedAt?.slice(11, 19) ?? "—"}
          />
        </Card>

        <Card>
          <CardHeader title="Policy" />
          <MetricRow label="List draw distance" value={`${DEFAULT_PERFORMANCE_POLICY.listDrawDistance}px`} />
          <MetricRow label="Prefetch stale time" value={`${DEFAULT_PERFORMANCE_POLICY.prefetchStaleTimeMs / 1000}s`} />
          <MetricRow label="Background polling" value={DEFAULT_PERFORMANCE_POLICY.backgroundPollingPaused ? "Paused" : "Always on"} />
        </Card>

        <Button label="Refresh metrics" variant="secondary" onPress={refreshMetrics} />
        <Button label="Clear caches" variant="outline" onPress={() => void clearCaches()} />
      </ScrollView>
    </Screen>
  );
}
