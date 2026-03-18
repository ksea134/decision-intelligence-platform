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

from config.app_config import APP
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
        flow_steps.append({"step": "質問理解", "done": True})

        # ツールコンテキストを設定
        set_tool_context(
            data_agent=self._data_agent,
            search_client=self._search_client,
            data_ctx=data_ctx,
            company=company,
        )

        # 企業固有コンテキストでエージェントを構築
        root_agent = build_root_agent(
            company=company,
            bq_schema=data_ctx.bq_result.content if data_ctx.bq_connected else "",
            knowledge=data_ctx.assets.knowledge_text,
            prompts=data_ctx.assets.prompt_text,
        )

        flow_steps.append({"step": "過去事例検索", "done": True, "detail": "エージェントが自動実行"})
        flow_steps.append({"step": "ルートエージェント", "done": True, "detail": "質問を分析中"})

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
                    label = agent_labels.get(event.author, event.author)
                    if event.author != "dip_root_agent":
                        flow_steps.append({"step": f"{label}エージェント", "done": True})
                        yield {"agent_type": event.author, "confidence": 0.9, "status": f"{label}モード"}

                # テキスト応答を取得
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text and event.is_final_response():
                            final_text_parts.append(part.text)
                            yield part.text

                        # function_callの実行をトラッキング
                        if hasattr(part, "function_call") and part.function_call:
                            fc_name = part.function_call.name
                            if fc_name == "query_bigquery":
                                flow_steps.append({"step": "データ取得", "done": True, "detail": "BigQueryからデータ取得"})
                                yield {"status": "データを取得しています..."}
                            elif fc_name == "search_past_qa":
                                # 過去事例検索のステップを更新
                                for step in flow_steps:
                                    if step["step"] == "過去事例検索":
                                        step["detail"] = "検索実行中"

        except Exception as e:
            logger.error("[ADK] Runner error: %s", e)
            yield f"エラーが発生しました: {str(e)}"

        # 回答生成完了
        flow_steps.append({"step": "回答生成", "done": True})
        yield {"flow_steps": list(flow_steps)}

        # Q&A自動保存（Vertex AI Search）
        full_text = "".join(final_text_parts)
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
                model=APP.gemini_model,
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
