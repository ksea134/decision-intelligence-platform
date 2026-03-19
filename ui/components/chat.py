"""
ui/components/chat.py — チャット画面コンポーネント

【責務】
- チャット画面の描画・入力処理
- ストリーミング表示（経過秒数付きプログレス）
- 補足フェーズ（思考ロジック・インフォグラフィック・深掘り質問）の2段階実行

【設計原則】
- Streamlit依存はこのファイルに完全に閉じ込める
- ビジネスロジックは orchestration/ に委譲する
- 現行コードの pending_supplement パターンを継承（重複防止の核心）

【現行コードからの主な変更点】
- AIService → ReasoningEngine への差し替え
- ChatState → SessionMemory への差し替え
- ensure_minimum_emphasis_for_display は廃止（prompts/で制御）
- viz_data / SupplementBundle は削除済み

【修正履歴】
- 2026-03-16: 空プロンプト問題の修正（Gemini API 400エラー対策）
- 2026-03-16: Phase 1 Agent Router 統合（ReasoningEngineV2）
- 2026-03-16: ver.2.2.2 ストリーミング表示対応（回答の逐次表示 + Agent状態可視化）
"""

from __future__ import annotations

import base64
import logging
import time
import re
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue
from typing import Any, Generator, Union

import streamlit as st
import streamlit.components.v1 as components

from config.app_config import APP
from config.cloud_config import CloudConfig
from domain.models import SQLResult
from domain.response_parser import parse_llm_response
from orchestration.agents.data_agent import DataAgent, DataContext
from orchestration.memory.session_memory import SessionMemory
from orchestration.reasoning_engine import ReasoningEngine
from orchestration.reasoning_engine_v2 import ReasoningEngineV2
from google import genai

logger = logging.getLogger(__name__)

# ============================================================
# バージョン情報
# ============================================================
__version__ = "3.6.1"

# ============================================================
# Phase 1: Agent Router 設定
# ============================================================
# エンジン選択フラグ
# USE_ADK_ENGINE = True: ADKベースのエージェント（Phase 4A）
# USE_AGENT_ROUTER = True: V1 + Router分類（現行安定版）
# 両方False: V1のみ（Router分類なし）
USE_ADK_ENGINE = True
USE_AGENT_ROUTER = True


# ============================================================
# CSS定数（UIレイヤー専用）
# ============================================================
_APP_CSS = """
<style>
.stMarkdown p { line-height:1.7!important; font-size:1.05rem!important; }
.stMarkdown strong, .stMarkdown b { color:#D2FF00!important; }
.stMarkdown h3 { margin-top:1.5rem!important; margin-bottom:0.5rem!important; }
.stMarkdown h4 { margin-top:1rem!important; margin-bottom:0.3rem!important; }
div[data-testid="stChatMessage"] div[data-testid="stButton"] > button {
  height:auto!important; min-height:2.5rem!important; white-space:normal!important;
  font-size:0.9rem!important; font-weight:400!important; text-align:left!important;
  padding-left:12px!important; line-height:1.4!important; padding-top:8px!important; padding-bottom:8px!important;
}
div[data-testid="stChatMessage"] div[data-testid="stButton"] > button:hover {
  border-color:#ff4b4b!important; color:#ff4b4b!important;
  background-color:rgba(255,75,75,0.08)!important;
}
div[data-testid="stExpander"] div[data-testid="stVerticalBlock"]
div[data-testid="stButton"] button {
  text-align:left!important; justify-content:flex-start!important;
  white-space:normal!important; height:auto!important; min-height:2.5rem!important;
}
/* チャット入力欄の送信ボタンアイコンを右向きに */
button[data-testid="stChatInputSubmitButton"] svg {
  transform: rotate(90deg)!important;
}
@keyframes spin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
/* 右側パネル: Expanderダークテーマ */
div[data-testid="stExpander"] details {
  background-color: #111827 !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 8px !important;
}
div[data-testid="stExpander"] details summary {
  background-color: #1f2937 !important;
  color: #f3f4f6 !important;
  border-radius: 8px !important;
}
div[data-testid="stExpander"] details[open] summary {
  border-bottom: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 8px 8px 0 0 !important;
}
div[data-testid="stExpander"] details div[data-testid="stExpanderDetails"] {
  background-color: #111827 !important;
  color: #e5e7eb !important;
}
/* スマートカード用CSS */
[data-testid="stForm"] {border:none !important;padding:0 !important;margin:0 !important;}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] {margin-top:-16px !important;}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
  font-size:0.75rem !important;
  padding:6px 12px !important;
  border:1px solid rgba(255,255,255,0.1) !important;
  border-top:none !important;
  border-radius:0 0 12px 12px !important;
  background:linear-gradient(135deg, #1a1a2e, #16213e) !important;
  color:#8c98a9 !important;
  transition:all 0.2s !important;
}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
  border-color:#D41F3C !important;
  color:#D41F3C !important;
  background:linear-gradient(135deg, #2a1a2e, #26213e) !important;
}
/* サイドバーフッター用CSS */
[data-testid="stSidebarUserContent"] { padding-bottom:80px!important; }
.sidebar-footer {
  position:fixed; bottom:24px; left:24px; display:flex; flex-direction:row; align-items:center; gap:8px;
  color:#8c98a9!important; font-size:14px!important; font-weight:600!important;
  font-family:'Helvetica Neue',Helvetica,Arial,sans-serif!important; letter-spacing:0.5px; z-index:999999; pointer-events:none;
}
.sidebar-footer img { height:18px!important; object-fit:contain; }
</style>
"""

_BTN_CSS = """
body{margin:0;padding:0;font-family:"Source Sans Pro",sans-serif;
display:flex;align-items:center;background-color:#0e1117;}
button{display:inline-flex;align-items:center;justify-content:center;
font-weight:400;padding:0.25rem 0.75rem;border-radius:0.5rem;min-height:2.5rem;
margin:0;line-height:1.6;width:100%;background-color:transparent;
border:1px solid rgba(250,250,250,0.2);color:rgba(250,250,250,0.8);
cursor:pointer;font-size:1rem;transition:border-color 0.2s,color 0.2s;box-sizing:border-box;}
button:hover{border-color:#ff4b4b;color:#ff4b4b;background-color:rgba(255,75,75,0.08);}
button:active{background-color:#ff4b4b;color:white;border-color:#ff4b4b;}
"""

_ACCENT = "#D2FF00"
_BLUE   = "#38bdf8"
_GREEN  = "#22c55e"
_RED    = "#ff4b4b"


