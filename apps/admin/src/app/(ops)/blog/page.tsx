"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const BlogListClient = dynamic(() => import("@/components/blog/BlogListClient"), {
  loading: () => <Spinner label="Loading…" />,
});

export default function BlogPage() {
  return <BlogListClient />;
}
