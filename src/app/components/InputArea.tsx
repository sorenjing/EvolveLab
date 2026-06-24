import { ROLES } from "@/app/lib/types";

interface InputAreaProps {
  task: string;
  role: string;
  running: boolean;
  onTaskChange: (v: string) => void;
  onRoleChange: (v: string) => void;
  onRun: () => void;
  onStop: () => void;
}

export function InputArea({
  task,
  role,
  running,
  onTaskChange,
  onRoleChange,
  onRun,
  onStop,
}: InputAreaProps) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <label htmlFor="task" className="text-sm font-medium">
        任务描述
      </label>
      <textarea
        id="task"
        value={task}
        onChange={(e) => onTaskChange(e.target.value)}
        disabled={running}
        placeholder="例如：列出当前项目根目录的文件，并总结项目结构。"
        rows={3}
        className="w-full resize-y rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none transition focus:border-zinc-900 dark:border-zinc-700 dark:focus:border-zinc-300 disabled:opacity-50"
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            onRun();
          }
        }}
      />
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-zinc-500 dark:text-zinc-400">角色</span>
          <select
            value={role}
            onChange={(e) => onRoleChange(e.target.value)}
            disabled={running}
            className="rounded-lg border border-zinc-300 bg-transparent px-2 py-1 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:focus:border-zinc-300 disabled:opacity-50"
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        <div className="flex-1" />
        {running ? (
          <button
            type="button"
            onClick={onStop}
            className="rounded-lg border border-red-300 px-4 py-1.5 text-sm font-medium text-red-600 transition hover:bg-red-50 dark:border-red-900 dark:hover:bg-red-950"
          >
            停止
          </button>
        ) : (
          <button
            type="button"
            onClick={onRun}
            disabled={!task.trim()}
            className="rounded-lg bg-zinc-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            执行 (Ctrl+Enter)
          </button>
        )}
      </div>
    </section>
  );
}
