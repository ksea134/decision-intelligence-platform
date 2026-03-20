"""
backend/api/chat.py — チャットエンドポイント（SSEストリーミング）

Streamlit版 ui/components/chat.py の以下の機能をFastAPI+SSEで再現する:
- ハイブリッドエンジン: スマートカード→V1、チャット→ADK
- データソースフィルタリング（_filter_data_ctx相当）
- 会話履歴のGemini渡し（SessionMemory永続化）
- Vertex AI Search Q&A自動保存
- tool_codeフィルタ、出典情報、InlineViz
- エラーバナー（chat_disabled）
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config.app_config import APP, PATHS
from config.cloud_config import CloudConfig
from domain.models import CloudDataResult
from backend.ops.request_logger import log_request

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

_executor = ThreadPoolExecutor(max_workers=4)

# ── B4: セッション永続化（企業名→SessionMemory） ──
# Streamlit版の st.session_state["memory"] に相当
_memory_store: dict[str, Any] = {}


def _get_memory(company: str) -> Any:
    """企業ごとのSessionMemoryを取得（なければ作成）。"""
    from orchestration.memory.session_memory import SessionMemory
    if company not in _memory_store:
        _memory_store[company] = SessionMemory()
        _memory_store[company].switch_company(company)
    return _memory_store[company]


# ── B1: データソースフィルタリング（Streamlit版 _filter_data_ctx 移植） ──

def _filter_data_ctx(data_ctx: Any, data_source: str) -> Any:
    """
    data_sourceの指定に従ってdata_ctxをフィルタしたコピーを返す。
    Streamlit版 chat.py 388-450行の完全移植。
    """
    if not data_source or data_source == "all":
        return data_ctx

    from orchestration.agents.data_agent import DataContext as DC

    bq_result = data_ctx.bq_result
    gcs_result = data_ctx.gcs_result
    assets = data_ctx.assets

    empty_cloud = CloudDataResult(content="", is_connected=False)

    if data_source == "bq":
        gcs_result = empty_cloud
    elif data_source == "gcs":
        bq_result = empty_cloud
    elif data_source == "bq+gcs":
        pass
    elif data_source.startswith("gcs:"):
        keyword = data_source[4:].strip()
        if keyword and gcs_result.content:
            blocks = re.split(r'(?=\[GCS: )', gcs_result.content)
            filtered = [b for b in blocks if keyword in b]
            gcs_result = CloudDataResult(
                content="".join(filtered),
                is_connected=gcs_result.is_connected,
            )
        bq_result = empty_cloud
    elif data_source.startswith("bq:"):
        keyword = data_source[3:].strip()
        if keyword and bq_result.content:
            blocks = re.split(r'(?=Dataset:)', bq_result.content)
            filtered = [b for b in blocks if keyword in b]
            bq_result = CloudDataResult(
                content="".join(filtered),
                is_connected=bq_result.is_connected,
            )
        gcs_result = empty_cloud
    elif data_source == "structured":
        gcs_result = empty_cloud
    elif data_source == "unstructured":
        bq_result = empty_cloud

    return DC(
        assets=assets,
        bq_result=bq_result,
        gcs_result=gcs_result,
        chat_disabled=data_ctx.chat_disabled,
    )


class ChatRequest(BaseModel):
    """チャットリクエストのスキーマ。"""
    question: str
    company_display_name: str
    company_folder_name: str
    source: str = "chat"  # "chat" or "smart_card"
    smart_card_id: str | None = None
    data_source: str = "all"  # B1: スマートカードのデータソース指定
    project_id: str = ""
    gcs_bucket: str = ""


def _run_engine(
    prompt: str,
    company: str,
    cfg: CloudConfig,
    data_ctx: Any,
    is_smart_card: bool,
    memory: Any,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """同期エンジンをスレッドで実行し、結果をasyncio.Queueに送信する。"""
    try:
        from google import genai
        from orchestration.reasoning_engine import ReasoningEngine
        try:
            from infra.vertex_ai_search import create_search_client
            search_client = create_search_client(cfg.project_id)
        except Exception:
            search_client = None

        from orchestration.agents.data_agent import DataAgent
        agent = DataAgent(cfg)
        client = genai.Client()

        # B4: 共有メモリを使用（会話履歴引き継ぎ）
        engine_v1 = ReasoningEngine(
            client=client, data_agent=agent, memory=memory, search_client=search_client,
        )

        engine = engine_v1
        if not is_smart_card:
            try:
                from orchestration.adk.runner import ADKReasoningEngine
                engine = ADKReasoningEngine(
                    client=client, data_agent=agent, memory=memory, search_client=search_client,
                )
            except ImportError:
                pass

        selected_engine = engine_v1 if is_smart_card else engine

        stream = selected_engine.stream_events(
            user_prompt=prompt,
            company=company,
            cfg=cfg,
            data_ctx=data_ctx,
        )

        for token in stream:
            loop.call_soon_threadsafe(queue.put_nowait, ("token", token))

        # B3: Vertex AI Search Q&A自動保存用にengineとsearch_clientを返す
        loop.call_soon_threadsafe(queue.put_nowait, ("done", {
            "engine": selected_engine,
            "search_client": search_client,
        }))

    except Exception as e:
        logger.error("[ENGINE] Error: %s", e, exc_info=True)
        loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))


@router.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    """質問を受け取り、SSEで回答をストリーミング返却する。"""

    async def event_generator() -> AsyncGenerator[dict, None]:
        start_ts = time.time()

        try:
            # --- データ読み込み ---
            base_dir = os.path.join("data", request.company_folder_name)
            cfg = CloudConfig(
                project_id=request.project_id,
                gcs_bucket=request.gcs_bucket,
                folder_name=request.company_folder_name,
            )

            from infra.file_loader import load_smart_cards
            from orchestration.agents.data_agent import DataAgent

            agent = DataAgent(cfg)
            data_ctx = agent.fetch_all(base_dir)

            # ── B6: chat_disabledチェック ──
            if data_ctx.chat_disabled:
                yield {"event": "error", "data": json.dumps({
                    "message": "データソースが利用できません。GCP接続設定を確認してください。",
                    "type": "chat_disabled",
                })}
                return

            # --- スマートカードの場合、プロンプトを取得 ---
            data_source = "all"
            if request.source == "smart_card" and request.smart_card_id:
                smart_cards_dir = os.path.join(base_dir, PATHS.smart_cards)
                cards = load_smart_cards(smart_cards_dir)
                card = next((c for c in cards if c["id"] == request.smart_card_id), None)
                if not card or not card.get("prompt_template"):
                    yield {"event": "error", "data": json.dumps({"message": f"スマートカード {request.smart_card_id} のプロンプトが未設定です"})}
                    return
                prompt = card["prompt_template"]
                data_source = card.get("data_source", "all")
                is_smart_card = True
            else:
                prompt = request.question
                is_smart_card = False

            # ── B1: データソースフィルタリング（Streamlit版準拠） ──
            filtered_ctx = _filter_data_ctx(data_ctx, data_source) if is_smart_card else data_ctx

            # ── B4: 共有SessionMemory ──
            memory = _get_memory(request.company_display_name)

            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            _executor.submit(
                _run_engine, prompt, request.company_display_name,
                cfg, filtered_ctx, is_smart_card, memory, queue, loop,
            )

            # --- キューからトークンを受信してSSEに変換 ---
            chunks: list[str] = []
            out_data: dict = {}
            engine_info: dict = {}

            while True:
                kind, payload = await queue.get()

                if kind == "token":
                    token = payload
                    if isinstance(token, str):
                        chunks.append(token)
                        yield {"event": "text", "data": json.dumps({"text": token})}
                    elif isinstance(token, dict):
                        if "status" in token:
                            yield {"event": "status", "data": json.dumps({"message": token["status"]})}
                        elif "flow_steps" in token:
                            out_data["flow_steps"] = token["flow_steps"]
                            yield {"event": "flow_steps", "data": json.dumps({"steps": token["flow_steps"]})}
                        elif "bq_tables" in token:
                            out_data["bq_tables"] = token["bq_tables"]
                        elif "agent_type" in token:
                            out_data["agent_type"] = token.get("agent_type", "general")
                            if "status" in token:
                                yield {"event": "status", "data": json.dumps({"message": token["status"]})}
                        else:
                            out_data.update(token)

                elif kind == "done":
                    engine_info = payload or {}
                    break

                elif kind == "error":
                    yield {"event": "error", "data": json.dumps({"message": payload})}
                    return

            # --- 全文結合 + tool_codeフィルタ（フェンス付き・なし両対応） ---
            full_text = "".join(chunks)
            if "tool_code" in full_text:
                full_text = re.sub(r"```tool_code.*?```", "", full_text, flags=re.DOTALL)
                full_text = re.sub(r"(?m)^tool_code\s*\n(?:print\(.*?\)\n?)*", "", full_text)
                full_text = full_text.strip()

            if not full_text:
                yield {"event": "error", "data": json.dumps({"message": "AIからの応答が空でした"})}
                return

            # --- 出典情報 ---
            from domain.response_parser import parse_llm_response
            parsed = parse_llm_response(full_text)

            # BQテーブル名補完
            bq_tables: list[str] = []
            if out_data.get("bq_tables"):
                bq_tables.extend(out_data["bq_tables"])
            _sql = out_data.get("executed_sql") or parsed.sql or ""
            if _sql:
                bq_tables += re.findall(r"FROM\s+`?[\w-]+`?\.`?([\w-]+)`?", _sql, re.IGNORECASE)
                bq_tables += re.findall(r"JOIN\s+`?[\w-]+`?\.`?([\w-]+)`?", _sql, re.IGNORECASE)
            if not bq_tables and filtered_ctx.bq_result and filtered_ctx.bq_result.content:
                schema_tables = re.findall(r"Table:\s*(\S+)", filtered_ctx.bq_result.content)
                bq_tables.extend(schema_tables)

            existing_bq = {f for f in parsed.files if f.startswith("BQ:")}
            for t in dict.fromkeys(bq_tables):
                bq_name = f"BQ:{t}"
                if bq_name not in existing_bq:
                    parsed.files.insert(0, bq_name)

            structured = [f for f in parsed.files if f.startswith("BQ:") or f.startswith("LOCAL:")]
            unstructured = [f for f in parsed.files if f.startswith("GCS:")]

            yield {
                "event": "files",
                "data": json.dumps({"structured": structured, "unstructured": unstructured}),
            }

            # --- InlineVizセグメント分割 ---
            from domain.viz_parser import parse_viz_segments
            segments = parse_viz_segments(parsed.display_text)

            elapsed = round(time.time() - start_ts, 1)
            yield {
                "event": "done",
                "data": json.dumps({
                    "elapsed_seconds": elapsed,
                    "display_text": parsed.display_text,
                    "segments": segments,
                }),
            }

            # ── B4: メッセージをメモリに保存（会話履歴引き継ぎ） ──
            display = f"{request.smart_card_id}" if is_smart_card else request.question
            user_msg = {"role": "user", "content": display, "llm_prompt": prompt}
            asst_msg = {
                "role": "assistant",
                "content": parsed.display_text,
                "files": parsed.files,
                "sql_result": out_data.get("sql_result"),
                "sql_query": out_data.get("executed_sql") or parsed.sql or "",
                "flow_steps": out_data.get("flow_steps", []),
            }
            memory.add_message(user_msg)
            memory.add_message(asst_msg)
            memory.sync()

            # ── B3: Vertex AI Search Q&A自動保存 ──
            try:
                search_client = engine_info.get("search_client")
                if search_client and search_client.is_ready() and parsed.display_text:
                    search_client.store(
                        question=prompt,
                        answer=parsed.display_text[:2000],
                        company=request.company_display_name,
                        intent=out_data.get("agent_type", "general"),
                    )
            except Exception:
                pass  # 保存失敗はチャット動作に影響させない

            # リクエストログ記録
            log_request(
                question=request.question or request.smart_card_id or "",
                company=request.company_display_name,
                source=request.source,
                engine="v1" if is_smart_card else "adk",
                elapsed_seconds=elapsed,
                response_length=len(parsed.display_text),
                files_count=len(parsed.files),
            )

        except Exception as e:
            logger.error("[ERROR] /api/chat: %s", e, exc_info=True)
            log_request(
                question=request.question or request.smart_card_id or "",
                company=request.company_display_name,
                source=request.source,
                engine="unknown",
                elapsed_seconds=round(time.time() - start_ts, 1),
                response_length=0,
                files_count=0,
                status="error",
                error_message=str(e),
            )
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())
