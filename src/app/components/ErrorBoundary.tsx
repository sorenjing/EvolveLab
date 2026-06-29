"use client";

import React from "react";

/**
 * 全局错误边界：子组件抛出异常时显示友好提示，而非白屏。
 * 提供「重试」按钮重置内部状态。
 */
interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary 捕获异常:", error, info);
  }

  handleReset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center p-6">
          <div className="w-full max-w-md rounded-xl border border-red-300 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950">
            <h2 className="text-lg font-semibold text-red-700 dark:text-red-300">
              页面出错了
            </h2>
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
              {this.state.error.message || "未知错误"}
            </p>
            <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded bg-red-100 p-2 text-xs text-red-800 dark:bg-red-900/50 dark:text-red-200">
              {this.state.error.stack}
            </pre>
            <button
              type="button"
              onClick={this.handleReset}
              className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700"
            >
              重试
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