# ============================================================
# 型エイリアス
# ============================================================
EngineType = Union[ReasoningEngine, ReasoningEngineV2]


# ============================================================
# 初期化ヘルパー
# ============================================================

def _read_binary_as_base64(path: str) -> str:
    """画像ファイルをBase64エンコードして返す（ベースプログラムから移植）"""
    from pathlib import Path
    try:
        return base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return ""


def _get_client() -> genai.Client:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        st.error("GEMINI_API_KEY が Streamlit Secrets に設定されていません。")
        st.stop()
    return genai.Client(api_key=api_key, http_options={"timeout": 300_000})


def _get_memory() -> SessionMemory:
    if st.session_state.get("memory") is None:
        st.session_state["memory"] = SessionMemory()
    memory = st.session_state["memory"]
    # 壊れたメッセージ（content=None, role=None）を自動クリーンアップ
    for company, msgs in memory._company_messages.items():
        memory._company_messages[company] = [
            m for m in msgs
            if m.get("role") and m.get("content") is not None
        ]
    memory._messages = [
        m for m in memory._messages
        if m.get("role") and m.get("content") is not None
    ]
    return memory


# ============================================================
# メインエントリーポイント
# ============================================================

def render_chat(selected_company: str, cfg: CloudConfig, base_dir: str) -> None:
    """チャット画面全体を描画する。"""
    st.markdown(_APP_CSS, unsafe_allow_html=True)

    # サイドバーフッター（ロゴ + バージョン）
    logo_b64 = _read_binary_as_base64("image/Kyndryl_logo.png")
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="Kyndryl" style="height:18px;">' if logo_b64 else "<b>Kyndryl</b>"
    st.sidebar.markdown(
        f'<div class="sidebar-footer"><span>powered by</span>{logo_html}<span style="margin-left:6px;opacity:0.5;">|</span><span style="margin-left:2px;">{APP.version}</span></div>',
        unsafe_allow_html=True,
    )

    memory = _get_memory()
    if memory.switch_company(selected_company):
        # 企業切り替え時のみ pending 系をクリア
        st.session_state.pop("pending_prompt", None)
        st.session_state.pop("pending_display", None)
        st.session_state.pop("pending_supplement", None)
        st.rerun()

    client  = _get_client()
    agent   = DataAgent(cfg)
    with st.spinner("データを準備しています…"):
        data_ctx = agent.fetch_all(base_dir)

    # ============================================================
    # エンジン選択
    # ============================================================
    from infra.vertex_ai_search import create_search_client
    search_client = create_search_client(project_id=cfg.project_id)

    if USE_ADK_ENGINE:
        try:
            from orchestration.adk.runner import ADKReasoningEngine
            engine: EngineType = ADKReasoningEngine(client=client, data_agent=agent, memory=memory, search_client=search_client)
        except ImportError:
            logger.warning("google-adk not installed — falling back to ReasoningEngine")
            engine = ReasoningEngine(client=client, data_agent=agent, memory=memory, search_client=search_client)
    elif USE_AGENT_ROUTER:
        from orchestration.agents.router_agent import RouterAgent
        router = RouterAgent(client=client)
        engine = ReasoningEngine(client=client, data_agent=agent, memory=memory, router_agent=router, search_client=search_client)
    else:
        engine = ReasoningEngine(client=client, data_agent=agent, memory=memory, search_client=search_client)

    # タイトル行
    title_col, btn_col = st.columns([10, 1.2])
    with title_col:
        st.markdown(
            "<div style='margin-bottom:-12px;background-color:transparent;'>"
            "<span style='font-size:1.1rem;color:rgba(255,255,255,0.45);font-weight:400;letter-spacing:0.05em;'>"
            "DIP | Decision Intelligence Platform</span></div>",
            unsafe_allow_html=True,
        )
        st.title(APP.title + " | " + selected_company)
    with btn_col:
        st.markdown("<div style='margin-top:38px'></div>", unsafe_allow_html=True)
        if st.button("新規チャット", key="new_chat_btn", use_container_width=True, type="secondary"):
            memory.reset_chat()
            st.rerun()

    _render_error_banner(data_ctx)

    if data_ctx.chat_disabled:
        st.error("データソースが利用できません。設定を確認してください。")
        col_r = st.columns([1.3, 0.7], gap="large")[1]
        with col_r:
            _render_right_column(selected_company, data_ctx, memory)
        st.stop()

    col_chat, col_monitor = st.columns([1.3, 0.7], gap="large")
    with col_monitor:
        _render_right_column(selected_company, data_ctx, memory)
    with col_chat:
        _render_left_column(
            memory=memory, engine=engine,
            data_ctx=data_ctx, selected_company=selected_company,
        )


# ============================================================
# 左カラム（チャット）
# ============================================================

def _render_left_column(
    memory: SessionMemory,
    engine: EngineType,
    data_ctx: DataContext,
    selected_company: str,
) -> None:
    # メッセージが0件のときスマートカードを表示
    if not memory.get_messages():
        _render_smart_cards(data_ctx.assets.smart_cards)

    # メッセージ履歴の描画
    for index, msg in enumerate(memory.get_messages()):
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(msg.get("content", ""))
            else:
                _render_assistant_message(index, msg, data_ctx, selected_company)

    # 補足フェーズのステータス表示用プレースホルダー（最新回答の直後に配置）
    supplement_status_placeholder = st.empty()

    # pending_prompt の処理（メッセージ履歴の後に描画することで正しい順序を維持）
    if "pending_prompt" in st.session_state:
        pending_prompt  = st.session_state.pop("pending_prompt")
        pending_display = st.session_state.pop("pending_display", None)

        if pending_prompt and str(pending_prompt).strip():
            display_text = pending_display if pending_display and str(pending_display).strip() else pending_prompt
            with st.chat_message("user"):
                st.markdown(display_text)
            is_smart_card = pending_display is not None
            _execute_main_phase(
                prompt=pending_prompt,
                display=display_text,
                memory=memory, engine=engine,
                data_ctx=data_ctx, selected_company=selected_company,
                is_smart_card=is_smart_card,
            )

    # 質問履歴
    history = memory.get_question_history(selected_company)
    if history:
        with st.expander(f"直近の質問一覧（{len(history)}件）", expanded=False):
            for entry in history:
                col_t, col_d = st.columns([11, 1])
                with col_t:
                    if st.button("↩  " + entry["text"], key="qh_" + entry["id"],
                                 use_container_width=True, type="secondary",
                                 help=entry.get("ts", "")):
                        st.session_state["pending_prompt"] = entry["text"]
                        st.rerun()
                with col_d:
                    if st.button("✕", key="qh_del_" + entry["id"],
                                 use_container_width=True, type="secondary"):
                        memory.delete_question_history(selected_company, entry["id"])
                        st.rerun()

    # チャット入力
    placeholder = "本日はどのようなお手伝いをしましょうか。" if not memory.get_messages() else "追加でご質問はございますか。"
    prompt = st.chat_input(placeholder)
    if prompt:
        st.session_state["pending_prompt"] = prompt
        st.rerun()

    # 補足フェーズの実行（メイン回答後の rerun で到達する）
    if st.session_state.get("pending_supplement"):
        _execute_supplement_phase(engine=engine, memory=memory, data_ctx=data_ctx, selected_company=selected_company, status_placeholder=supplement_status_placeholder)

    # 【修正】深掘り質問生成（ボタンクリック時のみ実行）
    if st.session_state.get("pending_deepdive"):
        _execute_deepdive_phase(engine=engine, memory=memory)


