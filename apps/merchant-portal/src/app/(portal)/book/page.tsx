import dynamic from "next/dynamic";
import WithGoogleMaps from "@/components/maps/WithGoogleMaps";
import { PageSkeleton } from "@porterchain/ui/loading";

const BookDeliveryClient = dynamic(() => import("@/components/booking/BookDeliveryClient"), {
  loading: () => <PageSkeleton rows={6} />,
});

export default function BookPage() {
  return (
    <WithGoogleMaps>
      <BookDeliveryClient />
    </WithGoogleMaps>
  );
}
