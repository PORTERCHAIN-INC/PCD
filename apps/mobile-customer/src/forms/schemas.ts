import { z } from "zod";

export const signInSchema = z.object({
  email: z.string().email("Enter a valid email"),
  phone: z.string().min(8, "Enter a valid phone").optional(),
});

export const quoteSchema = z.object({
  pickup: z.string().min(3, "Pickup required"),
  dropoff: z.string().min(3, "Dropoff required"),
  vehicle_class: z.enum(["bike", "car", "van", "truck"]),
  package_type: z.string().min(1),
  weight_kg: z.string().optional(),
  special_instructions: z.string().optional(),
});

export const bookingSchema = z.object({
  email: z.string().email(),
  phone: z.string().min(8),
  terms_accepted: z.literal(true, { errorMap: () => ({ message: "Accept terms to continue" }) }),
});

export const trackingLookupSchema = z.object({
  trackingNumber: z.string().min(6, "Enter tracking number"),
});

export const supportSchema = z.object({
  subject: z.string().min(3),
  description: z.string().optional(),
  order_id: z.string().optional(),
});

export const claimSchema = z.object({
  order_id: z.string().min(1, "Order required"),
  description: z.string().min(10, "Describe the issue"),
});

export type SignInForm = z.infer<typeof signInSchema>;
export type QuoteForm = z.infer<typeof quoteSchema>;
export type BookingForm = z.infer<typeof bookingSchema>;
export type TrackingLookupForm = z.infer<typeof trackingLookupSchema>;
export type SupportForm = z.infer<typeof supportSchema>;
export type ClaimForm = z.infer<typeof claimSchema>;