# ============================================================
# スマートカード
# ============================================================

_KYNDRYL = "#D41F3C"

def _render_smart_cards(cards: list[dict[str, Any]]) -> None:
    if not cards:
        return

    COLS_PER_ROW = 5
    TILE_HEIGHT = 120  # px — 固定高さ

    # Render rows of 5
    for row_start in range(0, len(cards), COLS_PER_ROW):
        row_cards = cards[row_start : row_start + COLS_PER_ROW]
        cols = st.columns(COLS_PER_ROW, gap="small")
        for i, card in enumerate(row_cards):
            with cols[i]:
                icon = card.get("icon", "")
                title = card.get("title", card["id"])

                with st.form(key=f"sc_form_{card['id']}"):
                    st.markdown(
                        f"""<div style="
                            height:{TILE_HEIGHT - 36}px;display:flex;flex-direction:column;
                            align-items:center;justify-content:center;text-align:center;
                            background:linear-gradient(135deg, #1a1a2e, #16213e);
                            border-radius:12px 12px 0 0;
                            border:1px solid rgba(255,255,255,0.1);
                            border-bottom:none;
                            padding:10px 8px;margin-bottom:0;
                        " onmouseover="this.style.borderColor='{_KYNDRYL}';this.style.background='linear-gradient(135deg, #2a1a2e, #26213e)'"
                          onmouseout="this.style.borderColor='rgba(255,255,255,0.1)';this.style.background='linear-gradient(135deg, #1a1a2e, #16213e)'">
                            <div style="font-size:1.4rem;margin-bottom:4px;">{icon}</div>
                            <div style="font-size:0.85rem;font-weight:700;color:#f3f4f6;line-height:1.2;">{title}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    submitted = st.form_submit_button("AI実行", use_container_width=True)
                    if submitted:
                        prompt_template = card.get("prompt_template", "")
                        if not prompt_template or not str(prompt_template).strip():
                            st.error(
                                f"スマートカード「{title}」のプロンプトが未設定です。\n"
                                f"smart_cards/{card['id']}.md を作成してください。"
                            )
                            return
                        display_label = f"{icon} {title}" if icon else title
                        st.session_state["pending_prompt"] = prompt_template
                        st.session_state["pending_display"] = display_label
                        st.rerun()


# ============================================================
# メインフェーズ（ストリーミング回答生成）ver.2.2.2
# ============================================================

def _execute_main_phase(
    prompt: str,
    display: str,
    memory: SessionMemory,
    engine: EngineType,
    data_ctx: DataContext,
    selected_company: str,
    is_smart_card: bool = False,
) -> None:
    """
    Gemini ストリーミング呼び出しを行い、回答を memory に追加する。
    完了後に pending_supplement をセットして st.rerun() する。
    
    【ver.2.2.2】回答を逐次表示 + Agent状態を可視化
    - ThreadPoolExecutor + Queue で秒数カウントを実現
    - ステータス表示はchat_messageの中に配置
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 空プロンプトの早期検出
    if not prompt or not str(prompt).strip():
        st.error("⚠️ プロンプトが空です。")
        return

    start_ts = time.time()
    out_data: dict[str, Any] = {}

    # ストリーム取得
    try:
        stream = engine.stream_events(
            user_prompt=prompt,
            company=selected_company,
            cfg=engine._data_agent._cfg,
            data_ctx=data_ctx,
        )
    except Exception as exc:
        st.error("ストリーム開始エラー: " + str(exc))
        return

    # ストリーム処理を別スレッドで実行
    stream_queue: Queue = Queue()
    
    def _stream_worker():
        try:
            for token in stream:
                stream_queue.put(("token", token))
            stream_queue.put(("done", None))
        except Exception as e:
            stream_queue.put(("error", e))
    
    # 【ver.2.2.3】最終回答のみ表示: 全処理完了まではスピナーのみ表示
    chunks: list[str] = []
    current_status = "回答を生成しています…"
    has_tool_call = False  # Tool Callが発生したかどうか

    with st.chat_message("assistant"):
        status_container = st.empty()
        response_placeholder = st.empty()

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_stream_worker)

            while True:
                # 毎ループで秒数を更新
                elapsed = int(time.time() - start_ts)
                status_container.markdown(
                    f"""<div style="display:flex;align-items:center;gap:10px;padding:4px 0;
                    color:rgba(255,255,255,0.85);font-size:0.9rem;">
                    <div style="width:14px;height:14px;border-radius:50%;
                    border:2px solid rgba(255,255,255,0.25);border-top-color:#22c55e;border-right-color:#22c55e;
                    animation:spin 0.8s linear infinite;flex-shrink:0;"></div>
                    <span>{current_status} ({elapsed}秒)</span>
                    </div>""",
                    unsafe_allow_html=True,
                )

                try:
                    kind, payload = stream_queue.get(timeout=0.1)  # 100msタイムアウト

                    if kind == "token":
                        token = payload

                        # テキストトークン（文字列）
                        if isinstance(token, str):
                            if has_tool_call:
                                # Tool Call後のテキスト = 最終回答 → 蓄積のみ（表示しない）
                                chunks.append(token)
                            else:
                                # Tool Call前のテキスト → 蓄積のみ（表示しない）
                                chunks.append(token)

                        # dictイベント（旧形式の互換性）
                        elif isinstance(token, dict):
                            if "flow_steps" in token:
                                out_data["flow_steps"] = token["flow_steps"]
                            elif "agent_type" in token:
                                out_data["agent_type"] = token["agent_type"]
                                out_data["agent_confidence"] = token.get("confidence", 0)
                                if "status" in token:
                                    current_status = token["status"]
                            elif "status" in token:
                                current_status = token["status"]
                                if "ツールを実行" in token["status"] or "BQ実行中" in token["status"]:
                                    has_tool_call = True
                                    chunks.clear()
                            else:
                                out_data.update(token)

                        # StreamEvent オブジェクト（Agent Router対応）
                        elif hasattr(token, 'kind'):
                            if token.kind == "text":
                                chunks.append(token)
                            elif token.kind == "status":
                                current_status = token.status
                            elif token.kind == "agent_selected":
                                current_status = token.status
                            elif token.kind == "sql":
                                out_data["executed_sql"] = token.executed_sql
                                out_data["sql_result"] = token.sql_result
                                row_count = token.sql_result.row_count if token.sql_result else 0
                                current_status = f"BigQuery: {row_count}件取得"

                    elif kind == "done":
                        break

                    elif kind == "error":
                        raise payload

                except Empty:
                    pass  # タイムアウト → 次のループで秒数更新

        # 全処理完了後に一括表示
        if chunks:
            response_placeholder.markdown("".join(chunks))
    
    # ステータスをクリア
    status_container.empty()
    
    logger.info("[PERF] メイン回答生成: %.2f秒", time.time() - start_ts)

    full_text = "".join(chunks)
    if not full_text and not out_data:
        st.warning("AIからの応答が空でした。もう一度お試しください。")
        return

    parsed = parse_llm_response(full_text)

    safe_display = display if display and str(display).strip() else prompt
    user_msg: dict = {"role": "user", "content": safe_display, "llm_prompt": prompt}
    asst_msg: dict = {
        "role": "assistant",
        "content": parsed.display_text,
        "files": parsed.files,
        "thought_process": "",
        "sql_result": out_data.get("sql_result"),
        "sql_query": out_data.get("executed_sql") or parsed.sql or "",
        "artifacts": {},
        "flow_steps": out_data.get("flow_steps", []),
    }

    memory.add_message(user_msg)
    memory.add_message(asst_msg)
    # 【修正】スマートカード経由の場合は履歴に追加しない（ベースプログラムと同じ）
    if not is_smart_card:
        memory.add_question_history(selected_company, display)
    memory.sync()

    # Vertex AI Search にQ&Aを自動保存（バックグラウンド、失敗しても無視）
    try:
        if engine._search_client and engine._search_client.is_ready() and parsed.display_text:
            engine._search_client.store(
                question=prompt,
                answer=parsed.display_text[:2000],
                company=selected_company,
                intent=out_data.get("agent_type", "general"),
            )
    except Exception:
        pass  # 保存失敗はチャット動作に影響させない

    assistant_index = len(memory.get_messages()) - 1
    st.session_state["pending_supplement"] = {
        "assistant_index": assistant_index,
        "user_prompt": prompt,
        "display_text": parsed.display_text,
    }
    st.rerun()


