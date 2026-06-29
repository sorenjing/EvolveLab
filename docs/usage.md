# 使用指南

本文档面向已部署/启动 EvolveLab 的最终用户，介绍如何使用各功能。部署请参考 [RUN.md](../RUN.md)。

## 目录

- [快速开始](#快速开始)
- [任务模板](#任务模板)
- [执行 Agent 任务](#执行-agent-任务)
- [阅读 Timeline](#阅读-timeline)
- [角色与权限](#角色与权限)
- [工具系统](#工具系统)
- [Agent 自我修改能力](#agent-自我修改能力)
- [暗黑模式](#暗黑模式)
- [常见问题](#常见问题)

---

## 快速开始

三步上手：

1. **启动**：按 [RUN.md](../RUN.md) 启动前后端
2. **配置 Key**：点击右上角「设置」按钮（黄点表示未配置），填入 LLM API Key，点「测试」确认连通后「保存」。配置存浏览器 localStorage，不上传后端
3. **执行任务**：点击首页任一任务模板（如「分析项目结构」），内容会自动填入输入框，点「执行」或 `Ctrl+Enter` 启动

> 第一次使用建议先跑「分析项目结构」模板，让 Agent 读一遍项目自身，你能直观看到每一步思考与动作。

---

## 任务模板

首页空闲时展示 6 个高频任务卡片，点击即填入输入框：

| 模板 | 用途 |
|------|------|
| 📁 分析项目结构 | 列目录、识别模块、总结架构 |
| 🔍 代码审查 | 扫描代码，给出安全/性能/可维护性建议 |
| 📝 生成 README | 基于代码现状自动生成项目文档 |
| 🔧 创建翻译工具 | 演示 Agent 自举新工具能力 |
| 🛡 检查项目安全 | 审查命令白名单与权限配置 |
| 📊 统计代码行数 | 按语言分类统计 |

任务执行后模板区自动隐藏（避免干扰），任务结束后回到空闲态会重新出现。

> 想自定义模板？编辑 `src/app/lib/templates.ts`，加一项即可。

---

## 执行 Agent 任务

### 输入任务

在文本框输入任意任务描述。任务越具体，效果越好：

- 差：`修复 bug`
- 好：`backend/api/routes.py 的 /agent/stream 接口在 SSE 流被客户端中断时未正确清理，请定位并修复`

### 角色选择

执行前在「角色」下拉选择，详见 [角色与权限](#角色与权限)。

### 快捷键

`Ctrl+Enter`（Windows/Linux）或 `Cmd+Enter`（macOS）启动任务。

### 中断

运行中「执行」按钮变为「停止」，点击即中断当前请求（前端 AbortController，后端不再产生新事件）。

### 结果展示

- **执行中**：Timeline 实时滚动展示每步思考→动作→观察
- **成功**：底部绿色卡片显示最终结果
- **失败**：顶部红色卡片显示错误信息，对应步骤卡片红色边框

---

## 阅读 Timeline

Timeline 是 EvolveLab 的核心可视化，每个 Step 包含三段：

| 字段 | 含义 | 颜色 |
|------|------|------|
| THOUGHT | Agent 当前的推理思考 | 蓝 |
| ACTION | 调用的工具与参数 | 黄 |
| OBSERVATION | 工具返回结果 | 灰 |
| ERROR | 该步出错（如有） | 红 |

### 状态徽章

每个 Step 卡片顶部显示状态色徽章：

- 🟢 **成功**：该步有 observation 且无错误标记
- 🔴 **失败**：observation 含 `[错误]` / `[失败]` / `[退出码 非零]`，或有 ERROR 字段
- 🔵 **运行中**：只有 thought/action，还没收到 observation

失败步骤的卡片边框变红，方便快速定位问题步骤。

### 折叠与展开

- **步骤级折叠**：点击 Step 标题行，折叠/展开整个步骤（适合步骤多时快速浏览）
- **长内容折叠**：observation 超 600 字符自动截断，点「展开全部（共 N 字符）」查看完整内容

### 调试建议

任务失败时，按顺序排查：
1. 看红色徽章的 Step，读其 ERROR / OBSERVATION
2. 若是工具调用参数错误，回到上一个 ACTION 看是否 JSON 格式有误
3. 若是 LLM 返回异常格式，可能是模型能力不足，换更强的模型（如 glm-4 代替 glm-4-flash）

---

## 角色与权限

Agent 内置三种角色，决定能调用哪些工具：

| 角色 | 说明 | 可用命令 |
|------|------|----------|
| **标准** standard（默认） | 日常任务，可读写文件、执行白名单命令 | `ls`、`cat`、`find`、`git status`、`git diff`、`git log` 等只读命令 |
| **管理员** admin | 含标准权限 + 删除文件、执行任意命令 | 标准 + `rm`、`mv`、`cp`、`mkdir`、构建命令等 |
| **只读** readonly | 仅可读，不可写不可执行 | 仅 `ls`、`cat`、`find`、`git status`、`git diff`、`git log` |

切换角色：点「设置」→ 在配置面板选，或在执行任务前于输入框旁选择。角色配置持久化到后端。

### 命令白名单

`execute_command` 工具只能在白名单内执行命令，白名单可增删：

- 查询/修改需通过管理接口（`POST /api/admin/whitelist`），默认仅 localhost 可调用
- 三层防御：白名单前缀匹配 → AST 参数审计 → 路径沙箱

> 安全设计详见 [DESIGN.md](../DESIGN.md) 的安全机制章节。

---

## 工具系统

EvolveLab 内置 **16 个工具** + 1 个特殊终止工具 `final_answer`：

### 文件操作（4 个）
- `read_file` — 读取文件
- `write_file` — 写入/覆盖文件
- `edit_file` — 基于 search/replace 修改
- `delete_file` — 删除文件（需管理员角色）

### 系统操作（3 个）
- `execute_command` — 执行白名单内命令
- `list_files` — 列目录
- `search_files` — 按文件名或内容搜索

### 截图与清理（2 个）
- `screenshot` — 截屏，返回 base64（支持视觉模型）
- `cleanup` — 清理 .bak 备份、过期截图、pycache

### 自我修改安全层（4 个）
- `create_snapshot` — 改源码前创建 Git 快照
- `verify_build` — 验证构建（后端语法 + 前端类型）
- `rollback` — 回滚到指定快照（验证失败时调用）
- `list_snapshots` — 列出所有快照

### 工具生命周期（3 个）
- `create_tool` — 创建并注册自定义工具
- `list_tools` — 列出所有工具
- `delete_tool` — 删除自定义工具

### 终止（1 个）
- `final_answer` — 任务完成，返回最终结果（Agent Kernel 特殊处理，不在 TOOLS dict）

### 工具面板

点右上角「工具」按钮打开面板，可：
- 查看所有内置 + 自定义工具及描述
- 删除自定义工具

---

## Agent 自我修改能力

EvolveLab 的核心特色是 **Agent 能改自己的代码**，且有安全闭环：

### 工作流

```
create_snapshot  →  edit_file (改源码)  →  verify_build
                                           │
                                   ┌───────┴───────┐
                                   │               │
                              验证通过          验证失败
                                   │               │
                            继续任务      rollback 回滚
```

### 示例任务

让 Agent 给自己加一个新工具：

```
任务：创建一个名为 translate_to_en 的工具，用于将中文翻译为英文，
创建后测试调用一次。
```

Agent 会调用 `create_tool`，传入工具名、描述、参数和 Python 代码。工具会持久化到 `backend/tools/custom/`，下次启动自动加载。

> 自定义工具的 `code` 参数需符合模板：定义 `TOOL_NAME`、`TOOL_DESCRIPTION`、`TOOL_ARGS` 和 `run(**kwargs) -> str` 函数。不传 code 会用空模板。

---

## 暗黑模式

右上角 ☾/☀ 按钮切换：

- 首次访问跟随系统偏好（`prefers-color-scheme`）
- 手动切换后记忆到 localStorage（`evolvelab_theme`），下次保持
- 切换在 HTML 渲染前就应用（内联脚本），避免暗色闪烁（FOUC）

---

## 常见问题

### Q: 执行任务后立即报错「后端响应异常: HTTP 401」？

A: API Key 无效或过期。点「设置」→「测试」验证连通性。

### Q: Agent 一直循环重复同样的思考？

A: 触发了死循环检测（默认连续 3 次相同 thought 自动终止）。这是保护机制。换更明确的任务描述，或换更强的模型。

### Q: 工具调用返回「权限不足」？

A: 当前角色不允许该操作。如 `delete_file` 需管理员角色，在角色下拉切换。

### Q: Agent 改代码后构建失败怎么办？

A: EvolveLab 设计了安全闭环。若 Agent 调用 `verify_build` 失败，应自动调用 `rollback` 回滚。若 Agent 未回滚，可手动：
```bash
cd backend
git stash   # 丢弃 Agent 的修改
# 或 git checkout <被改的文件>
```

### Q: 自定义工具重启后丢失？

A: 不会。自定义工具持久化在 `backend/tools/custom/` 目录，启动时自动加载。若丢失，检查目录权限或 `tools/registry.py` 的日志。

### Q: 想用其他 LLM 提供商？

A: 任意 OpenAI-compatible 接口都支持。在「设置」面板改 BaseURL 和 Model 即可。常见配置见 [RUN.md 的 LLM 提供商表](../RUN.md#支持的-llm-提供商)。

### Q: 前端报错白屏？

A: ErrorBoundary 会捕获并显示错误堆栈 + 重试按钮。点「重试」即可恢复，无需刷新。若持续报错，看浏览器控制台定位问题。

### Q: 如何查看历史会话？

A: 当前会话存后端（内存或 Redis）。访问 `GET /api/agent/session/{session_id}` 可查询某次会话状态。session_id 在执行任务时由后端生成，前端暂未展示——可从浏览器 Network 面板的 SSE 请求头 `X-Session-Id` 获取（如有）。

### Q: 速率限制被触发？

A: 默认全局 30 次/分钟，Agent 接口 10 次/分钟。等 1 分钟自动恢复。生产环境可在 `main.py` 调整 `default_limits`。

---

## 下一步

- 了解架构设计：[DESIGN.md](../DESIGN.md)
- 了解运行部署：[RUN.md](../RUN.md)
- 了解项目愿景与对比：[README.md](../README.md)
