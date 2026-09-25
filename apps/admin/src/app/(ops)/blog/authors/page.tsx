"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const BlogAuthorsClient = dynamic(() => import("@/components/blog/BlogAuthorsClient"), {
  loading: () => <Spinner label="Loading…" />,
});

export default function BlogAuthorsPage() {
  return <BlogAuthorsClient />;
}