# ============================================================
# 旧バージョンのストリーム処理（補足フェーズ用に残す）
# ============================================================

def _collect_stream_chunks(stream: Any, out_data: dict, queue: Queue) -> list[str]:
    """ストリームを消費し、テキストチャンクを収集する"""
    chunks: list[str] = []
    for token in stream:
        if isinstance(token, str):
            chunks.append(token)
        elif isinstance(token, dict):
            if "status" in token:
                queue.put(("phase", token["status"]))
            else:
                # SQL結果などを受け取るタイミングでchunksをクリア（2重出力防止）
                chunks.clear()
                out_data.update(token)
        # Phase 1: StreamEvent オブジェクト対応
        elif hasattr(token, 'kind'):
            if token.kind == "text":
                chunks.append(token.text)
            elif token.kind == "status":
                queue.put(("phase", token.status))
            elif token.kind == "agent_selected":
                queue.put(("phase", token.status))
            elif token.kind == "sql":
                out_data["executed_sql"] = token.executed_sql
                out_data["sql_result"] = token.sql_result
    return chunks


def _run_stream_with_progress(status_box: Any, label: str, start_ts: float, stream: Any, out_data: dict) -> list[str]:
    """
    ストリーム専用の進捗表示付き実行。
    _collect_stream_chunks に queue を明示的に渡す。
    """
    def elapsed_sec() -> int:
        return max(0, int(time.time() - start_ts))

    queue: Queue = Queue()

    def _worker():
        queue.put(("phase", label))
        try:
            result = _collect_stream_chunks(stream, out_data, queue)
            queue.put(("result", result))
        except Exception as exc:
            queue.put(("error", exc))

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_worker)
        while True:
            try:
                kind, payload = queue.get(timeout=0.2)
                if kind == "phase":
                    _render_progress(status_box, payload, start_ts)
                elif kind == "result":
                    return payload
                elif kind == "error":
                    raise payload
            except Empty:
                if future.done():
                    try:
                        kind, payload = queue.get_nowait()
                        if kind == "result":
                            return payload
                        elif kind == "error":
                            raise payload
                    except Empty:
                        exc = future.exception()
                        if exc:
                            raise exc
                        raise RuntimeError("ワーカーが結果を返さずに終了しました")
                _render_progress(status_box, label, start_ts)


def _run_with_progress(status_box: Any, label: str, start_ts: float, fn, *args, **kwargs):
    """通常の関数用の進捗表示付き実行（補足フェーズ用）"""
    def elapsed_sec() -> int:
        return max(0, int(time.time() - start_ts))

    result_holder: list = []
    error_holder: list = []

    def _worker():
        try:
            result_holder.append(fn(*args, **kwargs))
        except Exception as exc:
            error_holder.append(exc)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_worker)
        while not future.done():
            _render_progress(status_box, label, start_ts)
            time.sleep(0.2)

    if error_holder:
        raise error_holder[0]
    if result_holder:
        return result_holder[0]
    return None


def _render_progress(container: Any, label: str, start_ts: float) -> None:
    elapsed = max(0, int(time.time() - start_ts))
    container.markdown(
        f"""<div style="display:flex;align-items:center;gap:12px;padding:8px 0 12px 0;
        color:rgba(255,255,255,0.95);font-size:1rem;font-weight:600;">
        <div style="width:14px;height:14px;border-radius:50%;
        border:2px solid rgba(255,255,255,0.28);border-top-color:#fff;border-right-color:#fff;
        animation:spin 0.9s linear infinite;flex:0 0 auto;"></div>
        <div>{label}（{elapsed}秒）</div></div>""",
        unsafe_allow_html=True,
    )


