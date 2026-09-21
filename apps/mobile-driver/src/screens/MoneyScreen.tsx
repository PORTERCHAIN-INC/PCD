import { useEffect, useState } from "react";
import { ScrollView, Share, Text, View, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import {
  claimBonus,
  downloadStatementCsv,
  fetchBonuses,
  fetchEarnings,
  fetchEarningsToday,
  fetchRatings,
  fetchStatementDetail,
  fetchStatements,
  fetchWallet,
} from "../api";
import { formatCents, formatWhen } from "../format";
import { Card, CardTitle, Kpi } from "../ui/Card";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import { ScreenHeader } from "../ui/ScreenHeader";
import type {
  BonusRow,
  EarningsSnapshot,
  RatingsSummary,
  StatementDetail,
  StatementRow,
  WalletSnapshot,
} from "../types";

export function MoneyScreen({ refreshToken = 0 }: { refreshToken?: number }) {
  const [wallet, setWallet] = useState<WalletSnapshot | null>(null);
  const [earnings, setEarnings] = useState<EarningsSnapshot | null>(null);
  const [todayCents, setTodayCents] = useState<number | null>(null);
  const [statements, setStatements] = useState<StatementRow[]>([]);
  const [bonuses, setBonuses] = useState<BonusRow[]>([]);
  const [ratings, setRatings] = useState<RatingsSummary | null>(null);
  const [detail, setDetail] = useState<StatementDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      fetchWallet(),
      fetchEarnings(),
      fetchStatements(),
      fetchEarningsToday().catch((): { today_cents?: number; amount_cents?: number } => ({})),
      fetchBonuses().catch(() => ({ bonuses: [] as BonusRow[] })),
      fetchRatings().catch(() => null),
    ])
      .then(([nextWallet, nextEarnings, nextStatements, today, bonusPayload, ratingPayload]) => {
        setWallet(nextWallet);
        setEarnings(nextEarnings);
        setStatements(nextStatements.statements ?? []);
        setTodayCents(today.today_cents ?? today.amount_cents ?? nextEarnings.today_cents ?? null);
        setBonuses(bonusPayload.bonuses ?? []);
        setRatings(ratingPayload);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "money_failed");
      });
  }, [refreshToken]);

  return (
    <Screen testID="mobile-money" includeBottomSafeArea={false}>
      <ScreenHeader title="Money" lede="Wallet, earnings, bonuses, and statements." />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.kpis}>
          <Kpi
            label="Wallet"
            value={formatCents(wallet?.balance_cents ?? earnings?.wallet_balance_cents)}
          />
          <Kpi label="Today" value={formatCents(todayCents ?? earnings?.today_cents)} />
        </View>
        <View style={styles.kpis}>
          <Kpi label="This week" value={formatCents(earnings?.week_cents)} />
          <Kpi label="This month" value={formatCents(earnings?.month_cents)} />
        </View>
        <View style={styles.kpis}>
          <Kpi
            label="Rating"
            value={
              ratings?.average != null || ratings?.rating != null
                ? String(ratings.average ?? ratings.rating)
                : "—"
            }
          />
          <Kpi label="Reviews" value={ratings?.count != null ? String(ratings.count) : "—"} />
        </View>

        <Card>
          <CardTitle>Bonuses</CardTitle>
          {bonuses.slice(0, 8).map((bonus) => (
            <View key={bonus.id} style={styles.bonusRow}>
              <Text style={styles.rowLabel}>
                {bonus.title || bonus.label || bonus.id} · {formatCents(bonus.amount_cents)}
              </Text>
              {(bonus.claimable || bonus.status === "available") && (
                <PrimaryButton
                  tone="ghost"
                  label={busy === bonus.id ? "Claiming…" : "Claim"}
                  disabled={Boolean(busy)}
                  onPress={() => {
                    setBusy(bonus.id);
                    void claimBonus(bonus.id)
                      .then(() => fetchBonuses().then((p) => setBonuses(p.bonuses ?? [])))
                      .catch((err: unknown) => {
                        setError(err instanceof Error ? err.message : "claim_failed");
                      })
                      .finally(() => setBusy(null));
                  }}
                />
              )}
            </View>
          ))}
          {bonuses.length === 0 ? <Text style={styles.empty}>No bonuses right now.</Text> : null}
        </Card>

        <Card>
          <CardTitle>Recent wallet</CardTitle>
          {(wallet?.transactions ?? []).slice(0, 8).map((tx) => (
            <View key={tx.id ?? `${tx.created_at}-${tx.amount_cents}`} style={styles.row}>
              <Text style={styles.rowLabel}>{tx.description || tx.type || "Transaction"}</Text>
              <Text style={styles.rowValue}>{formatCents(tx.amount_cents)}</Text>
            </View>
          ))}
          {(wallet?.transactions ?? []).length === 0 ? (
            <Text style={styles.empty}>No wallet activity yet.</Text>
          ) : null}
        </Card>

        <Card>
          <CardTitle>Payouts</CardTitle>
          {(wallet?.payouts ?? []).slice(0, 6).map((payout) => (
            <View key={payout.id ?? payout.created_at} style={styles.row}>
              <Text style={styles.rowLabel}>
                {payout.status ?? "payout"} {formatWhen(payout.created_at)}
              </Text>
              <Text style={styles.rowValue}>{formatCents(payout.amount_cents)}</Text>
            </View>
          ))}
          {(wallet?.payouts ?? []).length === 0 ? (
            <Text style={styles.empty}>No payouts yet.</Text>
          ) : null}
        </Card>

        <Card>
          <CardTitle>Statements</CardTitle>
          {statements.map((row) => (
            <View key={row.id} style={styles.bonusRow}>
              <Text style={styles.rowLabel}>
                {row.period_label} · {row.deliveries} stops · {formatCents(row.net_cents)}
              </Text>
              <PrimaryButton
                tone="ghost"
                label={busy === row.id ? "Loading…" : "Details"}
                disabled={Boolean(busy)}
                onPress={() => {
                  setBusy(row.id);
                  void fetchStatementDetail(row.id)
                    .then(setDetail)
                    .catch((err: unknown) => {
                      setError(err instanceof Error ? err.message : "statement_failed");
                    })
                    .finally(() => setBusy(null));
                }}
              />
            </View>
          ))}
          {statements.length === 0 ? (
            <Text style={styles.empty}>Statements appear after the first payout cycle.</Text>
          ) : null}
          {detail ? (
            <View style={styles.detail}>
              <Text style={styles.rowLabel}>{detail.period_label || detail.id}</Text>
              <Text style={styles.meta}>Net {formatCents(detail.net_cents)}</Text>
              {(detail.lines ?? []).slice(0, 8).map((line, idx) => (
                <Text key={`${line.description}-${idx}`} style={styles.meta}>
                  {line.description || "Line"} · {formatCents(line.amount_cents)}
                </Text>
              ))}
              <PrimaryButton
                tone="ghost"
                label={busy === `dl-${detail.id}` ? "Exporting…" : "Share CSV"}
                disabled={Boolean(busy)}
                testID="statement-download"
                onPress={() => {
                  setBusy(`dl-${detail.id}`);
                  void downloadStatementCsv(detail.id)
                    .then(({ csv, filename }) => Share.share({ message: csv, title: filename }))
                    .catch((err: unknown) => {
                      setError(err instanceof Error ? err.message : "download_failed");
                    })
                    .finally(() => setBusy(null));
                }}
              />
            </View>
          ) : null}
        </Card>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  error: { ...typography.caption, color: colors.danger },
  flex: { flex: 1 },
  list: { gap: spacing.md, paddingBottom: spacing.xl },
  kpis: {
    flexDirection: "row",
    gap: spacing.md,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
  },
  row: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md },
  bonusRow: { gap: spacing.xs, marginBottom: spacing.sm },
  rowLabel: { ...typography.body, color: colors.primary, flex: 1 },
  rowValue: { ...typography.body, fontWeight: "600", color: colors.primary },
  empty: { ...typography.caption, color: colors.muted },
  meta: { ...typography.caption, color: colors.muted },
  detail: { gap: spacing.xs, marginTop: spacing.sm },
});
