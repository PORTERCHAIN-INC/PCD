import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ScrollView, View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import {
  Body,
  Button,
  Caption,
  Card,
  CardHeader,
  Display,
  ListItem,
  MetricCard,
  Screen,
  SkeletonCard,
  StatusChip,
} from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";

function money(cents: number) {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" }).format(cents / 100);
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-CA", { month: "short", day: "numeric", year: "numeric" });
}

function MetricRow({ children }: { children: ReactNode }) {
  const { theme } = useTheme();
  return <View style={{ flexDirection: "row", gap: theme.spacing.md }}>{children}</View>;
}

function MetricCell({ children }: { children: ReactNode }) {
  return <View style={{ flex: 1, minWidth: 0 }}>{children}</View>;
}

export function EarningsScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["driver", "earnings"],
    queryFn: () => api.earningsSnapshot(),
  });

  const { data: statementsData } = useQuery({
    queryKey: ["driver", "earnings", "statements"],
    queryFn: () => api.earningsStatements(),
    enabled: Boolean(data),
  });

  const statements = statementsData?.statements ?? [];

  return (
    <Screen>
      <ScreenHeader title="Earnings" subtitle="Wallet & payouts" />
      <ScrollView
        contentContainerStyle={{
          padding: theme.spacing.lg,
          gap: theme.spacing.lg,
          paddingBottom: theme.layout.tabBarHeight + theme.spacing.lg,
        }}
      >
        {isLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : null}

        {isError ? (
          <Card>
            <Body style={{ fontWeight: "600" }}>Could not load earnings</Body>
            <Body muted style={{ marginTop: theme.spacing.sm }}>
              Pull to refresh or tap Sync now below.
            </Body>
          </Card>
        ) : null}

        {data ? (
          <>
            <Card
              style={{
                backgroundColor: theme.colors.secondary,
                borderColor: theme.colors.secondary,
                gap: theme.spacing.sm,
              }}
            >
              <Caption inverse>Wallet balance</Caption>
              <Display inverse>{money(data.wallet_balance_cents)}</Display>
              <Caption inverse>
                {data.completed_deliveries_today} deliveries today · Updated{" "}
                {formatDate(data.last_updated)}
              </Caption>
            </Card>

            <View style={{ gap: theme.spacing.sm }}>
              <Caption style={{ fontWeight: "600", letterSpacing: 0.4 }}>PERIOD SUMMARY</Caption>
              <MetricRow>
                <MetricCell>
                  <MetricCard label="Today" value={money(data.today_cents)} />
                </MetricCell>
                <MetricCell>
                  <MetricCard label="This week" value={money(data.week_cents)} />
                </MetricCell>
              </MetricRow>
              <MetricRow>
                <MetricCell>
                  <MetricCard label="This month" value={money(data.month_cents)} />
                </MetricCell>
                <MetricCell>
                  <MetricCard
                    label="Deliveries today"
                    value={String(data.completed_deliveries_today)}
                  />
                </MetricCell>
              </MetricRow>
              <Caption muted>
                {data.completed_deliveries_week} this week · {data.completed_deliveries_month} this
                month
              </Caption>
            </View>

            <Card>
              <CardHeader title="Payment schedule" subtitle="Payout timing from Finance Engine" />
              <Body muted>Frequency: {data.payment_schedule.frequency}</Body>
              <Body muted style={{ marginTop: theme.spacing.xs }}>
                Payout day: {data.payment_schedule.day_of_week}
              </Body>
              <Body muted style={{ marginTop: theme.spacing.xs }}>
                Cutoff: {data.payment_schedule.cutoff_description}
              </Body>
              {data.payment_schedule.next_payout_date ? (
                <Body muted style={{ marginTop: theme.spacing.xs }}>
                  Next payout: {formatDate(data.payment_schedule.next_payout_date)}
                </Body>
              ) : null}
            </Card>

            <Card>
              <CardHeader
                title="Bonuses"
                subtitle={data.bonuses.length ? `${data.bonuses.length} on file` : "No bonuses yet"}
              />
              {data.bonuses.length === 0 ? (
                <Body muted>Complete milestones to earn bonuses.</Body>
              ) : (
                data.bonuses.map((bonus, index) => (
                  <ListItem
                    key={bonus.id}
                    title={bonus.title}
                    subtitle={bonus.status}
                    meta={money(bonus.amount_cents)}
                    showDivider={index < data.bonuses.length - 1}
                    inset={false}
                  />
                ))
              )}
            </Card>

            <Card>
              <CardHeader
                title="Payout history"
                subtitle={
                  data.payout_history.length
                    ? `${data.payout_history.length} recorded`
                    : "No payouts yet"
                }
              />
              {data.payout_history.length === 0 ? (
                <Body muted>Payouts appear here after your first deposit.</Body>
              ) : (
                data.payout_history.map((payout, index) => (
                  <ListItem
                    key={payout.id}
                    title={money(payout.amount_cents)}
                    subtitle={`${formatDate(payout.created_at)} · ${payout.reference ?? "Payout"}`}
                    trailing={<StatusChip label={payout.status} tone="neutral" />}
                    showDivider={index < data.payout_history.length - 1}
                    inset={false}
                  />
                ))
              )}
            </Card>

            <Card>
              <CardHeader title="Statements" subtitle="Monthly earnings from Finance Engine" />
              {statements.length === 0 ? (
                <Body muted>No monthly statements yet.</Body>
              ) : (
                statements.map((statement, index) => (
                  <ListItem
                    key={statement.id}
                    title={statement.period_label}
                    subtitle={`${statement.deliveries} deliveries · gross ${money(statement.gross_cents)}`}
                    meta={money(statement.net_cents)}
                    showDivider={index < statements.length - 1}
                    inset={false}
                  />
                ))
              )}
            </Card>
          </>
        ) : null}

        <Button
          label={isFetching ? "Syncing…" : "Sync now"}
          variant="secondary"
          fullWidth
          onPress={() => void refetch()}
        />
      </ScrollView>
    </Screen>
  );
}
