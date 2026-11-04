import { OrgDetailClient } from "@/components/orgs/OrgDetailClient";

export default async function OrgDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <OrgDetailClient orgId={id} />;
}
