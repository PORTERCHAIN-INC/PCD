"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, MapPinned, MessageCircle, Package, ShieldCheck, Truck } from "lucide-react";
import Marquee from "@/components/magic/Marquee";
import ShimmerLink from "@/components/magic/ShimmerLink";
import { customerApi, REBOOK_STORAGE_KEY, type CustomerDashboard } from "@/lib/api";

const HIGHLIGHTS = [
  { icon: Truck, label: "Matched capacity" },
  { icon: MapPinned, label: "Live tracking" },
  { icon: ShieldCheck, label: "Proof of delivery" },
  { icon: Package, label: "Same-day lanes" },
] as const;

const FLEET = [
  {
    src: "/images/brand/vehicles/sedan.jpg",
    alt: "Sedan delivery capacity",
    label: "Sedan",
  },
  {
    src: "/images/brand/vehicles/cargo-van.jpg",
    alt: "Cargo van capacity",
    label: "Cargo van",
  },
  {
    src: "/images/brand/urban-delivery.jpg",
    alt: "Urban delivery on the road",
    label: "GTA lanes",
  },
  {
    src: "/images/brand/warehouse-loading.jpg",
    alt: "Warehouse loading",
    label: "Dock pickup",
  },
] as const;

type Props = {
  dashboard: CustomerDashboard | null;
  error?: string;
  getToken?: () => Promise<string | null>;
};

