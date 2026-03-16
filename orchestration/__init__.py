"""
orchestration — オーケストレーション層パッケージ

Agent Router の中核となるワークフローとエージェントを定義する。

【修正履歴】
- 2026-03-16: google-genai 依存を遅延インポートに変更
"""
from orchestration.graph import (
    WorkflowState,
    ClassificationResult,
    AgentResult,
    IntentType,
    create_initial_state,
    build_workflow,
    compile_workflow,
    run_workflow,
)

# RouterAgent は google-genai に依存するため、必要な場合のみインポート
def get_router_agent():
    """RouterAgent を遅延インポートする"""
    from orchestration.agents.router_agent import RouterAgent
    return RouterAgent

def get_create_router_agent():
    """create_router_agent を遅延インポートする"""
    from orchestration.agents.router_agent import create_router_agent
    return create_router_agent

__all__ = [
    # State
    "WorkflowState",
    "ClassificationResult",
    "AgentResult",
    "IntentType",
    "create_initial_state",
    # Workflow
    "build_workflow",
    "compile_workflow",
    "run_workflow",
    # Agents (lazy import)
    "get_router_agent",
    "get_create_router_agent",
]
