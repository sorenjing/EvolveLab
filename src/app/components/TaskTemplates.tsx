import { TASK_TEMPLATES } from "@/app/lib/templates";

interface TaskTemplatesProps {
  onPick: (task: string) => void;
  disabled?: boolean;
}

/**
 * 任务模板首页：高频任务一键填入，降低上手成本。
 */
export function TaskTemplates({ onPick, disabled }: TaskTemplatesProps) {
  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold">任务模板</h2>
        <span className="text-xs text-zinc-400 dark:text-zinc-500">
          点击一键填入
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {TASK_TEMPLATES.map((t) => (
          <button
            key={t.title}
            type="button"
            disabled={disabled}
            onClick={() => onPick(t.task)}
            className="group flex flex-col gap-1 rounded-lg border border-zinc-200 p-3 text-left transition hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-800 dark:hover:border-zinc-600 dark:hover:bg-zinc-900"
          >
            <span className="flex items-center gap-2 text-sm font-medium">
              <span className="text-base">{t.icon}</span>
              {t.title}
            </span>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              {t.description}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