# ============================================================
# 補足フェーズ（思考ロジック・インフォグラフィック）
# ============================================================

def _execute_supplement_phase(
    engine: EngineType,
    memory: SessionMemory,
    data_ctx: DataContext,
    selected_company: str,
    status_placeholder: Any = None,
) -> None:
    """
    pending_supplement が存在するときのみ実行される。
    メイン回答後の rerun で到達するため、描画の重複が発生しない。
    
    【修正】深掘り質問（generate_deep_dive）は初回には実行しない。
    ボタンクリック時（generating_dd フラグ）にのみ実行する。
    """
    import logging
    logger = logging.getLogger(__name__)
    
    pending = st.session_state.get("pending_supplement")
    if not pending:
        return

    assistant_index = pending["assistant_index"]
    user_prompt     = pending["user_prompt"]
    display_text    = pending["display_text"]

    if assistant_index >= len(memory.get_messages()):
        st.session_state.pop("pending_supplement", None)
        return

    status_box = status_placeholder if status_placeholder else st.empty()
    phase_start = time.time()
    timestamp = time.strftime("%Y%m%d-%H%M")

    # 思考ロジックを経過秒数付きで生成
    start_ts = time.time()
    thought = _run_with_progress(
        status_box, "補足情報を整理しています…", start_ts,
        engine.generate_thought_process,
        user_prompt, display_text,
        data_ctx.assets.structured_text,
        data_ctx.assets.unstructured_text,
    )
    logger.info("[PERF] 思考ロジック生成: %.2f秒", time.time() - start_ts)

    # インフォグラフィックを経過秒数付きで生成
    # 【重要】display_text はAIの回答文（parsed.display_text）
    logger.warning("[DEBUG] インフォグラフィック入力テキスト(%d文字): %s", len(display_text), display_text[:200])
    start_ts = time.time()
    info_html, info_data = _run_with_progress(
        status_box, "インフォグラフィックを生成しています…", start_ts,
        engine.generate_infographic,
        display_text,
        timestamp,
        selected_company,
    )
    logger.info("[PERF] インフォグラフィック生成: %.2f秒", time.time() - start_ts)
    logger.info("[PERF] 補足フェーズ合計: %.2f秒", time.time() - phase_start)

    status_box.empty()

    # memory に書き込む
    memory.get_messages()[assistant_index]["thought_process"] = thought
    artifacts = memory.get_artifacts(assistant_index)
    artifacts["info_html"]  = info_html
    artifacts["info_data"]  = info_data
    # 【修正】deepdive は初回にはセットしない
    # artifacts["deepdive"]   = deep_dive
    memory.sync()

    st.session_state.pop("pending_supplement", None)
    st.rerun()


def _execute_deepdive_phase(
    engine: EngineType,
    memory: SessionMemory,
) -> None:
    """
    pending_deepdive が存在するときのみ実行される。
    追加質問ボタンクリック後の rerun で到達する。
    """
    pending = st.session_state.get("pending_deepdive")
    if not pending:
        return

    assistant_index = pending["assistant_index"]

    if assistant_index >= len(memory.get_messages()):
        st.session_state.pop("pending_deepdive", None)
        return

    msg = memory.get_messages()[assistant_index]
    user_prompt = msg.get("llm_prompt", "")
    display_text = msg.get("content", "")

    # 直前のユーザーメッセージを取得
    if assistant_index > 0:
        user_msg = memory.get_messages()[assistant_index - 1]
        if user_msg.get("role") == "user":
            user_prompt = user_msg.get("llm_prompt") or user_msg.get("content", "")

    status_box = st.empty()
    start_ts   = time.time()

    # 深掘り質問を経過秒数付きで生成
    deep_dive = _run_with_progress(
        status_box, "追加質問を生成しています…", start_ts,
        engine.generate_deep_dive,
        user_prompt, display_text,
    )

    status_box.empty()

    # memory に書き込む
    artifacts = memory.get_artifacts(assistant_index)
    artifacts["deepdive"] = deep_dive
    memory.sync()

    st.session_state.pop("pending_deepdive", None)
    st.rerun()


def _run_with_progress(
    status_box: Any,
    label: str,
    start_ts: float,
    fn: Any,
    *args: Any,
) -> Any:
    """fn を別スレッドで実行しながら経過秒数を表示する。"""
    q: Queue = Queue()

    def _worker() -> None:
        q.put(("phase", label))
        try:
            q.put(("result", fn(*args)))
        except Exception as exc:
            q.put(("error", exc))

    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(_worker)
        while True:
            try:
                kind, payload = q.get(timeout=0.2)
                if kind == "phase":
                    _render_progress(status_box, payload, start_ts)
                elif kind == "result":
                    return payload
                elif kind == "error":
                    raise payload
            except Empty:
                if future.done():
                    try:
                        kind, payload = q.get_nowait()
                        if kind == "result":
                            return payload
                        elif kind == "error":
                            raise payload
                    except Empty:
                        exc = future.exception()
                        if exc:
                            raise exc
                        raise RuntimeError("ワーカーが結果を返さずに終了しました")
                _render_progress(status_box, label, start_ts)


# ============================================================
# アシスタントメッセージ描画
# ============================================================

def _render_assistant_message(
    index: int,
    message: dict[str, Any],
    data_ctx: DataContext,
    selected_company: str,
) -> None:
    try:
        # 本文（sanitize のみ適用。事後改変はしない）
        content = _sanitize_markdown(message.get("content", ""))
        st.markdown(content)

        # データソースバッジ + 引用
        sql_result = SQLResult(**message["sql_result"]) if message.get("sql_result") else None
        _render_badges(message.get("files", []), sql_result, data_ctx)

        # BQ チャート
        if sql_result:
            _render_sql_chart(sql_result)

        # BQ 実行ログ
        _render_sql_log(message)

        # インフォグラフィック
        _render_infographic(index)

        # アクションボタン（コピー・テキストDL・PDF・深掘り）
        _render_action_buttons(index, message, selected_company)

    except Exception as exc:
        st.error("表示エラー: " + str(exc))
        try:
            st.markdown(message.get("content", "（表示できません）"))
        except Exception:
            pass


