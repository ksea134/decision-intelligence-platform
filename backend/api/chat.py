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

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config.app_config import APP, PATHS
from config.cloud_config import CloudConfig
from domain.models import CloudDataResult
from backend.ops.request_logger import log_request
from backend.ops.metrics import record_response_time, record_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


# ============================================================
# ヘルパー関数（event_generatorから抽出）
# ============================================================

def _extract_agent_info(trace, out_data: dict, is_smart_card: bool) -> None:
    """flow_stepsからエージェント情報をtraceに記録する。"""
    if trace.selected_agent:
        return  # runner.pyで設定済み

    agent_type = out_data.get("agent_type", "general")
    flow_steps = out_data.get("flow_steps", [])
    for fs in flow_steps:
        if "エージェント" in fs.get("step", "") and fs.get("detail"):
            trace.set_agent(
                selected_agent=agent_type,
                agent_model=fs["detail"],
                router_model=out_data.get("router_model", ""),
            )
            return

    # ADKエンジンでagentが未設定の場合はデフォルト設定
    if not is_smart_card:
        from config.app_config import MODELS as _M
        trace.set_agent(
            selected_agent="汎用回答エージェント",
            agent_model=_M.fast,
            router_model=_M.router,
        )


def _clean_full_text(full_text: str) -> str:
    """tool_codeブロックおよびADKのprint(query_bigquery(...))パターンを除去する。"""
    if "tool_code" in full_text:
        full_text = re.sub(r"```tool_code.*?```", "", full_text, flags=re.DOTALL)
        full_text = re.sub(r"(?m)^tool_code\s*\n(?:print\(.*?\)\n?)*", "", full_text)
    # ADKのprint(query_bigquery(sql=...))パターン
    full_text = re.sub(r"print\(query_bigquery\(sql=.*?\)\)", "", full_text, flags=re.DOTALL)
    # SELECT文の断片（行頭のAS, FROM, WHERE, GROUP BY等）
    full_text = re.sub(r"(?m)^(?:AS|FROM|WHERE|GROUP BY|ORDER BY|SELECT|SUM\(|LIMIT)\b[^\n]*\n?", "", full_text)
    return full_text.strip()


def _build_segments(parsed, full_text: str, question: str) -> list:
    """InlineViz + Mermaidセグメントを構築する。"""
    from domain.viz_parser import parse_viz_segments
    from domain.step_to_mermaid import maybe_generate_mermaid_segments, inject_all_mermaids_into_segments, detect_steps

    # 全角波括弧を補正してvizパース
    viz_text = parsed.display_text.replace("｛", "{").replace("｝", "}")
    segments = parse_viz_segments(viz_text)

    # Mermaidフローチャート自動生成（C08: コード側で変換）
    _detect_text = parsed.display_text
    if len(detect_steps(parsed.display_text)) < 3 and len(detect_steps(full_text)) >= 3:
        _detect_text = full_text
        logger.info("[Mermaid] display_textにステップ不足、full_textから検出")
    mermaid_segs = maybe_generate_mermaid_segments(question or "", _detect_text)
    if mermaid_segs:
        segments = inject_all_mermaids_into_segments(segments, mermaid_segs)

    return segments


def _extract_sql_info(out_data: dict) -> tuple[str, int]:
    """SQL実行情報を抽出する。"""
    sql_query = out_data.get("executed_sql") or ""
    sql_row_count = 0
    if out_data.get("sql_result"):
        try:
            sr = out_data["sql_result"]
            sql_row_count = sr.row_count if hasattr(sr, "row_count") else sr.get("row_count", 0)
        except Exception:
            pass
    return sql_query, sql_row_count


def _save_to_memory(memory, prompt: str, parsed, out_data: dict, is_smart_card: bool, smart_card_id: str = "") -> None:
    """会話履歴をSessionMemoryに保存する。"""
    display = smart_card_id if is_smart_card else prompt
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


def _save_to_search(engine_info: dict, prompt: str, parsed, company: str, agent_type: str) -> None:
    """Vertex AI SearchにQ&Aを保存する。"""
    try:
        search_client = engine_info.get("search_client")
        if search_client and search_client.is_ready() and parsed.display_text:
            search_client.store(
                question=prompt,
                answer=parsed.display_text[:2000],
                company=company,
                intent=agent_type,
            )
    except Exception:
        pass


