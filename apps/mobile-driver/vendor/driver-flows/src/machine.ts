import { blockersFor } from "./checks";
import type { FlowContext, FlowSpec, FlowStep } from "./types";

export type FlowState = { spec: FlowSpec; index: number; done: boolean; warnings: string[] };

export function visibleSteps(spec: FlowSpec, flags: Record<string, boolean> = {}): FlowStep[] {
  return spec.steps.filter((s) => !s.only_if || flags[s.only_if] !== false);
}

export function start(spec: FlowSpec): FlowState {
  return { spec, index: 0, done: spec.steps.length === 0, warnings: [] };
}

export function current(state: FlowState, flags?: Record<string, boolean>): FlowStep | null {
  return state.done ? null : (visibleSteps(state.spec, flags)[state.index] ?? null);
}

export type AdvanceResult = { state: FlowState; blockedBy: string[] };

/** Try to finish the current step. Blocked steps stay put and report why. */
export function advance(state: FlowState, ctx: FlowContext): AdvanceResult {
  const steps = visibleSteps(state.spec, ctx.flags);
  const step = steps[state.index];
  if (!step || state.done) return { state, blockedBy: [] };
  const blockedBy = blockersFor(step.block_if, ctx, state.spec);
  if (blockedBy.length) return { state, blockedBy };
  const index = state.index + 1;
  return { state: { ...state, index, done: index >= steps.length }, blockedBy: [] };
}

export function progress(
  state: FlowState,
  flags?: Record<string, boolean>
): { step: number; of: number } {
  const of = visibleSteps(state.spec, flags).length;
  return { step: Math.min(state.index + 1, of), of };
}
