"use client";

import { useState } from "react";
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

// 判断单步状态：有 error 字段或 observation 含失败标记 → 失败
function stepStatus(step: TimelineStep): "success" | "error" | "running" {
  if (step.error) return "error";
  const obs = step.observation ?? "";
  // 后端工具失败常见前缀
  if (obs.includes("[错误]") || obs.includes("[失败]") || /\[退出码 [1-9]/.test(obs)) {
    return "error";
  }
  // 有 observation 即视为该步完成
  if (step.observation !== undefined) return "success";
  return "running";
}

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  success: {
    label: "成功",
    cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  },
  error: {
    label: "失败",
    cls: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  },
  running: {
    label: "运行中",
    cls: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  },
};

// 长内容折叠阈值（字符数）
const COLLAPSE_THRESHOLD = 600;

function StepCard({ step }: { step: TimelineStep }) {
  const [collapsed, setCollapsed] = useState(false);
  const status = stepStatus(step);

  const borderCls =
    status === "error"
      ? "border-red-200 dark:border-red-900"
      : "border-zinc-200 dark:border-zinc-800";

  return (
    <div className={`rounded-lg border ${borderCls} bg-white p-4 shadow-sm dark:bg-zinc-950`}>
      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        className="mb-2 flex w-full items-center gap-2 text-xs font-semibold text-zinc-500 dark:text-zinc-400"
        aria-expanded={!collapsed}
      >
        <span className="rounded bg-zinc-200 px-1.5 py-0.5 dark:bg-zinc-800">
          Step {step.step}
        </span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] ${STATUS_BADGE[status].cls}`}
        >
          {STATUS_BADGE[status].label}
        </span>
        <span className="ml-auto text-zinc-400 dark:text-zinc-500">
          {collapsed ? "展开 ▸" : "折叠 ▾"}
        </span>
      </button>

      {!collapsed && (
        <div className="flex flex-col gap-2 text-sm">
          {step.thought !== undefined && (
            <Field icon="THOUGHT" label="思考" tone="blue">
              <p className="whitespace-pre-wrap break-words">{step.thought}</p>
            </Field>
          )}
          {step.action && (
            <Field icon="ACTION" label="动作" tone="amber">
              <p className="font-mono text-xs">
                {step.action.tool}({formatInput(step.action.input)})
              </p>
            </Field>
          )}
          {step.observation !== undefined && (
            <Field icon="OBSERVATION" label="观察" tone="zinc">
              <CollapsibleText text={step.observation} />
            </Field>
          )}
          {step.error && (
            <Field icon="ERROR" label="错误" tone="red">
              <p className="whitespace-pre-wrap break-words text-red-600 dark:text-red-400">
                {step.error}
              </p>
            </Field>
          )}
        </div>
      )}
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
  tone: "blue" | "amber" | "zinc" | "red";
  children: React.ReactNode;
}) {
  const toneClass = {
    blue: "border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-200",
    amber:
      "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200",
    zinc: "border-zinc-200 bg-zinc-50 text-zinc-800 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200",
    red: "border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
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

// 长内容折叠：超过阈值默认折叠，显示「展开全部」
function CollapsibleText({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const tooLong = text.length > COLLAPSE_THRESHOLD;
  const display = tooLong && !expanded ? text.slice(0, COLLAPSE_THRESHOLD) : text;
  return (
    <div>
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words font-mono text-xs">
        {display}
        {tooLong && !expanded && <span className="text-zinc-400"> …</span>}
      </pre>
      {tooLong && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
        >
          {expanded ? "收起" : `展开全部（共 ${text.length} 字符）`}
        </button>
      )}
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
