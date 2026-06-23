"use client";

import { useState, useRef, useCallback, useEffect } from "react";

// 后端地址：优先读环境变量，默认本地 8001（与 RUN.md 一致）
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8001";

// ---------- 类型定义 ----------

type AgentEventType = "thought" | "action" | "observation" | "error" | "complete";

interface AgentEvent {
  type: AgentEventType;
  step: number;
  payload: Record<string, unknown>;
}

// 单个步骤聚合：一个 step 可能先后收到 thought / action / observation
interface TimelineStep {
  step: number;
  thought?: string;
  action?: { tool: string; input: unknown };
  observation?: string;
  error?: string;
}

type RunStatus = "idle" | "running" | "done" | "error";

const ROLES = [
  { value: "standard", label: "标准" },
  { value: "admin", label: "管理员" },
  { value: "readonly", label: "只读" },
] as const;

// ---------- LLM 配置（localStorage 持久化，避免 .env 泄密） ----------

interface LlmConfig {
  apiKey: string;
  baseUrl: string;
  model: string;
}

const DEFAULT_CONFIG: LlmConfig = {
  apiKey: "",
  baseUrl: "https://open.bigmodel.cn/api/paas/v4",
  model: "glm-4-flash",
};

const CONFIG_STORAGE_KEY = "evolvingai_llm_config";

function loadConfig(): LlmConfig {
  if (typeof window === "undefined") return DEFAULT_CONFIG;
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!raw) return DEFAULT_CONFIG;
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_CONFIG;
  }
}

function saveConfig(cfg: LlmConfig): void {
  try {
    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(cfg));
  } catch {
    // 忽略存储失败
  }
}

// ---------- 主组件 ----------

