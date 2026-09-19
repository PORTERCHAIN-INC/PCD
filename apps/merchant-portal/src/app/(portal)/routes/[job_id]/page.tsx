"use client";

import RouteJobDetail from "@/components/routes/RouteJobDetail";
import { useParams } from "next/navigation";

export default function RouteJobPage() {
  const { job_id } = useParams<{ job_id: string }>();
  if (!job_id) return <p className="text-muted">Missing route.</p>;
  return <RouteJobDetail jobId={job_id} />;
}
