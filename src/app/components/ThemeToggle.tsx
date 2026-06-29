"use client";

import { useEffect, useState } from "react";

const THEME_KEY = "evolvelab_theme";

type Theme = "light" | "dark";

/**
 * 主题切换按钮。
 * 初始值由 layout 注入的内联脚本已设置到 <html class>，
 * 这里负责同步 React 状态与 DOM class，并持久化到 localStorage。
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "dark" : "light");
  }, []);

  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    const root = document.documentElement;
    if (next === "dark") root.classList.add("dark");
    else root.classList.remove("dark");
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      // 忽略存储失败
    }
  };

  // 避免 SSR/CSR 不一致导致水合警告：挂载前渲染占位
  if (!mounted) {
    return (
      <button
        type="button"
        className="h-8 w-8 rounded-lg border border-zinc-300 dark:border-zinc-700"
        aria-label="切换主题"
      />
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="切换主题"
      title={theme === "dark" ? "切换到亮色" : "切换到暗色"}
      className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-300 text-sm transition hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
