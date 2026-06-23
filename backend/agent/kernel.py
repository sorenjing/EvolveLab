"""
Agent Kernel：自研 ReAct 推理循环，负责多轮工具调度与状态管理。
"""
import asyncio
import uuid
from typing import AsyncGenerator, Any
from dataclasses import dataclass, field

from config import MAX_STEPS
from auth.permissions import get_permission_cache
from auth.capability import get_llm_capability
from tools import TOOLS, TOOLS_META, get_tool
from .prompts import build_system_prompt, build_user_prompt
from .llm import LLMClient
from .context import compress_history, extract_todos, build_compressed_user_prompt


@dataclass
class AgentEvent:
    type: str  # thought | action | observation | error | complete
    step: int
    payload: dict[str, Any] = field(default_factory=dict)


class AgentKernel:
    """ReAct Agent 内核：自己管理循环、解析、路由。"""

    def __init__(self, task: str, role: str = "standard", model: str = "", api_key: str = "", base_url: str = ""):
        self.task = task
        self.role = role
        self.session_id = str(uuid.uuid4())
        self.history: list[dict[str, Any]] = []
        self.step = 0
        self.max_steps = MAX_STEPS
        self.done = False

        self.perm = get_permission_cache()
        self.perm.set_role(role)
        self.cap = get_llm_capability(model)
        self.llm = LLMClient(model=model, api_key=api_key, base_url=base_url)

        # 根据视觉能力决定是否暴露 screenshot
        self.allow_screenshot = self.cap.detect()
        self.system_prompt = build_system_prompt(TOOLS_META, self.allow_screenshot)

    async def run(self) -> AsyncGenerator[AgentEvent, None]:
        """启动 ReAct 循环，逐事件通过 AsyncGenerator 产出。"""
        try:
            while self.step < self.max_steps and not self.done:
                self.step += 1

                # 0. 上下文压缩：步数过多时压缩旧历史，但保留 todo 和完成状态
                todos = extract_todos(self.history)
                compressed, recent = compress_history(self.history)
                effective_history = compressed + recent

                # 1. 构造 Prompt 并调用 LLM（使用压缩后的历史）
                if compressed:
                    user_prompt = build_compressed_user_prompt(self.task, effective_history, todos)
                else:
                    user_prompt = build_user_prompt(self.task, self.history)

                try:
                    parsed = await self.llm.chat(self.system_prompt, user_prompt)
                except Exception as e:
                    yield AgentEvent("error", self.step, {"message": f"LLM 调用失败: {e}"})
                    break

                thought = parsed.get("thought", "")
                action = parsed.get("action", "")
                action_input = parsed.get("actionInput", {})

                yield AgentEvent("thought", self.step, {"content": thought})
                yield AgentEvent("action", self.step, {"tool": action, "input": action_input})

                # 2. 执行工具或结束
                if action == "final_answer":
                    result = action_input.get("result", "")
                    self.history.append({"thought": thought, "action": action, "observation": result})
                    self.done = True
                    yield AgentEvent("complete", self.step, {"result": result})
                    break

                tool_fn = get_tool(action)
                if tool_fn is None:
                    observation = f"[错误] 未知工具: {action}"
                else:
                    # 视觉能力检测：若当前 LLM 不支持视觉，拦截 screenshot
                    if action == "screenshot" and not self.allow_screenshot:
                        observation = "[错误] 当前模型不支持视觉输入，无法使用截图工具。"
                    else:
                        try:
                            if asyncio.iscoroutinefunction(tool_fn):
                                observation = await tool_fn(**action_input)
                            else:
                                observation = tool_fn(**action_input)
                        except TypeError as te:
                            observation = f"[错误] 参数不匹配: {te}"
                        except Exception as e:
                            observation = f"[错误] 工具执行异常: {e}"

                yield AgentEvent("observation", self.step, {"result": observation})

                self.history.append({
                    "thought": thought,
                    "action": action,
                    "observation": observation,
                })

                # 3. 死循环检测：连续 3 次相同 action + input
                if self.step >= 3:
                    last_three = self.history[-3:]
                    if all(
                        h["action"] == action and h.get("observation") == observation
                        for h in last_three
                    ):
                        yield AgentEvent("error", self.step, {"message": "检测到死循环，强制终止"})
                        break

            if not self.done:
                yield AgentEvent("complete", self.step, {"result": "达到最大步数限制，任务未明确完成。"})
        finally:
            await self.llm.close()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task": self.task,
            "role": self.role,
            "step": self.step,
            "done": self.done,
            "history": self.history,
        }
