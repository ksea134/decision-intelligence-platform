"""
orchestration/adk/agent_definition.py — ADKエージェント定義

エージェントの設定は config/agents.json から読み込む。
コード変更なしでエージェントの追加・プロンプト変更・モデル切替が可能。

設計原則:
- C05: グローバル状態は build_root_agent() で毎回リセット
- C06: 波括弧エスケープ等の既存ルールを適用
- C08: LLMに判断を委ねない
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent

from config.app_config import MODELS
from orchestration.adk.tools import query_bigquery

logger = logging.getLogger(__name__)

# ============================================================
# エージェント設定の読み込み
# ============================================================

_AGENTS_JSON_PATH = Path(__file__).parent.parent.parent / "config" / "agents.json"


def _load_agents_config() -> dict:
    """config/agents.json を読み込む。"""
    try:
        with open(_AGENTS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("[AgentDef] Failed to load agents.json: %s", e)
        return {"agents": [], "router": {}}


def _get_model_for_role(role: str) -> str:
    """ロール名からMODELSの値を取得する。"""
    return getattr(MODELS, role, MODELS.fast)


def _adk_safe(model_id: str, fallback: str = "gemini-2.5-flash") -> str:
    """ADKはGemini専用のため、Claudeが選ばれていてもGeminiにフォールバック。"""
    return model_id if model_id.startswith("gemini-") else fallback


# ============================================================
# エージェント構築
# ============================================================

_config = _load_agents_config()

# サブエージェントを生成
_sub_agents: dict[str, LlmAgent] = {}
for agent_conf in _config.get("agents", []):
    model_role = agent_conf.get("model_role", "fast")
    _sub_agents[agent_conf["name"]] = LlmAgent(
        name=agent_conf["name"],
        model=_adk_safe(_get_model_for_role(model_role)),
        instruction=agent_conf["instruction"],
        tools=[query_bigquery],
    )

# ルートエージェントを生成
_router_conf = _config.get("router", {})
root_agent = LlmAgent(
    name=_router_conf.get("name", "dip_root_agent"),
    model=_adk_safe(_get_model_for_role(_router_conf.get("model_role", "router"))),
    instruction=_router_conf.get("instruction", ""),
    sub_agents=list(_sub_agents.values()),
)

# 各エージェントの元のinstructionを保存（毎回リセットするため）
_BASE_INSTRUCTIONS = {name: agent.instruction for name, agent in _sub_agents.items()}


# ============================================================
# 公開関数
# ============================================================

def get_agents_info() -> list[dict]:
    """エージェント一覧を返す（API用）。"""
    agents_info = []
    for agent_conf in _config.get("agents", []):
        model_role = agent_conf.get("model_role", "fast")
        agents_info.append({
            "name": agent_conf["name"],
            "display_name": agent_conf.get("display_name", agent_conf["name"]),
            "model_role": model_role,
            "current_model": _adk_safe(_get_model_for_role(model_role)),
            "triggers": agent_conf.get("triggers", []),
        })
    # ルーター
    router_role = _router_conf.get("model_role", "router")
    agents_info.insert(0, {
        "name": _router_conf.get("name", "dip_root_agent"),
        "display_name": _router_conf.get("display_name", "ルーター"),
        "model_role": router_role,
        "current_model": _adk_safe(_get_model_for_role(router_role)),
        "triggers": [],
    })
    return agents_info


def build_root_agent(
    company: str = "",
    bq_schema: str = "",
    gcs_docs: str = "",
    knowledge: str = "",
    prompts: str = "",
    past_qa_context: str = "",
) -> LlmAgent:
    """
    ルートエージェントを構築して返す。
    各サブエージェントのinstructionに追加情報を注入する。
    注意: 毎回ベースinstructionからリセットしてから追記する（累積防止）。
    """
    # 企業固有のコンテキストを組み立て
    company_context = ""
    if company:
        company_context += f"\n\n対象企業: {company}\n"
    if bq_schema:
        safe_bq_schema = bq_schema.replace("{", "｛").replace("}", "｝") if isinstance(bq_schema, str) else str(bq_schema).replace("{", "｛").replace("}", "｝")
        company_context += f"\nBigQueryスキーマ:\n{safe_bq_schema}\n"
    if gcs_docs:
        # ADKがinstruction内の{...}をテンプレート変数と誤認するため、波括弧を全角に変換
        safe_gcs_docs = gcs_docs.replace("{", "｛").replace("}", "｝")
        company_context += (
            "\n【GCS資料（報告書・分析レポート — 必ず回答に反映すること）】\n"
            "※以下の資料には数値の背景・原因・考察が含まれている。\n"
            "※数値データ（BigQuery）と合わせて、資料の内容も必ず踏まえて回答すること。\n"
            "※数値だけの回答は不十分。資料に書かれた背景・要因・提言も含めること。\n"
            f"{safe_gcs_docs}\n"
        )
    if past_qa_context:
        safe_past_qa = past_qa_context.replace("{", "｛").replace("}", "｝")
        company_context += (
            "\n【過去の類似Q&A — 参考にして回答の一貫性を保つこと】\n"
            f"{safe_past_qa}\n"
        )
    if knowledge:
        safe_knowledge = knowledge.replace("{", "｛").replace("}", "｝")
        company_context += f"\n企業前提知識:\n{safe_knowledge}\n"
    if prompts:
        safe_prompts = prompts.replace("{", "｛").replace("}", "｝")
        company_context += f"\n回答スタイル指示:\n{safe_prompts}\n"

    # 出典情報の記載ルール（全エージェント共通）
    company_context += (
        "\n\n【出典情報の記載ルール（必須）】\n"
        "回答本文中でデータを参照した箇所に※1、※2のような米印番号を付けること。\n"
        "回答末尾に米印番号と参照したデータソース名の対応一覧を記載すること。\n"
        "実際に回答の根拠として使ったデータのみ記載（使っていないデータは書かない）。\n"
        "例: ※1：BQ:production_results  ※2：GCS:inspection_report.txt\n"
        "データソース名の形式: BQ:テーブル名 / GCS:ファイル名 / LOCAL:ファイル名\n"
        "\n\n【チャート描画タグ（任意）】\n"
        "数値データをチャートで可視化すると理解が深まる箇所には、以下の形式で <viz> タグを挿入:\n"
        '<viz type="bar" title="タイトル">\n'
        '｛"labels": ["A","B","C"], "data": [100,200,150]｝\n'
        "</viz>\n"
        '使えるtype: "bar"（比較）, "line"（推移）, "pie"（構成比）。最大3つまで。不要なら使わない。\n'
    )

    # ベースinstructionにリセットしてから企業コンテキストを追加（累積防止）
    # ADKエンジンはGemini専用のため、Claudeが選ばれていてもGeminiにフォールバック
    for name, agent in _sub_agents.items():
        agent.instruction = _BASE_INSTRUCTIONS[name] + company_context
        agent_conf = next((a for a in _config["agents"] if a["name"] == name), {})
        model_role = agent_conf.get("model_role", "fast")
        agent.model = _adk_safe(_get_model_for_role(model_role))

    router_role = _router_conf.get("model_role", "router")
    root_agent.model = _adk_safe(_get_model_for_role(router_role))

    return root_agent
