import { STEPS, type Step } from "../useFieldShift.ts";

const LABELS: Record<Step, string> = { location: "Farm", crop: "Crop", priority: "Priorities", simulation: "Analysis", result: "Plan" };

/** Where the farmer is in the journey. */
export function Steps({ current }: { current: Step }) {
  const position = STEPS.indexOf(current);
  return (
    <nav className="journey-steps" aria-label="Steps">
      {STEPS.map((step, index) => (
        <span key={step} className={index < position ? "done" : index === position ? "current" : ""} aria-current={index === position ? "step" : undefined}>
          {LABELS[step]}
        </span>
      ))}
    </nav>
  );
}
