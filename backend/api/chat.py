"""
backend/api/chat.py — チャットエンドポイント（SSEストリーミング）

ユーザーの質問を受け取り、既存のOrchestration層を呼び出して
SSE（Server-Sent Events）で回答をストリーミング返却する。

SSEイベント種別:
  - event: status   → ステータス更新（「回答を生成しています...」等）
  - event: text     → 回答テキストのチャンク
  - event: files    → 出典情報（構造化/非構造化）
  - event: viz      → InlineVizチャートデータ（Phase 5 Step 5で実装）
  - event: done     → ストリーム完了
  - event: error    → エラー

同期エンジン→非同期SSE変換:
  既存のOrchestration層は同期ジェネレータ（yield）で動作する。
  FastAPIの非同期イベントループをブロックしないよう、
  同期ジェネレータをスレッドで実行し、asyncio.Queueで非同期側に橋渡しする。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncGenerator, Generator

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config.app_config import APP, PATHS
from config.cloud_config import CloudConfig

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# エンジン実行用のスレッドプール（同期ジェネレータを非同期に変換）
_executor = ThreadPoolExecutor(max_workers=4)


class ChatRequest(BaseModel):
    """チャットリクエストのスキーマ。"""
    question: str
    company_display_name: str
    company_folder_name: str
    source: str = "chat"  # "chat" or "smart_card"
    smart_card_id: str | None = None
    project_id: str = ""
    gcs_bucket: str = ""


def _run_engine(
    prompt: str,
    company: str,
    cfg: CloudConfig,
    data_ctx: Any,
    is_smart_card: bool,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """同期エンジンをスレッドで実行し、結果をasyncio.Queueに送信する。"""
    try:
        from google import genai
        from orchestration.reasoning_engine import ReasoningEngine
        from orchestration.memory.session_memory import SessionMemory
        try:
            from infra.vertex_ai_search import create_search_client
            search_client = create_search_client(cfg.project_id)
        except Exception:
            search_client = None

        from orchestration.agents.data_agent import DataAgent
        agent = DataAgent(cfg)
        client = genai.Client()
        memory = SessionMemory()
        memory.switch_company(company)

        engine_v1 = ReasoningEngine(
            client=client, data_agent=agent, memory=memory, search_client=search_client,
        )

        # ADKエンジン（チャット入力用）
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

        loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

    except Exception as e:
        logger.error("[ENGINE] Error: %s", e, exc_info=True)
        loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))


@router.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    """質問を受け取り、SSEで回答をストリーミング返却する。"""

    async def event_generator() -> AsyncGenerator[dict, None]:
        start_ts = time.time()

        try:
            yield {"event": "status", "data": json.dumps({"message": "データを読み込んでいます..."})}

            # --- データ読み込み（同期だが軽量なのでメインスレッドで実行） ---
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

            # --- スマートカードの場合、プロンプトを取得 ---
            if request.source == "smart_card" and request.smart_card_id:
                smart_cards_dir = os.path.join(base_dir, PATHS.smart_cards)
                cards = load_smart_cards(smart_cards_dir)
                card = next((c for c in cards if c["id"] == request.smart_card_id), None)
                if not card or not card.get("prompt_template"):
                    yield {"event": "error", "data": json.dumps({"message": f"スマートカード {request.smart_card_id} のプロンプトが未設定です"})}
                    return
                prompt = card["prompt_template"]
                is_smart_card = True
            else:
                prompt = request.question
                is_smart_card = False

            # --- エンジンをスレッドで実行 ---
            yield {"event": "status", "data": json.dumps({"message": "回答を生成しています..."})}

            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            _executor.submit(
                _run_engine, prompt, request.company_display_name,
                cfg, data_ctx, is_smart_card, queue, loop,
            )

            # --- キューからトークンを受信してSSEに変換 ---
            chunks: list[str] = []
            out_data: dict = {}

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
                        elif "bq_tables" in token:
                            out_data["bq_tables"] = token["bq_tables"]
                        else:
                            out_data.update(token)

                elif kind == "done":
                    break

                elif kind == "error":
                    yield {"event": "error", "data": json.dumps({"message": payload})}
                    return

            # --- 全文結合 + tool_codeフィルタ ---
            full_text = "".join(chunks)
            if "tool_code" in full_text:
                full_text = re.sub(r"```tool_code.*?```", "", full_text, flags=re.DOTALL).strip()

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
            if not bq_tables and data_ctx.bq_result and data_ctx.bq_result.content:
                schema_tables = re.findall(r"Table:\s*(\S+)", data_ctx.bq_result.content)
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
                "data": json.dumps({
                    "structured": structured,
                    "unstructured": unstructured,
                }),
            }

            elapsed = round(time.time() - start_ts, 1)
            yield {
                "event": "done",
                "data": json.dumps({
                    "elapsed_seconds": elapsed,
                    "display_text": parsed.display_text,
                }),
            }

            logger.warning("[PERF] /api/chat: %.1f秒, %d文字, 出典%d件",
                           elapsed, len(parsed.display_text), len(parsed.files))

        except Exception as e:
            logger.error("[ERROR] /api/chat: %s", e, exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())
