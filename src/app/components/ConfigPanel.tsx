"use client";

import { useState, useCallback } from "react";
import { BACKEND_URL, type LlmConfig } from "@/app/lib/types";

export function ConfigPanel({
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
      <div className="mb-3 rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">
        <strong>安全提示：</strong>API Key 仅保存在浏览器 localStorage，不会上传 GitHub。
        但 localStorage 非加密存储，共享电脑请改用环境变量 <code className="rounded bg-amber-100 px-1 dark:bg-amber-900">LLM_API_KEY</code> 注入后端（详见 RUN.md）。
      </div>
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
