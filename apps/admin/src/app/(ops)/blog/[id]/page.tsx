"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const BlogEditClient = dynamic(() => import("@/components/blog/BlogEditClient"), {
  loading: () => <Spinner label="Loading…" />,
});

export default function BlogEditPage(props: { params: Promise<{ id: string }> }) {
  return <BlogEditClient {...props} />;
}
