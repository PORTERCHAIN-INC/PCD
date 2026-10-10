import { redirect } from "next/navigation";

/** Booking lives on Send. Stripe's cancel URL (/book?quote_id=) resumes the same quote there. */
export default async function BookPage({ searchParams }: { searchParams: Promise<{ quote_id?: string }> }) {
  const { quote_id } = await searchParams;
  redirect(quote_id ? `/send?quote_id=${encodeURIComponent(quote_id)}` : "/send");
}
