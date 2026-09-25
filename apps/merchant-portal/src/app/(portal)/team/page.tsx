import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const TeamClient = dynamic(() => import("@/components/team/TeamClient"), {
  loading: () => <PageSkeleton rows={5} />,
});

export default function TeamPage() {
  return <TeamClient />;
}
