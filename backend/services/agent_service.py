"""
Agent 运行服务：创建内核、生成 SSE 事件流、管理会话。
"""
import json
from typing import AsyncGenerator

from agent.kernel import AgentKernel
from session_store import get_session_store
from exceptions import SessionNotFound
from logger import get_logger

log = get_logger("agent_service")


def create_agent(task: str, role: str, model: str, api_key: str, base_url: str) -> AgentKernel:
    """创建 Agent 内核并初始化会话存储。"""
    log.info("Agent 任务启动: task=%r role=%s model=%s", task[:80], role, model)
    kernel = AgentKernel(
        task=task, role=role, model=model, api_key=api_key, base_url=base_url
    )
    get_session_store().save(kernel.session_id, kernel.to_dict())
    return kernel


async def stream_events(kernel: AgentKernel) -> AsyncGenerator[str, None]:
    """运行 Agent 并以 SSE 格式逐事件产出。"""
    try:
        async for ev in kernel.run():
            yield f"data: {json.dumps({'type': ev.type, 'step': ev.step, 'payload': ev.payload}, ensure_ascii=False)}\n\n"
            get_session_store().save(kernel.session_id, kernel.to_dict())
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'step': kernel.step, 'payload': {'message': str(e)}}, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"


def get_session(session_id: str) -> dict:
    """查询会话状态，不存在则抛 SessionNotFound。"""
    data = get_session_store().get(session_id)
    if not data:
        raise SessionNotFound(f"会话 {session_id} 不存在")
    return data
