"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const BlogNewClient = dynamic(() => import("@/components/blog/BlogNewClient"), {
  loading: () => <Spinner label="Loading…" />,
});

export default function BlogNewPage() {
  return <BlogNewClient />;
}
