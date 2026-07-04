import { z } from "zod";

export const driverLoginSchema = z.object({
  email: z.string().email("Enter a valid email"),
});

export type DriverLoginForm = z.infer<typeof driverLoginSchema>;
