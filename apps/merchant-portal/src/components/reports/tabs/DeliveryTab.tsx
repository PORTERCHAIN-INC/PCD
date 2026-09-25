"use client";

import { OrdersPerformanceChart, PerformanceChart } from "@/components/dashboard/PerformanceChart";
import { formatPercent, type DeliveryPerformance, type ReportsOverview } from "@/lib/reports";
import { formatCents } from "@/lib/utils";
import { Metric, RankedList } from "./shared";

export function DeliveryTab({ data }: { data: DeliveryPerformance }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Bookings this month" value={String(data.total_orders)} />
        <Metric label="Delivered" value={String(data.delivered)} />
        <Metric
          label="On-time"
          value={formatPercent(data.on_time_percent)}
          hint={
            data.on_time_sample_size
              ? `${data.on_time_orders ?? 0} of ${data.on_time_sample_size} scored`
              : "Needs a promised time and a delivered event"
          }
        />
        <Metric
          label="Delivered of bookings"
          value={formatPercent(data.delivery_success_percent)}
        />
        <Metric label="Failed deliveries" value={String(data.failed_deliveries)} />
        <Metric label="Failed of bookings" value={formatPercent(data.failed_percent)} />
        <Metric label="Returned" value={String(data.returned)} />
        <Metric
          label="Avg delivery (hrs)"
          value={data.avg_delivery_hours == null ? "—" : String(data.avg_delivery_hours)}
        />
        <Metric
          label="Avg pickup (hrs)"
          value={data.avg_pickup_hours == null ? "—" : String(data.avg_pickup_hours)}
        />
      </div>
    </div>
  );
}

export function OrderVolumeTab({ data }: { data: ReportsOverview["order_volume"] }) {
  const monthlyOrders = data.monthly_trends.labels.map((label, i) => ({
    label,
    value: data.monthly_trends.orders[i] ?? 0,
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-2">
        <OrdersPerformanceChart series={data.daily_orders} />
        <PerformanceChart title="Monthly orders" subtitle="6-month trend" series={monthlyOrders} />
      </div>
      <RankedList
        title="Top routes by volume"
        empty="No orders this period"
        rows={data.top_routes.map((r) => ({ label: r.route, count: r.count }))}
      />
    </div>
  );
}

export function DestinationsTab({
  destinations,
}: {
  destinations: Array<{ destination: string; count: number }>;
}) {
  return (
    <RankedList
      title="Top destinations"
      empty="No destination data"
      rows={destinations.map((d) => ({ label: d.destination, count: d.count }))}
    />
  );
}

export function DeliverySection({
  delivery,
  orderVolume,
  destinations,
}: {
  delivery: DeliveryPerformance;
  orderVolume: ReportsOverview["order_volume"];
  destinations: ReportsOverview["top_destinations"]["destinations"];
}) {
  return (
    <div className="space-y-6">
      <DeliveryTab data={delivery} />
      <OrderVolumeTab data={orderVolume} />
      <DestinationsTab destinations={destinations} />
    </div>
  );
}
