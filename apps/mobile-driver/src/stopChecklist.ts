/** Ordered field steps for the active stop — Arrive → Scan → POD → Leave. */

export type StopChecklistStepId = "arrive" | "scan" | "pod" | "leave";

export type StopChecklistStep = {
  id: StopChecklistStepId;
  label: string;
  status: "done" | "current" | "todo" | "skip";
};

export type StopChecklistInput = {
  hasStop: boolean;
  arrived: boolean;
  needsScan: boolean;
  scanComplete: boolean;
  needsPod: boolean;
  podReady: boolean;
  completed: boolean;
};

export function buildStopChecklist(input: StopChecklistInput): StopChecklistStep[] {
  if (!input.hasStop) return [];

  const steps: StopChecklistStep[] = [];
  let locked = false;

  const push = (id: StopChecklistStepId, label: string, done: boolean, skip = false) => {
    if (skip) {
      steps.push({ id, label, status: "skip" });
      return;
    }
    if (done) {
      steps.push({ id, label, status: "done" });
      return;
    }
    if (!locked) {
      steps.push({ id, label, status: "current" });
      locked = true;
      return;
    }
    steps.push({ id, label, status: "todo" });
  };

  push("arrive", "Arrive", input.arrived || input.completed);
  push("scan", "Scan packages", input.scanComplete || input.completed, !input.needsScan);
  push("pod", "Photo / signature", input.podReady || input.completed, !input.needsPod);
  push("leave", "Complete stop", input.completed);

  return steps;
}
