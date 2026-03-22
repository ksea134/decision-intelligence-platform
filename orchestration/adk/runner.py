"""
orchestration/adk/runner.py — ADK ReasoningEngine アダプター

【役割】
ADKのRunnerを使ってエージェントを実行し、
既存のchat.pyが消費するイベント形式（str / dict）に変換する。

【設計原則】
- 既存のReasoningEngineと同じインターフェース（stream_events, generate_thought_process等）。
- chat.pyは変更不要（同じyield形式を維持）。
- ADKのEvent → chat.py互換のstr/dictへの変換はこのファイルに閉じる。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Generator

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from config.app_config import APP, MODELS
from config.cloud_config import CloudConfig
from domain.prompt_builder import build_system_prompt
from orchestration.agents.data_agent import DataAgent, DataContext
from orchestration.memory.session_memory import SessionMemory
from orchestration.adk.agent_definition import build_root_agent
from orchestration.adk.tools import set_tool_context

logger = logging.getLogger(__name__)


class ADKReasoningEngine:
    """
    ADKベースのReasoningEngine。
    既存のReasoningEngineと同じインターフェースを持ち、
    chat.pyから透過的に使用できる。
    """

    def __init__(
        self,
        client: Any,  # genai.Client（補足フェーズで使用）
        data_agent: DataAgent,
        memory: SessionMemory,
        search_client: Any = None,
    ) -> None:
        self._client = client
        self._data_agent = data_agent
        self._memory = memory
        self._search_client = search_client

    def stream_events(
        self,
        user_prompt: str,
        company: str,
        cfg: CloudConfig,
        data_ctx: DataContext,
    ) -> Generator[Any, None, None]:
        """
        ADKエージェントを実行し、chat.py互換のイベントをyieldする。
        """
        if not user_prompt or not str(user_prompt).strip():
            raise ValueError(f"user_prompt cannot be empty: {repr(user_prompt)}")

        logger.info("[ADK] stream_events: user_prompt=%s...", user_prompt[:50])

        # AI処理フロー記録
        flow_steps = []
        flow_steps.append({"step": "質問理解", "done": True, "detail": MODELS.router})

        # ツールコンテキストを設定
        set_tool_context(
            data_agent=self._data_agent,
            search_client=self._search_client,
            data_ctx=data_ctx,
            company=company,
            user_prompt=user_prompt,
        )

        # 過去事例検索（ADK実行前に必ず実行 — LLMの判断に任せない）
        past_qa_context = ""
        if self._search_client and self._search_client.is_ready():
            try:
                similar_qas = self._search_client.search(query=user_prompt, company=company, top_k=3)
                if similar_qas:
                    parts = []
                    for i, qa in enumerate(similar_qas, 1):
                        parts.append(f"事例{i}:\n  質問: {qa.get('question', '')}\n  回答: {qa.get('answer', '')}")
                    past_qa_context = "\n\n".join(parts)
                    flow_steps.append({"step": "過去事例検索", "done": True, "detail": f"{len(similar_qas)}件の類似事例を発見"})
                else:
                    flow_steps.append({"step": "過去事例検索", "done": True, "detail": "類似事例なし"})
            except Exception as e:
                logger.warning("[ADK] Past QA search failed: %s", e)
                flow_steps.append({"step": "過去事例検索", "done": True, "detail": "検索スキップ"})
        else:
            flow_steps.append({"step": "過去事例検索", "done": True, "detail": "未接続"})

        # 企業固有コンテキストでエージェントを構築
        root_agent = build_root_agent(
            company=company,
            bq_schema=data_ctx.bq_result.content if data_ctx.bq_connected else "",
            gcs_docs=data_ctx.gcs_result.content,
            knowledge=data_ctx.assets.knowledge_text,
            prompts=data_ctx.assets.prompt_text,
            past_qa_context=past_qa_context,
        )
        flow_steps.append({"step": "ルートエージェント", "done": True, "detail": "質問を分析"})

        # ADK Runner を作成・実行
        import asyncio

        runner = InMemoryRunner(agent=root_agent, app_name="dip")

        # InMemorySessionServiceはasyncなのでイベントループで実行
        loop = asyncio.new_event_loop()
        session = loop.run_until_complete(
            runner.session_service.create_session(
                app_name="dip",
                user_id="dip_user",
            )
        )
        loop.close()

        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_prompt)],
        )

        yield {"status": "エージェントが処理しています..."}

        # ADKイベントを処理
        agent_name_seen = set()
        final_text_parts = []

        try:
            for event in runner.run(
                user_id="dip_user",
                session_id=session.id,
                new_message=user_content,
            ):
                # エージェント名をトラッキング
                if event.author and event.author not in agent_name_seen:
                    agent_name_seen.add(event.author)
                    agent_labels = {
                        "analysis_agent": "要因分析",
                        "comparison_agent": "比較分析",
                        "forecast_agent": "予測分析",
                        "general_agent": "汎用回答",
                        "dip_root_agent": "ルーター",
                    }
                    agent_models = {
                        "analysis_agent": MODELS.deep,
                        "comparison_agent": MODELS.deep,
                        "forecast_agent": MODELS.deep,
                        "general_agent": MODELS.fast,
                        "dip_root_agent": MODELS.router,
                    }
                    label = agent_labels.get(event.author, event.author)
                    model = agent_models.get(event.author, "")
                    if event.author == "dip_root_agent":
                        flow_steps.append({"step": "ルートエージェント", "done": True, "detail": model})
                    else:
                        flow_steps.append({"step": f"{label}エージェント", "done": True, "detail": model})
                        yield {"agent_type": event.author, "confidence": 0.9, "status": f"{label}モード"}

                # テキスト応答を取得
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text and event.is_final_response():
                            final_text_parts.append(part.text)

                        # function_callの実行をトラッキング
                        if hasattr(part, "function_call") and part.function_call:
                            fc_name = part.function_call.name
                            if fc_name == "query_bigquery":
                                flow_steps.append({"step": "データ取得", "done": True, "detail": "BigQueryからデータ取得"})
                                yield {"status": "データを取得しています..."}
                            elif fc_name == "search_past_qa":
                                # エージェントが追加検索を実行（メイン検索は実行済み）
                                logger.info("[ADK] Agent called search_past_qa (additional search)")

        except Exception as e:
            logger.error("[ADK] Runner error: %s", e)
            yield f"エラーが発生しました: {str(e)}"

        # 回答生成完了 — テキストをyield（tool_codeフィルタはchat.pyで実施）
        full_text = "".join(final_text_parts)
        if full_text:
            yield full_text

        # BQテーブル情報をyield（tools.pyで記録されたテーブル名を取得）
        from orchestration.adk import tools as _tools
        if _tools._last_bq_tables:
            yield {"bq_tables": list(_tools._last_bq_tables)}

        flow_steps.append({"step": "回答生成", "done": True, "detail": MODELS.deep})
        yield {"flow_steps": list(flow_steps)}

        # Q&A自動保存（Vertex AI Search）
        if self._search_client and self._search_client.is_ready() and full_text:
            try:
                # agent_typeを特定
                agent_type = "general"
                for name in agent_name_seen:
                    if name in ("analysis_agent", "comparison_agent", "forecast_agent"):
                        agent_type = name.replace("_agent", "")
                        break
                self._search_client.store(
                    question=user_prompt,
                    answer=full_text[:2000],
                    company=company,
                    intent=agent_type,
                )
            except Exception:
                pass

    # ----------------------------------------------------------
    # 補足フェーズ（既存のReasoningEngineと同じ実装を使用）
    # ----------------------------------------------------------

    def generate_thought_process(
        self,
        user_question: str,
        assistant_answer: str,
        structured_data: str,
        unstructured_data: str,
    ) -> str:
        """思考ロジック生成（既存実装を流用）。"""
        prompt = (
            "以下のQ&Aについて、AIがどのような思考プロセスで回答したかを簡潔に説明してください。\n\n"
            f"質問: {user_question}\n\n"
            f"回答: {assistant_answer[:APP.prompt_content_limit]}\n\n"
            "思考プロセスを以下の形式で:\n"
            "1. 質問の意図の理解\n"
            "2. 参照したデータ\n"
            "3. 分析のアプローチ\n"
            "4. 結論の導出\n"
        )
        try:
            response = self._client.models.generate_content(
                model=MODELS.supplement,
                contents=prompt,
            )
            return (response.text or "").strip()
        except Exception as e:
            logger.error("[ADK] Thought process error: %s", e)
            return ""

    def generate_infographic(
        self,
        content: str,
        timestamp: str = "",
        company: str = "",
    ) -> tuple[str, dict[str, Any]]:
        """インフォグラフィック生成（既存ReasoningEngineの実装を委譲）。"""
        # 既存のReasoningEngineのメソッドを再利用
        from orchestration.reasoning_engine import ReasoningEngine
        temp_engine = ReasoningEngine(
            client=self._client,
            data_agent=self._data_agent,
            memory=self._memory,
        )
        return temp_engine.generate_infographic(content, timestamp, company)

    def generate_deep_dive(
        self,
        user_question: str,
        assistant_answer: str,
    ) -> list[str]:
        """深掘り質問生成（既存ReasoningEngineの実装を委譲）。"""
        from orchestration.reasoning_engine import ReasoningEngine
        temp_engine = ReasoningEngine(
            client=self._client,
            data_agent=self._data_agent,
            memory=self._memory,
        )
        return temp_engine.generate_deep_dive(user_question, assistant_answer)