export default function Home() {
  const [task, setTask] = useState("");
  const [role, setRole] = useState<string>("standard");
  const [steps, setSteps] = useState<TimelineStep[]>([]);
  const [status, setStatus] = useState<RunStatus>("idle");
  const [finalResult, setFinalResult] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");

  // LLM 配置（localStorage 持久化）
  const [config, setConfig] = useState<LlmConfig>(DEFAULT_CONFIG);
  const [showConfig, setShowConfig] = useState(false);
  const [showTools, setShowTools] = useState(false);
  const configLoaded = useRef(false);

  // 首次挂载从 localStorage 加载配置
  useEffect(() => {
    if (configLoaded.current) return;
    configLoaded.current = true;
    setConfig(loadConfig());
  }, []);

  // 用于中断 fetch
  const abortRef = useRef<AbortController | null>(null);

  // 将事件聚合到对应 step
  const applyEvent = useCallback((ev: AgentEvent) => {
    if (ev.type === "complete") {
      const result =
        typeof ev.payload.result === "string" ? ev.payload.result : "";
      setFinalResult(result);
      setStatus("done");
      return;
    }
    if (ev.type === "error") {
      const msg =
        typeof ev.payload.message === "string" ? ev.payload.message : "未知错误";
      setErrorMsg(msg);
      setStatus("error");
      return;
    }

    setSteps((prev) => {
      const idx = prev.findIndex((s) => s.step === ev.step);
      if (idx === -1) {
        // 新 step
        const next: TimelineStep = { step: ev.step };
        fillStep(next, ev);
        return [...prev, next];
      }
      const copy = [...prev];
      copy[idx] = { ...copy[idx] };
      fillStep(copy[idx], ev);
      return copy;
    });
  }, []);

  const runAgent = useCallback(async () => {
    if (!task.trim() || status === "running") return;

    // 检查 API Key 是否已配置
    if (!config.apiKey.trim()) {
      setErrorMsg("请先配置 LLM API Key（点击右上角「设置」按钮）");
      setShowConfig(true);
      return;
    }

    // 重置状态
    setSteps([]);
    setFinalResult("");
    setErrorMsg("");
    setStatus("running");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch(`${BACKEND_URL}/api/agent/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task: task.trim(),
          role,
          api_key: config.apiKey,
          base_url: config.baseUrl,
          model: config.model,
        }),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`后端响应异常: HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE 事件以空行分隔
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);
          if (data === "[DONE]") {
            // 流正常结束；若未收到 complete 事件，标记为 done
            setStatus((s) => (s === "running" ? "done" : s));
            return;
          }
          try {
            const ev = JSON.parse(data) as AgentEvent;
            applyEvent(ev);
          } catch {
            // 忽略无法解析的行
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") {
        setStatus("idle");
        return;
      }
      const msg = e instanceof Error ? e.message : String(e);
      setErrorMsg(msg);
      setStatus("error");
    } finally {
      abortRef.current = null;
    }
  }, [task, role, status, applyEvent, config]);

  const stopAgent = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const running = status === "running";

  return (
    <div className="min-h-screen w-full bg-zinc-50 text-zinc-900 dark:bg-black dark:text-zinc-100">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-8">
        <Header
          onOpenConfig={() => setShowConfig((v) => !v)}
          configReady={!!config.apiKey.trim()}
          onOpenTools={() => setShowTools((v) => !v)}
        />

        {showConfig && (
          <ConfigPanel
            config={config}
            onChange={setConfig}
            onSave={() => {
              saveConfig(config);
              setShowConfig(false);
            }}
          />
        )}

        {showTools && <ToolsPanel />}

        <InputArea
          task={task}
          role={role}
          running={running}
          onTaskChange={setTask}
          onRoleChange={setRole}
          onRun={runAgent}
          onStop={stopAgent}
        />

        {errorMsg && (
          <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            <p className="font-semibold">出错</p>
            <p className="mt-1 whitespace-pre-wrap break-all">{errorMsg}</p>
          </div>
        )}

        <Timeline steps={steps} />

        {finalResult && (
          <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-950">
            <p className="mb-2 text-sm font-semibold text-emerald-700 dark:text-emerald-300">
              最终结果
            </p>
            <p className="whitespace-pre-wrap break-words text-sm text-emerald-900 dark:text-emerald-100">
              {finalResult}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------- 辅助：将事件字段填入 step ----------

function fillStep(step: TimelineStep, ev: AgentEvent): void {
  switch (ev.type) {
    case "thought":
      step.thought = typeof ev.payload.content === "string" ? ev.payload.content : "";
      break;
    case "action":
      step.action = {
        tool: typeof ev.payload.tool === "string" ? ev.payload.tool : "",
        input: ev.payload.input,
      };
      break;
    case "observation":
      step.observation =
        typeof ev.payload.result === "string" ? ev.payload.result : "";
      break;
  }
}

// ---------- 子组件 ----------

function Header({
  onOpenConfig,
  configReady,
  onOpenTools,
}: {
  onOpenConfig: () => void;
  configReady: boolean;
  onOpenTools: () => void;
}) {
  return (
    <header className="flex items-center justify-between border-b border-zinc-200 pb-4 dark:border-zinc-800">
      <div>
        <h1 className="text-xl font-bold tracking-tight">EvolveLab</h1>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
          可视化 AI Agent 实验平台 · 看清每一步思考
        </p>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onOpenTools}
          className="rounded-lg border border-zinc-300 px-3 py-1.5 text-xs font-medium transition hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          工具
        </button>
        <button
          type="button"
          onClick={onOpenConfig}
          className="flex items-center gap-2 rounded-lg border border-zinc-300 px-3 py-1.5 text-xs font-medium transition hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          <span
            className={`h-2 w-2 rounded-full ${configReady ? "bg-emerald-500" : "bg-amber-500"}`}
            title={configReady ? "已配置" : "未配置 API Key"}
          />
          设置
        </button>
      </div>
    </header>
  );
}

// ---------- LLM 配置面板 ----------

function ConfigPanel({
  config,
  onChange,
  onSave,
}: {
  config: LlmConfig;
  onChange: (cfg: LlmConfig) => void;
  onSave: () => void;
}) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  const handleTest = useCallback(async () => {
    if (!config.apiKey.trim()) {
      setTestResult({ ok: false, message: "API Key 不能为空" });
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const resp = await fetch(`${BACKEND_URL}/api/config/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: config.apiKey,
          base_url: config.baseUrl,
          model: config.model,
        }),
      });
      const data = await resp.json();
      setTestResult({ ok: data.ok, message: data.message });
    } catch (e) {
      setTestResult({ ok: false, message: e instanceof Error ? e.message : String(e) });
    } finally {
      setTesting(false);
    }
  }, [config]);

  const update = (field: keyof LlmConfig, value: string) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <p className="mb-3 text-sm font-semibold">LLM 配置</p>
      <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
        配置仅保存在浏览器 localStorage，不会写入文件或上传 GitHub。
      </p>
      <div className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">API Key</span>
          <input
            type="password"
            value={config.apiKey}
            onChange={(e) => update("apiKey", e.target.value)}
            placeholder="your-api-key"
            className="rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:focus:border-zinc-300"
          />
        </label>
        <div className="flex gap-3">
          <label className="flex flex-1 flex-col gap-1 text-sm">
            <span className="font-medium">Base URL</span>
            <input
              type="text"
              value={config.baseUrl}
              onChange={(e) => update("baseUrl", e.target.value)}
              placeholder="https://open.bigmodel.cn/api/paas/v4"
              className="rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:focus:border-zinc-300"
            />
          </label>
          <label className="flex w-40 flex-col gap-1 text-sm">
            <span className="font-medium">Model</span>
            <input
              type="text"
              value={config.model}
              onChange={(e) => update("model", e.target.value)}
              placeholder="glm-4-flash"
              className="rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:focus:border-zinc-300"
            />
          </label>
        </div>
        {testResult && (
          <div
            className={`rounded-md border p-2 text-xs ${
              testResult.ok
                ? "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300"
                : "border-red-300 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
            }`}
          >
            {testResult.message}
          </div>
        )}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleTest}
            disabled={testing}
            className="rounded-lg border border-zinc-300 px-4 py-1.5 text-sm font-medium transition hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            {testing ? "测试中..." : "测试连接"}
          </button>
          <button
            type="button"
            onClick={onSave}
            className="rounded-lg bg-zinc-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            保存
          </button>
        </div>
      </div>
    </section>
  );
}

// ---------- 工具列表面板 ----------

interface ToolMeta {
  name: string;
  description: string;
  args: string[];
  custom?: boolean;
}

function ToolsPanel() {
  const [builtin, setBuiltin] = useState<ToolMeta[]>([]);
  const [custom, setCustom] = useState<ToolMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const resp = await fetch(`${BACKEND_URL}/api/tools`);
      const data = await resp.json();
      setBuiltin(data.builtin ?? []);
      setCustom(data.custom ?? []);
    } catch {
      // 忽略
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleDelete = useCallback(async (name: string) => {
    setDeleting(name);
    try {
      await fetch(`${BACKEND_URL}/api/tools/${name}`, { method: "DELETE" });
      await refresh();
    } finally {
      setDeleting(null);
    }
  }, [refresh]);

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-semibold">工具列表</p>
        <button
          type="button"
          onClick={refresh}
          className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
        >
          刷新
        </button>
      </div>
      {loading ? (
        <p className="text-sm text-zinc-500">加载中...</p>
      ) : (
        <div className="flex flex-col gap-4">
          <div>
            <p className="mb-2 text-xs font-medium text-zinc-500">
              内置工具 ({builtin.length})
            </p>
            <div className="flex flex-col gap-1.5">
              {builtin.map((t) => (
                <ToolItem key={t.name} tool={t} />
              ))}
            </div>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium text-zinc-500">
              自定义工具 ({custom.length})
              {custom.length === 0 && " · Agent 创建后会显示在这里"}
            </p>
            <div className="flex flex-col gap-1.5">
              {custom.length === 0 ? (
                <p className="text-xs text-zinc-400">暂无自定义工具</p>
              ) : (
                custom.map((t) => (
                  <ToolItem
                    key={t.name}
                    tool={t}
                    onDelete={handleDelete}
                    deleting={deleting === t.name}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function ToolItem({
  tool,
  onDelete,
  deleting,
}: {
  tool: ToolMeta;
  onDelete?: (name: string) => void;
  deleting?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-2 rounded-lg border border-zinc-200 px-3 py-2 dark:border-zinc-800">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-medium">{tool.name}</span>
          {tool.custom && (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-950 dark:text-amber-300">
              自定义
            </span>
          )}
        </div>
        <p className="mt-0.5 line-clamp-2 text-xs text-zinc-500 dark:text-zinc-400">
          {tool.description}
        </p>
        {tool.args.length > 0 && (
          <p className="mt-0.5 font-mono text-[10px] text-zinc-400">
            args: {tool.args.join(", ")}
          </p>
        )}
      </div>
      {onDelete && (
        <button
          type="button"
          onClick={() => onDelete(tool.name)}
          disabled={deleting}
          className="shrink-0 text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
        >
          {deleting ? "删除中" : "删除"}
        </button>
      )}
    </div>
  );
}

interface InputAreaProps {
  task: string;
  role: string;
  running: boolean;
  onTaskChange: (v: string) => void;
  onRoleChange: (v: string) => void;
  onRun: () => void;
  onStop: () => void;
}

function InputArea({
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

function Timeline({ steps }: { steps: TimelineStep[] }) {
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