def _finalize_trace(trace, parsed, segments: list, question: str = "") -> None:
    """トレースにレスポンス情報+品質スコアを記録して出力する。"""
    trace.response_length = len(parsed.display_text)
    trace.sources_referenced = parsed.files
    chart_types = [s.get("chart_type", "") for s in segments if s.get("type") == "viz"]
    trace.charts = [c for c in chart_types if c]

    # 品質評価（C09: 全リクエストで評価）
    try:
        from backend.ops.quality_evaluator import evaluate_response
        from config.app_config import MODELS as _M
        # V1エンジンはagent_modelが空なのでMODELS.fastを使用
        model_id = trace.agent_model or _M.fast
        trace.quality_scores = evaluate_response(
            question=question,
            answer=parsed.display_text,
            sources=parsed.files,
            model_id=model_id,
        )
    except Exception as e:
        logger.warning("[QualityEval] Failed: %s", e)
        trace.quality_scores = {"overall_score": -1}

    trace.emit()

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
    trace: Any = None,
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
        from orchestration.llm_client import _get_gemini_client
        client = _get_gemini_client()

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
            trace=trace,
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
async def chat(request: ChatRequest, raw_request: Request = None) -> EventSourceResponse:
    """質問を受け取り、SSEで回答をストリーミング返却する。"""
    # IAPヘッダーからユーザーを取得（ローカルでは"local-dev"）
    _user_email = ""
    if raw_request:
        iap_email = raw_request.headers.get("X-Goog-Authenticated-User-Email", "")
        _user_email = iap_email.split(":")[-1] if ":" in iap_email else (iap_email or "local-dev")

    async def event_generator() -> AsyncGenerator[dict, None]:
        start_ts = time.time()
        from backend.ops.request_trace import RequestTrace
        trace = RequestTrace(
            question=request.question or request.smart_card_id or "",
            company=request.company_display_name,
            user=_user_email,
            source=request.source,
        )

        try:
            # --- データ読み込み ---
            trace.begin_step("data_load")
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
            trace.end_step(f"BQ: {len(data_ctx.bq_result.content) if data_ctx.bq_result else 0} chars, GCS: {len(data_ctx.gcs_result.content) if data_ctx.gcs_result else 0} chars")
            trace.engine = "v1" if is_smart_card else "adk"

            # ── B4: 共有SessionMemory ──
            memory = _get_memory(request.company_display_name)

            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            _executor.submit(
                _run_engine, prompt, request.company_display_name,
                cfg, filtered_ctx, is_smart_card, memory, queue, loop, trace,
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

            # --- エージェント情報抽出 ---
            _extract_agent_info(trace, out_data, is_smart_card)

            # --- 全文結合 + パース ---
            full_text = _clean_full_text("".join(chunks))
            if not full_text:
                yield {"event": "error", "data": json.dumps({"message": "AIからの応答が空でした"})}
                return

            from domain.response_parser import parse_llm_response
            parsed = parse_llm_response(full_text)

            # --- セグメント構築（InlineViz + Mermaid） ---
            segments = _build_segments(parsed, full_text, request.question or "")

            # --- SSE done イベント送信 ---
            sql_query, sql_row_count = _extract_sql_info(out_data)
            if not sql_query:
                sql_query = parsed.sql or ""
            elapsed = round(time.time() - start_ts, 1)
            yield {
                "event": "done",
                "data": json.dumps({
                    "elapsed_seconds": elapsed,
                    "display_text": parsed.display_text,
                    "segments": segments,
                    "sql_query": sql_query,
                    "sql_row_count": sql_row_count,
                }),
            }

            # --- 後処理（メモリ・検索・ログ・トレース） ---
            _save_to_memory(memory, prompt, parsed, out_data, is_smart_card, request.smart_card_id or "")
            _save_to_search(engine_info, prompt, parsed, request.company_display_name, out_data.get("agent_type", "general"))

            engine_type = "v1" if is_smart_card else "adk"
            log_request(
                question=request.question or request.smart_card_id or "",
                company=request.company_display_name,
                source=request.source,
                engine=engine_type,
                elapsed_seconds=elapsed,
                response_length=len(parsed.display_text),
                files_count=len(parsed.files),
                user=_user_email,
            )
            record_response_time(elapsed, engine_type, request.company_display_name)
            _finalize_trace(trace, parsed, segments, question=request.question or "")

        except Exception as e:
            logger.error("[ERROR] /api/chat: %s", e, exc_info=True)
            # メトリクス記録（エラー）
            record_error("unknown", request.company_display_name, type(e).__name__)
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
                user=_user_email,
            )
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

            # エラー時の構造化トレース（C09）
            trace.record_error("pipeline", e)
            trace.emit()

    return EventSourceResponse(event_generator())
