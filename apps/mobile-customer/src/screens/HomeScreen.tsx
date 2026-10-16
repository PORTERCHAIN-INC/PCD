import { View } from "react-native";
import { fetchDashboard, type CustomerDashboard } from "../api";
import {
  bookAgainRoutes,
  formatMoney,
  friendlyDate,
  isActiveState,
  JOURNEY,
  orderStatus,
  shortAddress,
} from "../format";
import { sessionIdentity } from "../session";
import { spacing, usePalette } from "../theme";
import {
  Banner,
  Button,
  Card,
  EmptyNote,
  Icon,
  ListRow,
  Progress,
  SectionHeader,
  SkeletonList,
  StatusPill,
  Txt,
} from "../ui/kit";
import { Screen } from "../ui/Screen";
import { useRemote } from "../ui/useRemote";

type Props = {
  onBook: (rebookOrderId?: string) => void;
  onTrack: (tracking: string) => void;
  onActivity?: () => void;
};

let cachedDashboard: CustomerDashboard | null = null;

/** Last successful Home payload — used to skip the cold-start spinner on re-entry. */
export function peekCachedDashboard(): CustomerDashboard | null {
  return cachedDashboard;
}

function greeting(now = new Date()): string {
  const h = Number(
    now.toLocaleString("en-CA", { timeZone: "America/Toronto", hour: "numeric", hour12: false })
  );
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export function HomeScreen({ onBook, onTrack, onActivity }: Props) {
  const c = usePalette();
  const { data, loading, refreshing, error, offline, refresh } = useRemote(async () => {
    const d = await fetchDashboard();
    cachedDashboard = d;
    return d;
  }, cachedDashboard);

  const email = sessionIdentity().email;
  const first = email ? email.split("@")[0]!.split(/[._-]/)[0]! : "";
  const name = first ? first[0]!.toUpperCase() + first.slice(1) : "";
  const active = data?.active_order ?? data?.orders.find((o) => isActiveState(o.state)) ?? null;
  const again = bookAgainRoutes(data?.orders ?? []);
  const recent = (data?.orders ?? []).filter((o) => o.order_id !== active?.order_id).slice(0, 4);

  return (
    <Screen
      scroll
      testID="home"
      title={name ? `${greeting()}, ${name}` : greeting()}
      subtitle="Same-day delivery across the GTA."
      refreshing={refreshing}
      onRefresh={() => void refresh()}
    >
      {error ? (
        <Banner
          tone={offline ? "offline" : "danger"}
          text={offline ? "You're offline. Showing your last saved shipments." : error}
          action="Retry"
          onAction={() => void refresh()}
        />
      ) : null}

      <Button testID="home-book" icon="add" label="Book a delivery" onPress={() => onBook()} />

      {loading && !data ? <SkeletonList rows={3} /> : null}

      {active ? (
        <Card
          testID="home-active"
          accessibilityLabel={`Active shipment ${active.tracking_number}, ${orderStatus(active.state).label}. Opens tracking.`}
          onPress={() => onTrack(active.tracking_number)}
          style={{ backgroundColor: c.hero, gap: spacing.md }}
        >
          <View
            style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}
          >
            <Txt v="overline" tone="onHeroMuted">
              Active shipment
            </Txt>
            <Icon name="chevron-forward" size={18} color={c.onHeroMuted} />
          </View>
          <Txt v="title" tone="onHero">
            {orderStatus(active.state).label}
          </Txt>
          <Progress steps={JOURNEY} current={orderStatus(active.state).step} onDark />
          <Txt v="callout" tone="onHeroMuted">
            {shortAddress(active.pickup?.formatted) || "Pickup"} →{" "}
            {shortAddress(active.dropoff?.formatted) || "Drop-off"}
          </Txt>
          <Txt v="caption" tone="onHeroMuted">
            {active.tracking_number}
            {active.goods_summary ? ` · ${active.goods_summary}` : ""}
          </Txt>
        </Card>
      ) : null}

      {again.length ? (
        <>
          <SectionHeader title="Book again" />
          <Card style={{ paddingVertical: spacing.xs }}>
            {again.map((r) => (
              <ListRow
                key={r.order_id}
                testID={`book-again-${r.order_id}`}
                icon="repeat"
                title={`${r.from} → ${r.to}`}
                subtitle="Same addresses, vehicle and parcels"
                onPress={() => onBook(r.order_id)}
              />
            ))}
          </Card>
        </>
      ) : null}

      {data ? (
        <>
          <SectionHeader
            title="Recent shipments"
            action={recent.length ? "See all" : undefined}
            onAction={onActivity}
          />
          {recent.length === 0 && !active ? (
            <EmptyNote
              icon="cube-outline"
              title="No shipments yet"
              body="Book your first delivery. Tracking and receipts show up here."
              action="Book a delivery"
              onAction={() => onBook()}
            />
          ) : null}
          {recent.length ? (
            <Card style={{ paddingVertical: spacing.xs }}>
              {recent.map((order) => {
                const s = orderStatus(order.state);
                return (
                  <ListRow
                    key={order.order_id}
                    title={`${shortAddress(order.pickup?.formatted) || order.tracking_number} → ${shortAddress(order.dropoff?.formatted)}`}
                    subtitle={[
                      friendlyDate(order.created_at),
                      order.amount_cents != null
                        ? formatMoney(order.amount_cents, order.currency)
                        : "",
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                    right={<StatusPill label={s.label} tone={s.tone} />}
                    onPress={() => onTrack(order.tracking_number)}
                  />
                );
              })}
            </Card>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}
