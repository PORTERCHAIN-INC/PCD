import type { FlowContext, FlowSpec, JobFlowSpecs } from "@porterchain/driver-flows";

/** Same mapping as the driver web (mobile-driver/src/flowContext.ts). */
export function flowFor(job: {
  flow_spec?: JobFlowSpecs | Record<string, never>;
  state?: string;
  signatures?: unknown[];
  photos?: unknown[];
}): { spec: FlowSpec | null; ctx: FlowContext; completed: number } {
  const fs = job.flow_spec as JobFlowSpecs | undefined;
  if (!fs?.delivery) return { spec: null, ctx: {}, completed: 0 };
  const picked =
    /PICKED_UP|IN_TRANSIT|ARRIVED_DROPOFF|AT_DESTINATION|NEAR_DELIVERY|OUT_FOR_DELIVERY|DELIVERED/.test(
      (job.state ?? "").toUpperCase()
    );
  const spec = picked ? fs.delivery : fs.pickup;
  const ctx: FlowContext = {
    signature: (job.signatures?.length ?? 0) > 0,
    photos: job.photos?.length ?? 0,
    flags: { cold_chain: fs.documents.includes("cold_chain_log") },
  };
  return { spec, ctx, completed: 0 };
}
