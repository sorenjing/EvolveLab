import type { TimelineStep } from "@/app/lib/types";

export function Timeline({ steps }: { steps: TimelineStep[] }) {
  if (steps.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-300 p-8 text-center text-sm text-zinc-400 dark:border-zinc-700">
        执行轨迹将在此处实时显示
      </div>
    );
  }
  return (
    <section className="flex flex-col gap-3">
      {steps.map((s) => (
        <StepCard key={s.step} step={s} />
      ))}
    </section>
  );
}

function StepCard({ step }: { step: TimelineStep }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-zinc-500 dark:text-zinc-400">
        <span className="rounded bg-zinc-200 px-1.5 py-0.5 dark:bg-zinc-800">
          Step {step.step}
        </span>
      </div>
      <div className="flex flex-col gap-2 text-sm">
        {step.thought !== undefined && (
          <Field icon="THOUGHT" label="思考" tone="blue">
            <p className="whitespace-pre-wrap break-words">{step.thought}</p>
          </Field>
        )}
        {step.action && (
          <Field icon="ACTION" label="动作" tone="amber">
            <p className="font-mono text-xs">
              {step.action.tool}(
              {formatInput(step.action.input)})
            </p>
          </Field>
        )}
        {step.observation !== undefined && (
          <Field icon="OBSERVATION" label="观察" tone="zinc">
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words font-mono text-xs">
              {step.observation}
            </pre>
          </Field>
        )}
      </div>
    </div>
  );
}

function Field({
  icon,
  label,
  tone,
  children,
}: {
  icon: string;
  label: string;
  tone: "blue" | "amber" | "zinc";
  children: React.ReactNode;
}) {
  const toneClass = {
    blue: "border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-200",
    amber:
      "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200",
    zinc: "border-zinc-200 bg-zinc-50 text-zinc-800 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200",
  }[tone];
  return (
    <div className={`rounded-md border p-2 ${toneClass}`}>
      <div className="mb-1 flex items-center gap-2 text-[10px] font-bold tracking-wider opacity-70">
        <span>{icon}</span>
        <span>{label}</span>
      </div>
      {children}
    </div>
  );
}

function formatInput(input: unknown): string {
  if (input === null || input === undefined) return "";
  if (typeof input === "string") return input;
  try {
    return JSON.stringify(input);
  } catch {
    return String(input);
  }
}