export default function CustomerWelcomeHome({ dashboard, error, getToken }: Props) {
  const router = useRouter();
  const active = dashboard?.active_order;
  const hasHistory = Boolean(dashboard?.orders?.length);
  const stats = dashboard?.stats;

  async function onRebook(orderId: string) {
    try {
      const token = getToken ? await getToken() : "dev";
      if (!token) return;
      const payload = await customerApi.rebook(token, orderId);
      sessionStorage.setItem(REBOOK_STORAGE_KEY, JSON.stringify(payload));
      router.push("/book?rebook=1");
    } catch {
      alert("Could not start rebook from this order.");
    }
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      <section className="customer-rise relative overflow-hidden rounded-2xl bg-primary text-white shadow-lg shadow-primary/10 sm:rounded-3xl lg:grid lg:min-h-[20rem] lg:grid-cols-[1.1fr_0.9fr]">
        <div className="absolute inset-0 lg:left-auto lg:w-1/2">
          <Image
            src="/images/brand/urban-delivery.jpg"
            alt=""
            fill
            priority
            className="object-cover object-center opacity-50 lg:opacity-70"
            sizes="(max-width: 1024px) 100vw, 520px"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-primary via-primary/80 to-primary/40 lg:bg-gradient-to-r lg:from-primary lg:via-primary/85 lg:to-primary/20" />
          <div aria-hidden className="customer-hero-glow absolute inset-0" />
        </div>

        <div className="relative z-10 flex flex-col justify-center px-5 py-7 sm:px-8 sm:py-10 lg:col-span-2 lg:max-w-xl lg:px-10">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-accent">
            Porterchain
          </p>
          <h1 className="mt-3 text-2xl font-semibold leading-tight tracking-tight sm:text-3xl lg:text-4xl">
            Welcome — capacity when you need it.
          </h1>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-white/75 sm:text-base">
            Quote lanes, book vehicle-and-driver capacity, and track every handoff in one place.
          </p>

          <div className="mt-6 max-w-sm">
            <ShimmerLink href="/book">Get a quote & book</ShimmerLink>
          </div>

          {active ? (
            <Link
              href={`/track/${active.tracking_number}`}
              className="mt-4 flex max-w-md items-center gap-3 rounded-2xl border border-white/15 bg-white/10 px-3.5 py-3 backdrop-blur-md transition-colors hover:bg-white/15"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary text-white">
                <MapPinned className="h-5 w-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-xs font-medium text-white/70">Active shipment</span>
                <span className="block truncate font-mono text-sm font-semibold">
                  {active.tracking_number}
                </span>
                <span className="block text-xs text-accent">{active.state}</span>
              </span>
            </Link>
          ) : null}
        </div>
      </section>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <section className="customer-rise-delay">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-muted">
          Quick actions
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <ActionTile href="/book" icon={Package} title="Book" subtitle="Quote & ship" accent />
          <ActionTile
            href={active ? `/track/${active.tracking_number}` : "/track"}
            icon={MapPinned}
            title="Track"
            subtitle={active ? "Live status" : "Enter tracking #"}
          />
          <ActionTile href="/notifications" icon={MessageCircle} title="Alerts" subtitle="Inbox" />
          <ActionTile
            href="/account"
            icon={FileText}
            title="Account"
            subtitle={
              stats?.total_orders != null
                ? `${stats.total_orders} shipment${stats.total_orders === 1 ? "" : "s"}`
                : "Support & privacy"
            }
          />
        </div>
      </section>

      <section className="customer-rise-delay-2">
        <Marquee>
          {HIGHLIGHTS.map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex shrink-0 items-center gap-2 rounded-full border border-primary/8 bg-white px-3.5 py-2 text-xs font-semibold text-primary shadow-sm"
            >
              <Icon className="h-3.5 w-3.5 text-secondary" />
              {label}
            </div>
          ))}
        </Marquee>
      </section>

      <section>
        <div className="mb-3 flex items-end justify-between">
          <h2 className="text-sm font-semibold text-primary sm:text-base">
            Capacity on your lanes
          </h2>
          <Link href="/book" className="text-xs font-semibold text-secondary sm:text-sm">
            See options
          </Link>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {FLEET.map((item) => (
            <Link
              key={item.label}
              href="/book"
              className="customer-fleet-card relative h-36 overflow-hidden rounded-2xl border border-primary/8 bg-white shadow-sm sm:h-40"
            >
              <Image src={item.src} alt={item.alt} fill className="object-cover" sizes="25vw" />
              <div className="absolute inset-0 bg-gradient-to-t from-primary/85 via-primary/20 to-transparent" />
              <span className="absolute bottom-3 left-3 text-sm font-semibold text-white">
                {item.label}
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section
        id="invoices"
        className="rounded-2xl border border-primary/8 bg-white p-4 shadow-sm sm:p-6"
      >
        <h2 className="text-sm font-semibold text-primary sm:text-base">Recent activity</h2>
        {!hasHistory && !active ? (
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
            No shipments yet. Get a quote and book your first delivery — tracking and invoices show
            up here.
          </p>
        ) : (
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {(dashboard?.orders ?? []).slice(0, 4).map((o) => (
              <li
                key={o.order_id}
                className="flex items-center gap-2 rounded-xl bg-gray-bg px-3 py-3"
              >
                <Link
                  href={`/track/${o.tracking_number}`}
                  className="min-w-0 flex-1 transition-colors hover:text-secondary"
                >
                  <span className="block font-mono text-xs font-semibold text-secondary">
                    {o.tracking_number}
                  </span>
                  <span className="text-xs text-muted">{o.state}</span>
                </Link>
                <button
                  type="button"
                  onClick={() => void onRebook(o.order_id)}
                  className="shrink-0 rounded-lg px-2 py-1 text-xs font-semibold text-secondary hover:bg-secondary/10"
                >
                  Rebook
                </button>
              </li>
            ))}
            {(dashboard?.invoices ?? []).slice(0, 2).map((inv) => (
              <li
                key={inv.invoice_id}
                className="flex items-center justify-between rounded-xl bg-gray-bg px-3 py-3"
              >
                <span className="font-mono text-xs text-primary">{inv.invoice_number}</span>
                <span className="text-xs text-muted">${(inv.amount_cents / 100).toFixed(2)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function ActionTile({
  href,
  icon: Icon,
  title,
  subtitle,
  accent,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle: string;
  accent?: boolean;
}) {
  return (
    <Link
      href={href}
      className={
        accent
          ? "customer-border-beam relative overflow-hidden rounded-2xl bg-white p-4 shadow-sm"
          : "rounded-2xl border border-primary/8 bg-white p-4 shadow-sm transition-colors hover:border-secondary/20"
      }
    >
      <span
        className={
          accent
            ? "relative z-10 flex h-10 w-10 items-center justify-center rounded-xl bg-secondary text-white"
            : "flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10 text-secondary"
        }
      >
        <Icon className="h-5 w-5" />
      </span>
      <span className="relative z-10 mt-3 block text-sm font-semibold text-primary">{title}</span>
      <span className="relative z-10 mt-0.5 block text-xs text-muted">{subtitle}</span>
    </Link>
  );
}