def _sanitize_markdown(text: str) -> str:
    """Markdownを表示用に正規化する。LLM出力の事後改変は行わない。"""
    if not text:
        return text
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    # $記号のエスケープ（数式誤認識防止）
    t = re.sub(r'\$(?=[a-zA-Z\\{])', r'\\$', t)
    t = re.sub(r'(?<=[a-zA-Z}])\$', r'\\$', t)
    # 奇数個の ** を除去
    if t.count("**") % 2 == 1:
        t = t.replace("**", "")
    # 3個以上の * を ** に統一
    t = re.sub(r'\*{3,}', '**', t)
    t = re.sub(r'\*\*\s*\*\*', '', t)
    # HTMLタグ除去
    t = re.sub(r'</?strong[^>]*>', '', t, flags=re.IGNORECASE)
    t = re.sub(r'</?b[^>]*>', '', t, flags=re.IGNORECASE)
    # 3行以上の空行を2行に統一
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()


# ============================================================
# データソースバッジ
# ============================================================

def _render_badges(
    files: list[str],
    sql_result: SQLResult | None,
    data_ctx: DataContext,
) -> None:
    badges: list[str] = []
    local_all = data_ctx.assets.structured_files + data_ctx.assets.unstructured_files
    local_used = [f for f in files if f in local_all]

    if local_used:
        label = ", ".join(local_used[:3])
        if len(local_used) > 3:
            label += f" 他{len(local_used) - 3}件"
        badges.append(_badge("📂", "ローカル: " + label, _ACCENT))

    if sql_result is not None:
        badges.append(_badge("🗄️", f"BigQuery: 実データ取得済（{sql_result.row_count}件）", _GREEN))
    elif data_ctx.bq_result.is_connected:
        badges.append(_badge("🗄️", "BigQuery: スキーマ参照", _GREEN, border_opacity=0.35))
    elif data_ctx.bq_result.is_error:
        badges.append(_badge("🗄️", "BigQuery: 未接続", _RED))

    if data_ctx.gcs_result.is_error:
        badges.append(_badge("☁️", "GCS: 未接続", _RED))
    elif data_ctx.gcs_result.is_connected:
        badges.append(_badge("☁️", "GCS: 実データ参照", _GREEN, border_opacity=0.35))

    if badges:
        st.markdown(
            '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;margin-top:2px;">'
            + " ".join(badges) + "</div>",
            unsafe_allow_html=True,
        )

    if files:
        citations = "　".join(f"※{i+1}：{name}" for i, name in enumerate(files))
        st.markdown(
            f"<p style='color:rgba(255,255,255,0.4);font-size:0.78rem;margin-top:6px;'>{citations}</p>",
            unsafe_allow_html=True,
        )
    else:
        # filesが空の場合: AIが[FILES:]を出力しなかった
        st.markdown(
            "<p style='color:rgba(255,200,100,0.6);font-size:0.78rem;margin-top:6px;'>"
            "出典情報: AIからの戻り値なし</p>",
            unsafe_allow_html=True,
        )


def _badge(icon: str, label: str, color: str, bg_opacity: float = 0.12, border_opacity: float = 1.0) -> str:
    if color.startswith("#") and len(color) == 7:
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        bg     = f"rgba({r},{g},{b},{bg_opacity})"
        border = f"rgba({r},{g},{b},{border_opacity})" if border_opacity < 1 else color
    else:
        bg, border = f"rgba(255,255,255,{bg_opacity})", color
    return (
        f'<span style="background:{bg};border:1px solid {border};color:{color};'
        f'padding:2px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;white-space:nowrap;">'
        f'{icon} {label}</span>'
    )


# ============================================================
# SQL チャート / ログ
# ============================================================

def _render_sql_chart(sql_result: SQLResult) -> None:
    try:
        import plotly.graph_objects as go
        df = sql_result.to_dataframe()
        if df.empty or len(df.columns) < 2:
            return
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.iloc[:, 0].astype(str),
            y=df.iloc[:, 1],
            mode="lines+markers",
            line={"color": _BLUE, "width": 3},
            marker={"size": 8},
            name=str(df.columns[1]),
        ))
        fig.update_layout(
            title="📊 " + str(df.columns[1]),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin={"l": 10, "r": 10, "t": 40, "b": 10},
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except Exception:
        pass


def _render_sql_log(message: dict[str, Any]) -> None:
    sql_query      = message.get("sql_query")
    sql_result_dict = message.get("sql_result")
    if not sql_query or not sql_result_dict:
        return
    sql_result = SQLResult(**sql_result_dict)
    with st.expander(f"🗄️ BigQuery 実行ログ — ✅ 実データ（{sql_result.row_count}件取得）", expanded=False):
        st.code(sql_query, language="sql")
        col_a, col_b = st.columns(2)
        col_a.metric("取得件数", f"{sql_result.row_count} 件")
        col_b.metric("データ種別", "実データ", delta="BigQuery接続済み", delta_color="normal")


# ============================================================
# アクションボタン
# ============================================================

def _clean_markdown_for_download(text: str) -> str:
    """ベースプログラムから移植: Markdown記法を除去してプレーンテキストにする"""
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)  # 見出し(###)を削除
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # 太字(**text**)を削除
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # 斜体(*text*)を削除
    return text


def _render_action_buttons(
    index: int,
    message: dict[str, Any],
    selected_company: str,
) -> None:
    """ベースプログラムからそのまま移植"""
    memory = _get_memory()
    messages = memory.get_messages()
    prev_question = messages[index - 1]["content"] if index > 0 and messages[index - 1]["role"] == "user" else ""
    # 【修正】ベースプログラムと同様にMarkdown記法を除去
    plain = ((f"【質問】\n{_clean_markdown_for_download(prev_question)}\n\n【回答】\n" if prev_question else "") + _clean_markdown_for_download(message.get("content", "")))
    markdown_text = ((f"## 質問\n\n{prev_question}\n\n## 回答\n\n" if prev_question else "") + message.get("content", ""))
    timestamp = time.strftime("%Y%m%d-%H%M")
    safe_company = re.sub(r"[^\w\-]", "_", selected_company)
    artifacts = memory.get_artifacts(index)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.4])
    with col1:
        components.html(_get_copy_button_html(plain, f"btn_{index}"), height=45)
    with col2:
        st.download_button(label="💾 テキスト", data=plain, file_name=f"{timestamp}_{safe_company}.txt", mime="text/plain", key=f"dl_txt_{index}", type="secondary", use_container_width=True)
    with col3:
        components.html(_get_pdf_button_html(markdown_text, f"pdf_{index}", selected_company, timestamp), height=45)
    with col4:
        if st.button("📎 追加質問（案）", key=f"btn_deepdive_{index}", use_container_width=True, type="secondary"):
            st.session_state["pending_deepdive"] = {"assistant_index": index}
            st.rerun()

    if artifacts.get("deepdive"):
        st.markdown("<p style='color:rgba(255,255,255,0.4);font-size:0.8rem;margin-top:6px;margin-bottom:4px;'>📎 追加質問（案）</p>", unsafe_allow_html=True)
        for deep_index, question in enumerate(artifacts["deepdive"]):
            if st.button(question, key=f"dd_btn_{index}_{deep_index}", use_container_width=True, type="secondary"):
                st.session_state["pending_prompt"] = question
                artifacts.pop("deepdive", None)
                st.rerun()


