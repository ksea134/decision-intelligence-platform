"""
orchestration/agents — エージェントパッケージ

各種エージェント（Router, Analysis, Comparison, Forecast, General）を定義する。

【修正履歴】
- 2026-03-16: google-genai 依存を遅延インポートに変更
- 2026-03-16: Step 3 - 全エージェントを追加
"""

# -----------------------------------------------------------------------------
# 遅延インポート関数（google-genai 依存）
# -----------------------------------------------------------------------------

def get_router_agent():
    """RouterAgent クラスを遅延インポートする"""
    from orchestration.agents.router_agent import RouterAgent
    return RouterAgent

def get_create_router_agent():
    """create_router_agent 関数を遅延インポートする"""
    from orchestration.agents.router_agent import create_router_agent
    return create_router_agent

def get_router_model():
    """ROUTER_MODEL 定数を遅延インポートする"""
    from orchestration.agents.router_agent import ROUTER_MODEL
    return ROUTER_MODEL

def get_router_system_prompt():
    """ROUTER_SYSTEM_PROMPT 定数を遅延インポートする"""
    from orchestration.agents.router_agent import ROUTER_SYSTEM_PROMPT
    return ROUTER_SYSTEM_PROMPT


# -----------------------------------------------------------------------------
# BaseAgent（共通基底クラス）
# -----------------------------------------------------------------------------

def get_base_agent():
    """BaseAgent クラスを遅延インポートする"""
    from orchestration.agents.base_agent import BaseAgent
    return BaseAgent


# -----------------------------------------------------------------------------
# 専門エージェント
# -----------------------------------------------------------------------------

def get_analysis_agent():
    """AnalysisAgent クラスを遅延インポートする"""
    from orchestration.agents.analysis_agent import AnalysisAgent
    return AnalysisAgent

def get_create_analysis_agent():
    """create_analysis_agent 関数を遅延インポートする"""
    from orchestration.agents.analysis_agent import create_analysis_agent
    return create_analysis_agent

def get_comparison_agent():
    """ComparisonAgent クラスを遅延インポートする"""
    from orchestration.agents.comparison_agent import ComparisonAgent
    return ComparisonAgent

def get_create_comparison_agent():
    """create_comparison_agent 関数を遅延インポートする"""
    from orchestration.agents.comparison_agent import create_comparison_agent
    return create_comparison_agent

def get_forecast_agent():
    """ForecastAgent クラスを遅延インポートする"""
    from orchestration.agents.forecast_agent import ForecastAgent
    return ForecastAgent

def get_create_forecast_agent():
    """create_forecast_agent 関数を遅延インポートする"""
    from orchestration.agents.forecast_agent import create_forecast_agent
    return create_forecast_agent

def get_general_agent():
    """GeneralAgent クラスを遅延インポートする"""
    from orchestration.agents.general_agent import GeneralAgent
    return GeneralAgent

def get_create_general_agent():
    """create_general_agent 関数を遅延インポートする"""
    from orchestration.agents.general_agent import create_general_agent
    return create_general_agent


__all__ = [
    # Router
    "get_router_agent",
    "get_create_router_agent",
    "get_router_model",
    "get_router_system_prompt",
    # Base
    "get_base_agent",
    # Analysis
    "get_analysis_agent",
    "get_create_analysis_agent",
    # Comparison
    "get_comparison_agent",
    "get_create_comparison_agent",
    # Forecast
    "get_forecast_agent",
    "get_create_forecast_agent",
    # General
    "get_general_agent",
    "get_create_general_agent",
]
