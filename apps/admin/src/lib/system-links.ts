import { publicEnv } from "@/lib/env";

export type SystemLink = {
  id: string;
  label: string;
  description: string;
  href: string;
  /** Opens via Porterchain API SSO (Fleetbase console only). */
  fleetbaseSso?: boolean;
  /** Local dev port or production hostname hint. */
  port?: number;
  host?: string;
};

function url(envKey: string, fallback: string): string {
  const value = (process.env[envKey] ?? fallback).trim();
  return value.replace(/\/$/, "");
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
  return [
    {
      id: "website",
      label: "Website",
      description: "porterchain.com",
      href: url("NEXT_PUBLIC_WEBSITE_URL", "http://localhost:3000"),
      port: 3000,
      host: linkHost(url("NEXT_PUBLIC_WEBSITE_URL", "http://localhost:3000"), 3000, "porterchain.com"),
    },
    {
      id: "merchant",
      label: "Merchant Portal",
      description: "merchant.porterchain.com",
      href: url("NEXT_PUBLIC_MERCHANT_PORTAL_URL", "http://localhost:3001"),
      port: 3001,
      host: linkHost(
        url("NEXT_PUBLIC_MERCHANT_PORTAL_URL", "http://localhost:3001"),
        3001,
        "merchant.porterchain.com"
      ),
    },
    {
      id: "customer",
      label: "Customer Portal",
      description: "customer.porterchain.com",
      href: url("NEXT_PUBLIC_CUSTOMER_PORTAL_URL", "http://localhost:3004"),
      port: 3004,
      host: linkHost(
        url("NEXT_PUBLIC_CUSTOMER_PORTAL_URL", "http://localhost:3004"),
        3004,
        "customer.porterchain.com"
      ),
    },
    {
      id: "admin",
      label: "Admin",
      description: "admin.porterchain.com",
      href: url("NEXT_PUBLIC_SITE_URL", "http://localhost:3002"),
      port: 3002,
      host: linkHost(url("NEXT_PUBLIC_SITE_URL", "http://localhost:3002"), 3002, "admin.porterchain.com"),
    },
    {
      id: "driver",
      label: "Driver Portal",
      description: "driver.porterchain.com",
      href: url("NEXT_PUBLIC_DRIVER_PORTAL_URL", "http://localhost:3003"),
      port: 3003,
      host: linkHost(
        url("NEXT_PUBLIC_DRIVER_PORTAL_URL", "http://localhost:3003"),
        3003,
        "driver.porterchain.com"
      ),
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
      id: "fleetbase",
      label: "Fleetbase Console",
      description: "Dispatch & GPS (SSO)",
      href: url("NEXT_PUBLIC_FLEETBASE_CONSOLE_URL", "http://localhost:4200"),
      fleetbaseSso: true,
      port: 4200,
    },
    {
      id: "fleetbase-api",
      label: "Fleetbase API",
      description: "Logistics execution API",
      href: url("NEXT_PUBLIC_FLEETBASE_API_URL", "http://localhost:8000"),
      port: 8000,
    },
    {
      id: "valhalla",
      label: "Valhalla",
      description: "Routing engine status",
      href: url("NEXT_PUBLIC_VALHALLA_URL", "http://localhost:8002/status"),
      port: 8002,
    },
    {
      id: "mailhog",
      label: "Mailhog",
      description: "Dev email inbox",
      href: url("NEXT_PUBLIC_MAILHOG_URL", "http://localhost:8025"),
      port: 8025,
    },
  ];
}
