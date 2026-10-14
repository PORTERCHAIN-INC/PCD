import type { Metadata } from "next";
import { TodayOps } from "@/components/today/TodayOps";

export const metadata: Metadata = { title: "Today" };

export default function TodayPage() {
  return <TodayOps />;
}
