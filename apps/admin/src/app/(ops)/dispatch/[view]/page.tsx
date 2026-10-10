import { notFound } from "next/navigation";
import { DispatchShell } from "@/components/dispatch/DispatchShell";
import { DISPATCH_VIEWS, isDispatchView } from "@/lib/dispatch";

export function generateStaticParams() {
  return DISPATCH_VIEWS.map((view) => ({ view }));
}

export default async function DispatchViewPage({ params }: { params: Promise<{ view: string }> }) {
  const { view } = await params;
  if (!isDispatchView(view)) notFound();
  return <DispatchShell view={view} />;
}