def _get_copy_button_html(text_to_copy: str, button_id: str) -> str:
    """ベースプログラムからそのまま移植"""
    b64 = base64.b64encode(text_to_copy.encode("utf-8")).decode("utf-8")
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", button_id)
    return f"""<!DOCTYPE html>
<html><head><style>{_BTN_CSS}</style></head>
<body>
  <button id="copy-btn-{safe_id}" onclick="copyToClipboard()">📋 コピー</button>
  <script>
  function copyToClipboard() {{
    const text = decodeURIComponent(escape(window.atob("{b64}")));
    navigator.clipboard.writeText(text).catch(() => {{
      const el = document.createElement('textarea');
      el.value = text; document.body.appendChild(el);
      el.select(); document.execCommand('copy');
      document.body.removeChild(el);
    }});
    const btn = document.getElementById("copy-btn-{safe_id}");
    btn.innerHTML = "✅ 完了";
    setTimeout(() => {{ btn.innerHTML = "📋 コピー"; }}, 2000);
  }}
  </script>
</body></html>"""


def _get_pdf_button_html(markdown_text: str, button_id: str, company_name: str, timestamp: str) -> str:
    """ベースプログラムからそのまま移植 + タイムスタンプ追加"""
    b64 = base64.b64encode(markdown_text.encode("utf-8")).decode("utf-8")
    safe_company = re.sub(r"[^\w\-]", "_", company_name)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", button_id)
    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
<style>
{_BTN_CSS}
#pdf-content-wrapper {{ display:none; position:absolute; left:-9999px; }}
.pdf-page {{
  padding:40px;
  font-family:'Helvetica Neue',Helvetica,'Hiragino Sans',Arial,sans-serif;
  color:#1a1a1a; background-color:#ffffff; line-height:1.8;
}}
</style>
</head>
<body>
  <button id="pdf-btn-{safe_id}" onclick="generatePDF()">📄 PDF</button>
  <div id="pdf-content-wrapper"><div id="pdf-content" class="pdf-page"></div></div>
  <script>
  function generatePDF() {{
    const btn = document.getElementById("pdf-btn-{safe_id}");
    const orig = btn.innerHTML;
    btn.innerHTML = "⏳ 生成中...";
    const text = decodeURIComponent(escape(window.atob("{b64}")));
    const contentDiv = document.getElementById("pdf-content");
    const wrapper = document.getElementById("pdf-content-wrapper");
    contentDiv.innerHTML = marked.parse(text);
    wrapper.style.display = "block";
    const opt = {{
      margin:[15,15,15,15], filename:'{timestamp}_Report_{safe_company}.pdf',
      image:{{type:'jpeg',quality:0.98}},
      html2canvas:{{scale:2,useCORS:true}},
      jsPDF:{{unit:'mm',format:'a4',orientation:'portrait'}}
    }};
    html2pdf().set(opt).from(contentDiv).save()
      .then(() => {{
        wrapper.style.display = "none";
        btn.innerHTML = "✅ 完了";
        setTimeout(() => {{ btn.innerHTML = orig; }}, 2000);
      }})
      .catch(() => {{
        wrapper.style.display = "none";
        btn.innerHTML = "❌ エラー";
        setTimeout(() => {{ btn.innerHTML = orig; }}, 2000);
      }});
  }}
  </script>
