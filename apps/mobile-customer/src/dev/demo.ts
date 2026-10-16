/**
 * Demo data for simulator screenshots and design review ONLY.
 * Active only in a development build with EXPO_PUBLIC_DEMO_DATA=1; release
 * builds (`__DEV__ === false`) can never return demo data.
 */
const on = typeof __DEV__ !== "undefined" && __DEV__ && process.env.EXPO_PUBLIC_DEMO_DATA === "1";

export function demoEnabled(): boolean {
  return on;
}

const now = Date.now();
const iso = (minsAgo: number) => new Date(now - minsAgo * 60_000).toISOString();

const KING = {
  formatted: "100 King St W, Toronto, ON M5X 1A9, Canada",
  place_id: "demo-king",
  lat: 43.6487,
  lng: -79.3817,
  postal: "M5X 1A9",
};
const MILTON = {
  formatted: "8450 Lawson Rd, Milton, ON L9T 5C6, Canada",
  place_id: "demo-milton",
  lat: 43.5183,
  lng: -79.8774,
  postal: "L9T 5C6",
};
const MISS = {
  formatted: "100 City Centre Dr, Mississauga, ON L5B 2C9, Canada",
  place_id: "demo-sq1",
  lat: 43.5931,
  lng: -79.6424,
  postal: "L5B 2C9",
};

const orders = [
  {
    order_id: "o1",
    order_number: "PC-1042",
    tracking_number: "PC-20261015-F4BC86",
    state: "IN_TRANSIT",
    amount_cents: 8475,
    currency: "CAD",
    pickup: MILTON,
    dropoff: KING,
    created_at: iso(95),
    goods_summary: "2 parcels",
    vehicle_class: "cargo_van",
  },
  {
    order_id: "o2",
    order_number: "PC-1031",
    tracking_number: "PC-20261012-91AC02",
    state: "DELIVERED",
    amount_cents: 4294,
    currency: "CAD",
    pickup: KING,
    dropoff: MISS,
    created_at: iso(60 * 24 * 3),
    goods_summary: "Medium box",
    vehicle_class: "sedan_suv",
  },
  {
    order_id: "o3",
    order_number: "PC-1017",
    tracking_number: "PC-20261004-77DE10",
    state: "DELIVERED",
    amount_cents: 12995,
    currency: "CAD",
    pickup: MILTON,
    dropoff: MISS,
    created_at: iso(60 * 24 * 11),
    goods_summary: "1 skid",
    vehicle_class: "box_16",
  },
];

const quote = {
  quote_id: "q-demo",
  state: "QUOTED",
  amount_cents: 8475,
  amount_display: "$84.75 CAD",
  currency: "CAD",
  expires_at: new Date(now + 14 * 60_000).toISOString(),
  distance_km: 52.4,
  pricing_breakdown: [
    { code: "base", label: "Base fare (first 10 km)", amount_cents: 3900 },
    { code: "distance", label: "Distance 42.4 km", amount_cents: 3600 },
    { code: "hst", label: "HST 13%", amount_cents: 975 },
  ],
  vehicle_class: "cargo_van",
  booking_mode: "parcels",
  pickup: MILTON,
  dropoff: KING,
};

function route(path: string, method: string): unknown {
  if (path === "/health") return { ok: true };
  if (path.startsWith("/v1/auth/customer/onboarding"))
    return { ready: true, blockers: [], status: "ready", steps: [], can_access_portal: true };
  if (path.startsWith("/v1/auth/session-context"))
    return { email: "tracy@kaylulu.com", permissions: ["customer.portal"], status: "active" };
  if (path.startsWith("/v1/customers/me/dashboard"))
    return {
      active_order: orders[0],
      orders,
      bookings: [
        {
          booking_id: "b1",
          booking_number: "BK-2207",
          state: "CONFIRMED",
          order_id: "o1",
          created_at: iso(95),
        },
      ],
      invoices: [
        {
          invoice_id: "i1",
          invoice_number: "INV-3311",
          order_id: "o2",
          amount_cents: 4294,
          currency: "CAD",
          stripe_receipt_url: "https://porterchain.com",
          created_at: iso(60 * 24 * 3),
        },
      ],
      payments: [
        {
          payment_id: "p1",
          status: "succeeded",
          amount_cents: 8475,
          currency: "CAD",
          order_id: "o1",
        },
      ],
      stats: { total_orders: 3, total_bookings: 3 },
    };
  if (path.startsWith("/v1/customers/me/support"))
    return method === "POST"
      ? { ticket_id: "t2", status: "open", subject: "x", created_at: iso(0) }
      : [
          {
            ticket_id: "t1",
            status: "resolved",
            subject: "Gate code for Milton warehouse",
            created_at: iso(60 * 30),
          },
        ];
  if (path.startsWith("/v1/customers/me/rebook/"))
    return {
      pickup: MILTON,
      dropoff: KING,
      vehicle_class: "cargo_van",
      booking_mode: "parcels",
      parcels: [{ preset_id: "medium" }],
      source_order_id: "o1",
      tracking_number: orders[0]!.tracking_number,
    };
  if (path.startsWith("/v1/booking-catalog"))
    return {
      vehicles: [
        { id: "sedan_suv", label: "Sedan / SUV", whole_vehicle_enabled: true },
        { id: "cargo_van", label: "Cargo van", whole_vehicle_enabled: true },
        { id: "box_16", label: "16 ft box truck", whole_vehicle_enabled: true },
      ],
      presets: [
        { id: "small", label: "Small" },
        { id: "medium", label: "Medium" },
        { id: "large", label: "Large" },
        { id: "skid", label: "Skid" },
        { id: "other", label: "Other", manual: true },
      ],
      included_km: 10,
    };
  if (path.startsWith("/v1/quotes/preview"))
    return { amount_cents: 8475, amount_display: "$84.75 CAD", distance_km: 52.4 };
  if (path.startsWith("/v1/quotes")) return quote;
  if (path.startsWith("/v1/notifications/inbox?"))
    return {
      unread_count: 1,
      items: [
        {
          id: "n1",
          title: "Your parcel is on the way",
          body: "Amrit picked up 2 parcels in Milton. ETA 2:40 PM.",
          read: false,
          created_at: iso(20),
          deep_link: "porterchain://track/PC-20261015-F4BC86",
        },
        {
          id: "n2",
          title: "Delivered",
          body: "PC-20261012-91AC02 was delivered and signed for.",
          read: true,
          created_at: iso(60 * 24 * 3),
          deep_link: "porterchain://track/PC-20261012-91AC02",
        },
      ],
    };
  if (path.startsWith("/v1/notifications")) return { ok: true };
  const m = /^\/v1\/orders\/([^/]+)(\/(experience|tracking))?$/.exec(path);
  if (m) {
    const o = orders.find((x) => x.tracking_number === decodeURIComponent(m[1]!)) ?? orders[0]!;
    if (m[3] === "tracking")
      return {
        order_id: o.order_id,
        tracking_number: o.tracking_number,
        state: o.state,
        live_tracking: {
          delivery_status: { label: "On the way", in_transit: true },
          eta: { label: "2:40 PM", arrives_at: new Date(now + 35 * 60_000).toISOString() },
        },
      };
    if (m[3] === "experience") throw new Error("order_not_found");
    return { ...o };
  }
  throw new Error("request_failed");
}

export async function demoRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  await new Promise((r) => setTimeout(r, 250));
  return route(path, (init.method ?? "GET").toUpperCase()) as T;
}
