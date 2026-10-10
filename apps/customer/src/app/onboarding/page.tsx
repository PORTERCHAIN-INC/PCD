import { redirect } from "next/navigation";

/** No onboarding step: the customer row is created on first sign-in (and adopted from guest bookings). */
export default function OnboardingPage() {
  redirect("/send");
}