</body></html>"""


def memory_get_artifacts(index: int) -> dict[str, Any]:
    return _get_memory().get_artifacts(index)


# ============================================================
# インフォグラフィック描画
# ============================================================

def _render_infographic(index: int) -> None:
    artifacts = memory_get_artifacts(index)

    # 【修正】深掘り質問の表示は _render_action_buttons() で行うため、ここでは削除
    # （重複表示の原因だった）

    # インフォグラフィックの表示
    if artifacts.get("info_html"):
        st.markdown("##### 🎨 インフォグラフィック")
        # 【修正】ベースプログラムと同じ動的高さ計算 + scrolling=True
        _info_data = artifacts.get("info_data", {})
        _n = max(
            len(_info_data.get("insights", [])),
            len(_info_data.get("actions", [])),
            5,
        )
        _dynamic_h = max(60 + _n * 100 + 120, 500)
        components.html(artifacts["info_html"], height=_dynamic_h, scrolling=True)


# ============================================================
# 右カラム（モニタリング・情報パネル）
# ============================================================

def _render_right_column(
    selected_company: str,
    data_ctx: DataContext,
    memory: SessionMemory,
) -> None:
    assets = data_ctx.assets

    with st.expander("📌 はじめに", expanded=False):
        st.markdown(assets.intro_text) if assets.intro_text else st.info("設定なし")

    with st.expander(f"📖 前提知識（{len(assets.knowledge_files)}件）", expanded=False):
        if assets.knowledge_files:
            for name in assets.knowledge_files:
                st.markdown(f"- `{name}`")
            preview = assets.knowledge_text[:APP.knowledge_preview_len]
            suffix  = "..." if len(assets.knowledge_text) > APP.knowledge_preview_len else ""
            st.code(preview + suffix, language="markdown")
        else:
            st.info("設定なし")

    with st.expander("📝 役割・回答方針", expanded=False):
        st.markdown(assets.prompt_text) if assets.prompt_text else st.info("設定なし")

    latest = next((m for m in reversed(memory.get_messages()) if m["role"] == "assistant"), None)
    with st.expander("AI処理フロー", expanded=True):
        if latest and latest.get("flow_steps"):
            for step in latest["flow_steps"]:
                check = "completed" if step.get("done") else "pending"
                icon = "&#x2705;" if step.get("done") else "&#x23F3;"
                name = step.get("step", "")
                detail = step.get("detail", "")
                detail_html = f"<span style='color:rgba(255,255,255,0.5);font-size:0.8rem;margin-left:8px;'>{detail}</span>" if detail else ""
                st.markdown(
                    f"<div style='padding:4px 0;font-size:0.95rem;'>{icon} {name}{detail_html}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("質問を送信すると、処理フローが表示されます。")

    with st.expander("AI思考ロジック", expanded=True):
        if latest and latest.get("thought_process"):
            st.markdown(latest["thought_process"])
        else:
            st.info("回答の表示から数秒後に、思考ロジックが表示されます。")

    st.markdown(
        "<div style='display:flex;align-items:center;gap:8px;margin:16px 0 10px 0;'>"
        "<div style='flex:1;height:1px;background:rgba(255,255,255,0.15);'></div>"
        "<span style='color:rgba(255,255,255,0.45);font-size:0.75rem;font-weight:700;"
        "letter-spacing:0.12em;white-space:nowrap;'>モニタリング</span>"
        "<div style='flex:1;height:1px;background:rgba(255,255,255,0.15);'></div></div>",
        unsafe_allow_html=True,
    )

    with st.expander("📡 データソース稼働状況", expanded=True):
        _render_status_panel(data_ctx)

    bq         = data_ctx.bq_result
    table_cnt  = len(re.findall(r"Table:", bq.content)) if bq.is_connected else "--"
    with st.expander(f"🗄️ クラウド読込｜構造化データ（{table_cnt}件）", expanded=False):
        if bq.is_error:
            st.error(f"🔴 BigQuery 接続エラー: {bq.error_detail}")
            st.info(f"💡 {bq.recovery_hint}")
        else:
            st.code(bq.content, language="markdown")

    gcs      = data_ctx.gcs_result
    gcs_files = re.findall(r"\[GCS:\s*(.+?)\]", gcs.content) if gcs.is_connected else []
    gcs_cnt  = len(gcs_files) if gcs.is_connected else "--"
    with st.expander(f"☁️ クラウド読込｜非構造化データ（{gcs_cnt}件）", expanded=False):
        if gcs.is_error:
            st.error(f"🔴 GCS 接続エラー: {gcs.error_detail}")
            st.info(f"💡 {gcs.recovery_hint}")
        elif gcs_files:
            for name in gcs_files:
                st.markdown(f"- `{name.strip()}`")
        else:
            st.info("（GCS資料なし）")

    total = len(assets.structured_files) + len(assets.unstructured_files)
    with st.expander(f"📂 ローカル読込（{total}件）", expanded=False):
        if total == 0:
            st.info("クラウドデータ優先のため非表示")
        else:
            for name in assets.structured_files + assets.unstructured_files:
                st.markdown(f"- `{name}`")


def _render_status_panel(data_ctx: DataContext) -> None:
    bq  = data_ctx.bq_result
    gcs = data_ctx.gcs_result
    local_cnt = len(data_ctx.assets.structured_files) + len(data_ctx.assets.unstructured_files)
    now = time.strftime("%H:%M")

    def _dot(ok: bool) -> str:
        c = "#22c55e" if ok else "orange"
        s = f"box-shadow:0 0 6px {c};" if ok else ""
        return f'<span style="width:8px;height:8px;border-radius:50%;background:{c};display:inline-block;margin-right:6px;{s}"></span>'

    def _lbl(result: Any) -> str:
        if result.is_connected:
            return '<span style="color:#22c55e;font-weight:700;">接続済み</span>'
        return f'<span style="color:#ff4b4b;font-weight:700;">接続エラー（{result.error_type}）</span>'

    local_dot = _dot(local_cnt > 0).replace("orange", "rgba(255,255,255,0.3)").replace("box-shadow:0 0 6px rgba(255,255,255,0.3);", "") if local_cnt == 0 else _dot(True)
    local_lbl = (f'<span style="color:#22c55e;font-weight:700;">{local_cnt}ファイル読込済</span>'
                 if local_cnt > 0 else '<span style="color:rgba(255,255,255,0.3);font-weight:700;">なし</span>')

    st.markdown(
        f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.10);'
        f'border-radius:10px;padding:12px 16px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;'
        f'font-size:0.82rem;color:rgba(255,255,255,0.75);border-bottom:1px solid rgba(255,255,255,0.05);">'
        f'<span>{_dot(bq.is_connected)}🗄️ BigQuery</span>{_lbl(bq)}</div>'
        f'<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;'
        f'font-size:0.82rem;color:rgba(255,255,255,0.75);border-bottom:1px solid rgba(255,255,255,0.05);">'
        f'<span>{_dot(gcs.is_connected)}☁️ GCS</span>{_lbl(gcs)}</div>'
        f'<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;'
        f'font-size:0.82rem;color:rgba(255,255,255,0.75);">'
        f'<span>{local_dot}📂 ローカルファイル</span>{local_lbl}</div>'
        f'<div style="font-size:0.72rem;color:rgba(255,255,255,0.25);margin-top:6px;text-align:right;">'
        f'最終確認: {now}（キャッシュ {APP.cache_ttl_seconds // 60}分）</div></div>',
        unsafe_allow_html=True,
    )


# ============================================================
# エラーバナー
# ============================================================

def _render_error_banner(data_ctx: DataContext) -> None:
    bq, gcs = data_ctx.bq_result, data_ctx.gcs_result
    if bq.is_connected and gcs.is_connected:
        return
    targets = " / ".join((["BigQuery"] if bq.is_error else []) + (["GCS"] if gcs.is_error else []))
    hints   = [f"{lbl}: {r.recovery_hint}" for lbl, r in (("BigQuery", bq), ("GCS", gcs)) if r.is_error]
    hint_html = (f"<br><span style='font-size:0.8rem;font-weight:400;opacity:0.85;'>"
                 + " / ".join(hints) + "</span>") if hints else ""
    st.markdown(
        f'<div style="background:linear-gradient(90deg,rgba(255,75,75,0.18),rgba(255,75,75,0.10));'
        f'border:1px solid #ff4b4b;border-radius:8px;padding:10px 16px;margin-bottom:12px;'
        f'display:flex;align-items:center;gap:10px;font-size:0.9rem;color:#ff4b4b;font-weight:600;">'
        f'🔴&nbsp;&nbsp;<strong>クラウド接続エラー</strong>&nbsp;—&nbsp;'
        f'{targets} への接続に失敗しました。{hint_html}</div>',
        unsafe_allow_html=True,
    )
