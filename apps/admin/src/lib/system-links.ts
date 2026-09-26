import { publicEnv } from "@/lib/env";

export type SystemLink = {
  id: string;
  label: string;
  description: string;
  href: string;
  /** Local dev port or production hostname hint. */
  port?: number;
  host?: string;
};

function isDevRuntime(): boolean {
  const appEnv = (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? "").trim();
  return appEnv === "development" || appEnv === "local";
}

/** Never fall back to localhost in a production admin bundle. */
function url(envKey: string, localFallback: string, prodFallback: string): string {
  const raw = (process.env[envKey] ?? "").trim();
  if (raw) return raw.replace(/\/$/, "");
  return (isDevRuntime() ? localFallback : prodFallback).replace(/\/$/, "");
}

function linkHost(href: string, localPort: number, prodHost: string): string {
  try {
    const { hostname } = new URL(href);
    if (hostname === "localhost" || hostname === "127.0.0.1") return `:${localPort}`;
    return prodHost;
  } catch {
    return prodHost;
  }
}

/** Local / deployed Porterchain ecosystem URLs — admin quick-launch panel. */
export function getSystemLinks(): SystemLink[] {
  const api = publicEnv.porterchainApiUrl;
  const website = url(
    "NEXT_PUBLIC_WEBSITE_URL",
    "http://localhost:3000",
    "https://porterchain.com"
  );
  const merchant = url(
    "NEXT_PUBLIC_MERCHANT_PORTAL_URL",
    "http://localhost:3001",
    "https://merchant.porterchain.com"
  );
  const customer = url(
    "NEXT_PUBLIC_CUSTOMER_PORTAL_URL",
    "http://localhost:3004",
    "https://customer.porterchain.com"
  );
  const admin = url(
    "NEXT_PUBLIC_SITE_URL",
    "http://localhost:3002",
    "https://admin.porterchain.com"
  );
  const driver = url(
    "NEXT_PUBLIC_DRIVER_PORTAL_URL",
    "http://localhost:3003",
    "https://driver.porterchain.com"
  );
  return [
    {
      id: "website",
      label: "Website",
      description: "porterchain.com",
      href: website,
      port: 3000,
      host: linkHost(website, 3000, "porterchain.com"),
    },
    {
      id: "merchant",
      label: "Merchant Portal",
      description: "merchant.porterchain.com",
      href: merchant,
      port: 3001,
      host: linkHost(merchant, 3001, "merchant.porterchain.com"),
    },
    {
      id: "customer",
      label: "Customer Portal",
      description: "customer.porterchain.com",
      href: customer,
      port: 3004,
      host: linkHost(customer, 3004, "customer.porterchain.com"),
    },
    {
      id: "admin",
      label: "Admin",
      description: "admin.porterchain.com",
      href: admin,
      port: 3002,
      host: linkHost(admin, 3002, "admin.porterchain.com"),
    },
    {
      id: "driver",
      label: "Driver Portal",
      description: "driver.porterchain.com",
      href: driver,
      port: 3003,
      host: linkHost(driver, 3003, "driver.porterchain.com"),
    },
    {
      id: "api",
      label: "Porterchain API",
      description: "api.porterchain.com",
      href: `${api}/docs`,
      port: 8001,
      host: "api.porterchain.com",
    },
    {
      id: "fleetbase-api",
      label: "Fleetbase API",
      description: "Permanent bond target (engineers)",
      href: url("NEXT_PUBLIC_FLEETBASE_API_URL", "http://localhost:8000", "http://localhost:8000"),
      port: 8000,
    },
    {
      id: "valhalla",
      label: "Valhalla",
      description: "Routing engine status",
      href: url(
        "NEXT_PUBLIC_VALHALLA_URL",
        "http://localhost:8002/status",
        "https://api.porterchain.com/status"
      ),
      port: 8002,
    },
    {
      id: "mailpit",
      label: "Mailpit",
      description: "Dev email inbox",
      href: url("NEXT_PUBLIC_MAILPIT_URL", "http://localhost:8025", "http://localhost:8025"),
      port: 8025,
    },
  ];
}
