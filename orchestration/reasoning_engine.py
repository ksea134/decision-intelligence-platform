from __future__ import annotations
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Generator

from google import genai
from google.genai import types

from config.app_config import APP, MODELS
from config.cloud_config import CloudConfig
from domain.models import ChatMessage, MessageArtifacts, ParsedResponse, SQLResult
from domain.prompt_builder import build_system_prompt
from domain.response_parser import parse_llm_response
from domain.sql_validator import validate_sql, SQLValidationError
from orchestration.agents.data_agent import DataAgent, DataContext
from orchestration.memory.session_memory import SessionMemory

logger = logging.getLogger(__name__)



@dataclass
class StreamEvent:
    """A single event emitted during Gemini streaming."""
    kind: str
    text: str = ""
    status: str = ""
    executed_sql: str = ""
    sql_result: dict[str, Any] | None = None


@dataclass
class ResponseBundle:
    """Complete result of one reasoning cycle."""
    user_message: ChatMessage
    assistant_message: ChatMessage
    thought_process: str = ""
    info_html: str = ""
    info_data: dict[str, Any] | None = None
    deep_dive: list[str] | None = None


class ReasoningEngine:
    """
    Orchestration layer core — the brain of the system.

    Responsibilities:
    - Build system prompt from all data sources
    - Stream Gemini responses with Tool Call loop
    - Execute BigQuery SQL when Gemini requests it
    - Parse and clean LLM output
    - Generate thought process, infographic, deep-dive questions

    No Streamlit dependency. All UI concerns are handled by the caller.
    """

    def __init__(self, client: genai.Client, data_agent: DataAgent, memory: SessionMemory, router_agent=None, search_client=None) -> None:
        self._client = client
        self._data_agent = data_agent
        self._memory = memory
        self._router_agent = router_agent
        self._search_client = search_client

    # ----------------------------------------------------------
    # Main entry point
    # ----------------------------------------------------------

    def run(
        self,
        user_prompt: str,
        display_label: str,
        company: str,
        cfg: CloudConfig,
        data_ctx: DataContext,
    ) -> ResponseBundle | None:
        """
        Execute one full reasoning cycle.

        Args:
            user_prompt:   The actual prompt sent to Gemini.
            display_label: Text shown to the user (may differ from prompt).
            company:       Selected company name.
            cfg:           Cloud configuration.
            data_ctx:      All data sources from DataAgent.

        Returns:
            ResponseBundle with messages and generated artifacts.
            Returns None if Gemini returns an empty response.
        """
        history = self._memory.build_gemini_history(user_prompt)
        sys_prompt = build_system_prompt(
            company=company,
            bq_schema=data_ctx.bq_result.content,
            gcs_docs=data_ctx.gcs_result.content,
            knowledge=data_ctx.assets.knowledge_text,
            prompts=data_ctx.assets.prompt_text,
            structured=data_ctx.assets.structured_text,
            unstructured=data_ctx.assets.unstructured_text,
            bq_connected=data_ctx.bq_connected,
        )

        full_text, out_data = self._stream_and_collect(
            user_prompt=user_prompt,
            history=history,
            sys_prompt=sys_prompt,
            cfg=cfg,
            bq_connected=data_ctx.bq_connected,
        )

        if not full_text and not out_data:
            return None

        parsed = parse_llm_response(full_text)

        user_message: ChatMessage = {
            "role": "user",
            "content": display_label,
            "llm_prompt": user_prompt,
        }
        assistant_message: ChatMessage = {
            "role": "assistant",
            "content": parsed.display_text,
            "files": parsed.files,
            "thought_process": "",
            "sql_result": out_data.get("sql_result"),
            "sql_query": out_data.get("executed_sql") or parsed.sql or "",
            "artifacts": {},
        }

        return ResponseBundle(
            user_message=user_message,
            assistant_message=assistant_message,
        )

    # ----------------------------------------------------------
    # Streaming — v4 完全再設計
    # ----------------------------------------------------------
    #
    # 設計原則:
    #   - function calling を完全に廃止する
    #   - Gemini API呼び出しは固定回数（BQ時: 2回、非BQ時: 1回）
    #   - whileループなし、mode="ANY"なし、tools定義なし
    #   - Phase 1: SQL生成（軽量プロンプト、非ストリーミング）
    #   - Phase 2: 回答生成（フルプロンプト+データ、ストリーミング）
    #
    # 過去エラーへの対策:
    #   #1 バッククォート → validate_sql で自動付与
    #   #2 ツール未発火   → function calling自体を廃止、SQL生成を分離
    #   #3 遅延/無限ループ → function calling廃止、ループ廃止
    #   #4 SQL繰り返し   → SQL生成は1回固定
    #   #5 非ストリーミング遅延 → SQL生成は軽量プロンプトで高速化
    #   #6,#7 Router障害 → キーワード分類のみ（APIコールなし）
    #   #8 AUTO未発火再発 → function calling自体が存在しない

    def stream_events(
        self,
        user_prompt: str,
        company: str,
        cfg: CloudConfig,
        data_ctx: DataContext,
    ) -> Generator[Any, None, None]:
        if not user_prompt or not str(user_prompt).strip():
            raise ValueError(f"user_prompt cannot be empty: {repr(user_prompt)}")

        history = self._memory.build_gemini_history(user_prompt)
        logger.info("stream_events: user_prompt=%s...", user_prompt[:50])

        # AI処理フロー記録
        agent_labels = {"analysis": "要因分析", "comparison": "比較分析", "forecast": "予測分析", "general": "汎用回答"}
        flow_steps = []

        # ── Phase 0: 質問理解 + 過去事例検索 ──
        flow_steps.append({"step": "質問理解", "done": True})

        past_qa_context = ""
        if self._search_client and self._search_client.is_ready():
            try:
                logger.warning("[Search] Searching past Q&A: query='%s', company='%s'", user_prompt[:50], company)
                similar_qas = self._search_client.search(query=user_prompt, company=company, top_k=3)
                if similar_qas:
                    parts = []
                    for i, qa in enumerate(similar_qas, 1):
                        parts.append(f"事例{i}:\n  質問: {qa.get('question', '')}\n  回答: {qa.get('answer', '')}")
                    past_qa_context = "\n\n".join(parts)
                    flow_steps.append({"step": "過去事例検索", "done": True, "detail": f"{len(similar_qas)}件の類似事例を発見"})
                    logger.info("[Search] %d similar Q&As found", len(similar_qas))
                else:
                    flow_steps.append({"step": "過去事例検索", "done": True, "detail": "類似事例なし"})
            except Exception as e:
                logger.warning("[Search] Failed: %s", e)
                flow_steps.append({"step": "過去事例検索", "done": True, "detail": "検索スキップ"})
        else:
            flow_steps.append({"step": "過去事例検索", "done": True, "detail": "未接続"})

        # ── Phase 0.5: Router分類 ──
        intent = None
        if self._router_agent:
            try:
                classification = self._router_agent.classify(user_prompt)
                intent = classification.get("intent", "general")
                confidence = classification.get("confidence", 0.0)
                logger.info("[Router] intent=%s, confidence=%.2f", intent, confidence)
                flow_steps.append({"step": "ルートエージェント", "done": True, "detail": f"{agent_labels.get(intent, intent)}を選択"})
                flow_steps.append({"step": f"{agent_labels.get(intent, intent)}エージェント", "done": True})
                yield {"agent_type": intent, "confidence": confidence, "status": f"{agent_labels.get(intent, intent)}モード"}
            except Exception as e:
                logger.warning("[Router] Classification failed: %s", e)
                flow_steps.append({"step": "ルートエージェント", "done": True, "detail": "汎用回答を選択"})

        # ── Phase 1: データ取得（BQ接続時のみ） ──
        bq_data_csv = ""
        self._last_sql_result = None
        if data_ctx.bq_connected:
            yield {"status": "データを取得しています..."}
            bq_data_csv = self._fetch_bq_data(user_prompt, data_ctx)
            if self._last_sql_result:
                yield self._last_sql_result
                flow_steps.append({"step": "データ取得", "done": True, "detail": "BigQueryからデータ取得完了"})
            else:
                flow_steps.append({"step": "データ取得", "done": True, "detail": "データなし"})
        else:
            flow_steps.append({"step": "データ取得", "done": True, "detail": "ローカル/GCSデータを使用"})

        # ── Phase 2: 回答生成（ストリーミング） ──
        flow_steps.append({"step": "回答生成", "done": False})
        yield {"flow_steps": list(flow_steps)}
        sys_prompt = build_system_prompt(
            company=company,
            bq_schema=data_ctx.bq_result.content,
            gcs_docs=data_ctx.gcs_result.content,
            knowledge=data_ctx.assets.knowledge_text,
            prompts=data_ctx.assets.prompt_text,
            structured=data_ctx.assets.structured_text,
            unstructured=data_ctx.assets.unstructured_text,
            bq_connected=data_ctx.bq_connected,
            intent=intent,
        )

        # BQデータがあればシステムプロンプトに注入
        if bq_data_csv:
            sys_prompt += (
                "\n\n【BigQueryから取得した実データ — 必ずこの数値を使って回答すること】\n"
                f"{bq_data_csv}\n"
            )
            # GCS資料がある場合、数値だけでなく報告書も必ず反映するよう再強調
            if data_ctx.gcs_result.content.strip():
                sys_prompt += (
                    "\n【重要】上記の数値データだけでなく、先に提示したGCS資料（報告書）の内容も必ず回答に反映すること。"
                    "数値の背景・原因・考察が報告書に含まれている。数値だけの回答は禁止。\n"
                )

        # 過去事例があればシステムプロンプトに注入
        if past_qa_context:
            sys_prompt += (
                "\n\n【過去の類似Q&A — 参考にして回答の一貫性を保つこと】\n"
                f"{past_qa_context}\n"
            )

        current_history = list(history)

        yield {"status": "回答を生成しています..."}

        from orchestration.llm_client import generate_stream
        for chunk in generate_stream(
            model=MODELS.fast,
            contents=current_history,
            system_instruction=sys_prompt,
            temperature=0.0,
        ):
            yield chunk

        # 回答生成完了 → フロー最終状態をyield
        flow_steps[-1]["done"] = True  # 回答生成を完了に
        yield {"flow_steps": list(flow_steps)}

    def _fetch_bq_data(self, user_prompt: str, data_ctx: DataContext) -> str:
        """
        Phase 1: BQからデータを取得してCSVで返す。
        - テーブルが少数の場合: SELECT * で全データ取得（SQL生成不要、確実）
        - 失敗時は空文字を返す（Phase 2がデータなしで回答する）
        """
        import re
        from dataclasses import asdict

        try:
            # スキーマからテーブル一覧を抽出
            schema_text = data_ctx.bq_result.content
            tables = re.findall(r"Dataset:\s*(\S+)[\s\S]*?Table:\s*(\S+)", schema_text)

            if not tables:
                logger.warning("[Phase1] テーブルが見つかりません")
                return ""

            # 全テーブルからデータを取得してCSVに結合（30秒タイムアウト）
            import time as _time
            _bq_start = _time.time()
            _BQ_TIMEOUT = 30

            all_csv_parts = []
            first_sql = None
            first_result = None

            for dataset, table in tables:
                if _time.time() - _bq_start > _BQ_TIMEOUT:
                    logger.warning("[Phase1] タイムアウト（%d秒超過）。残りテーブルをスキップ", _BQ_TIMEOUT)
                    break
                sql = f"SELECT * FROM `{dataset}`.`{table}` LIMIT 100"
                logger.warning("[Phase1] SQL実行: %s", sql)

                try:
                    result = self._data_agent.execute_sql(sql)
                    if result and result.row_count > 0:
                        df = result.to_dataframe()
                        csv_part = f"--- {dataset}.{table} ---\n{df.head(100).to_csv(index=False)}"
                        all_csv_parts.append(csv_part)
                        logger.warning("[Phase1] %s.%s: %d行取得", dataset, table, result.row_count)

                        if first_sql is None:
                            first_sql = sql
                            first_result = result
                except Exception as e:
                    logger.error("[Phase1] %s.%s 取得エラー: %s", dataset, table, e)

            if not all_csv_parts:
                logger.warning("[Phase1] データ取得できず")
                return ""

            # SQL結果を保存（UIでの表示用）
            if first_result:
                self._last_sql_result = {"executed_sql": first_sql, "sql_result": asdict(first_result)}

            return "\n\n".join(all_csv_parts)

        except Exception as e:
            logger.error("[Phase1] データ取得エラー: %s", e)
            return ""

    # ----------------------------------------------------------
    # Supplement phase
    # ----------------------------------------------------------

    def generate_thought_process(
        self,
        user_question: str,
        assistant_answer: str,
        structured_data: str,
        unstructured_data: str,
    ) -> str:
        """Generate 4-step thought process from Q&A pair."""
        prompt = (
            "あなたはAIの推論過程を分析するシステムです。\n"
            "以下の質問・回答・データから、4ステップの思考プロセスを再構成してください。\n\n"
            "【質問】" + user_question + "\n\n"
            "【回答】" + assistant_answer + "\n\n"
            "【構造化データ（抜粋）】" + (structured_data[:APP.prompt_data_limit] if structured_data else "なし") + "\n\n"
            "【非構造化データ（抜粋）】" + (unstructured_data[:APP.prompt_data_limit] if unstructured_data else "なし") + "\n\n"
            "以下のフォーマットのみ出力すること。他のテキストは一切不要。\n"
            "各項目は体言止めで簡潔に記載し、ブレット（-）形式で列挙すること。\n\n"
            "**Step 1: データの定量的把握**\n- （体言止めで事実を列挙）\n\n"
            "**Step 2: リスク・文脈の把握**\n- （体言止めでリスク・背景を列挙）\n\n"
            "**Step 3: 論点・仮説の統合**\n- （体言止めで論点・仮説を列挙）\n\n"
            "**Step 4: 回答方針**\n- （体言止めで方針を列挙）"
        )
        try:
            return self._generate_text(prompt)
        except Exception as exc:
            logger.error("thought process generation failed: %s", exc)
            return ""

    def generate_infographic(self, content: str, timestamp: str = "", company: str = "") -> tuple[str, dict[str, Any]]:
        """
        Generate infographic HTML from answer text.
        Returns (html_string, data_dict).
        """
        prompt = (
            "あなたはデータ抽出の専門家です。\n"
            "以下の回答文を分析し、エグゼクティブ向けインフォグラフィック用のデータをJSON形式で返してください。\n\n"
            "【出力ルール（厳守）】\n"
            "- JSON のみを出力すること。説明文・前置きは一切含めないこと\n"
            "- 文字列内のダブルクォートはエスケープ（\\\"）すること\n"
            "- 必ず以下のキーをすべて含めること\n"
            "- insights は必ず5件、actions は必ず5件出力すること\n\n"
            '{"title":"回答の核心を表す短いタイトル（20字以内）",'
            '"summary":"意思決定者向けのエグゼクティブサマリー（80字以内）",'
            '"kpi":{"label":"最も重要な指標名（10字以内）","value":"その数値または状態（10字以内）","delta":"前期比・変化率など（任意・不明なら空文字）"},'
            '"insights":[{"icon":"絵文字1つ","label":"カテゴリ（10字以内）","text":"内容（40字以内）"}],'
            '"actions":[{"text":"アクション内容（30字以内）","priority":"high/medium/low"}]}\n\n'
            "回答文:\n" + content[:APP.prompt_content_limit]
        )
        default: dict[str, Any] = {
            "title": "エグゼクティブサマリー",
            "summary": "回答の要点を整理しました。",
            "kpi": {"label": "注目指標", "value": "-", "delta": ""},
            "insights": [
                {"icon": "📊", "label": "分析1", "text": "データを確認中です"},
                {"icon": "📈", "label": "分析2", "text": "詳細は本文をご確認ください"},
                {"icon": "📉", "label": "分析3", "text": "追加分析が必要です"},
                {"icon": "💡", "label": "分析4", "text": "示唆を抽出中です"},
                {"icon": "🔍", "label": "分析5", "text": "深掘りが推奨されます"},
            ],
            "actions": [
                {"text": "詳細は回答本文をご確認ください", "priority": "high"},
                {"text": "追加データの収集を検討", "priority": "medium"},
                {"text": "関係者への共有を推奨", "priority": "medium"},
                {"text": "次のアクションを策定", "priority": "low"},
                {"text": "継続的なモニタリング", "priority": "low"},
            ],
        }
        try:
            raw = self._generate_text(prompt)
            data = self._extract_json(raw)
            if not isinstance(data, dict):
                raise ValueError("not a dict")
        except Exception as exc:
            logger.warning("infographic JSON failed, using default: %s", exc)
            data = default

        html = self._build_infographic_html(data, timestamp, company)
        return html, data

    def generate_deep_dive(self, user_question: str, assistant_answer: str) -> list[str]:
        """Generate follow-up question suggestions."""
        prompt = (
            "You are a management consultant.\n"
            "Based on the Q&A below, suggest " + str(APP.deep_dive_count) + " follow-up questions.\n\n"
            "Question: " + user_question + "\n\n"
            "Answer: " + assistant_answer[:APP.prompt_content_limit] + "\n\n"
            "Return ONLY a JSON array of strings. No markdown, no backticks.\n"
            '["question1","question2","question3"]\n\n'
            "Rules: each question 20-40 Japanese characters, deepen the analysis."
        )
        try:
            result = self._extract_json(self._generate_text(prompt))
            if isinstance(result, list):
                return [str(x) for x in result[:APP.deep_dive_count]]
        except Exception as exc:
            logger.error("deep dive generation failed: %s", exc)
        return []

    # ----------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------

    def _stream_and_collect(
        self,
        user_prompt: str,
        history: list[dict[str, str]],
        sys_prompt: str,
        cfg: CloudConfig,
        bq_connected: bool,
    ) -> tuple[str, dict[str, Any]]:
        """Consume stream_events and collect full text + metadata."""
        chunks: list[str] = []
        out_data: dict[str, Any] = {}

        data_ctx_stub = _MinimalDataCtx(bq_connected=bq_connected)

        for event in self.stream_events(user_prompt, "", cfg, data_ctx_stub):
            if event.kind == "text":
                chunks.append(event.text)
            elif event.kind == "sql":
                out_data["executed_sql"] = event.executed_sql
                out_data["sql_result"] = event.sql_result

        return "".join(chunks), out_data

    def _generate_text(self, prompt: str) -> str:
        from orchestration.llm_client import generate_text
        return generate_text(model=MODELS.supplement, contents=prompt)

    def _extract_json(self, text: str) -> Any:
        cleaned = text.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        for open_ch, close_ch in (("{", "}"), ("[", "]")):
            start = cleaned.find(open_ch)
            if start == -1:
                continue
            depth = 0
            in_string = False
            escape_next = False
            for idx in range(start, len(cleaned)):
                ch = cleaned[idx]
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\":
                    escape_next = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(cleaned[start:idx + 1])
                        except json.JSONDecodeError:
                            break
        return None

    def _build_infographic_html(self, data: dict[str, Any], timestamp: str = "", company: str = "") -> str:
        import html as html_mod
        import re as re_mod
        title = html_mod.escape(str(data.get("title", "Summary")))
        summary = html_mod.escape(str(data.get("summary", "")))
        kpi = data.get("kpi", {})
        kpi_label = html_mod.escape(str(kpi.get("label", "")))
        kpi_value = html_mod.escape(str(kpi.get("value", "-")))
        kpi_delta = html_mod.escape(str(kpi.get("delta", "")))
        insights = data.get("insights", [])
        actions = data.get("actions", [])
        
        # ファイル名用
        safe_company = re_mod.sub(r"[^\w\-]", "_", company) if company else "Report"
        png_filename = f"{timestamp}_Infographic_{safe_company}.png" if timestamp else "infographic.png"

        # アクセントカラー
        accent = "#D2FF00"

        insight_rows = ""
        for item in insights[:5]:
            icon = html_mod.escape(str(item.get("icon", "●")))
            label = html_mod.escape(str(item.get("label", "")))
            text = html_mod.escape(str(item.get("text", "")))
            insight_rows += (
                '<div class="insight-row">'
                '<span class="insight-icon">' + icon + '</span>'
                '<div><span class="insight-label">' + label + '</span>'
                '<span class="insight-text">' + text + '</span></div>'
                '</div>'
            )

        priority_color = {"high": "#ff4b4b", "medium": "#f59e0b", "low": "#38bdf8"}
        action_rows = ""
        for item in actions[:5]:
            text = html_mod.escape(str(item.get("text", "")))
            color = priority_color.get(str(item.get("priority", "medium")).lower(), "#38bdf8")
            action_rows += (
                '<div class="action-row">'
                '<span class="action-dot" style="background:' + color + '"></span>'
                '<span class="action-text">' + text + '</span>'
                '</div>'
            )

        delta_html = '<span class="kpi-delta">' + kpi_delta + '</span>' if kpi_delta else ""

        # ベースプログラムと同じHTML構造（PNG保存ボタン付き）
        return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:100%;min-height:100%;background:#0e1117;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#fff}}
.root{{
  display:grid;
  grid-template-columns:1fr;
  grid-template-rows:auto;
  gap:12px;
  padding:18px;
  min-height:100%;
  background:#0e1117;
}}
@media(min-width:768px){{
  .root{{grid-template-columns:1.2fr 1fr 1fr;grid-template-rows:auto auto;}}
  .header{{grid-column:1/-1;}}
}}
.header{{
  display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;
  border-bottom:1px solid rgba(255,255,255,0.12);
  padding-bottom:10px;
}}
.header-kicker{{
  font-size:10px;letter-spacing:.14em;font-weight:700;
  color:{accent};text-transform:uppercase;white-space:nowrap;
}}
.header-title{{
  font-size:20px;font-weight:800;line-height:1.2;
  color:#fff;
}}
.card{{
  background:rgba(255,255,255,0.05);
  border:1px solid rgba(255,255,255,0.10);
  border-radius:16px;padding:18px;
  display:flex;flex-direction:column;
  justify-content:flex-start;
  gap:0;overflow:visible;
}}
.card-title{{
  font-size:12px;letter-spacing:.10em;font-weight:700;
  color:rgba(255,255,255,0.45);text-transform:uppercase;
  margin-bottom:12px;flex-shrink:0;
}}
.summary-text{{
  font-size:15px;line-height:1.8;color:rgba(255,255,255,0.90);
  flex:1;overflow:hidden;
}}
.kpi-block{{
  margin-top:16px;padding:14px;flex-shrink:0;
  background:rgba(210,255,0,0.08);
  border:1px solid rgba(210,255,0,0.25);
  border-radius:12px;
}}
.kpi-label{{font-size:12px;color:rgba(255,255,255,0.55);margin-bottom:6px;}}
.kpi-value{{font-size:22px;font-weight:800;color:{accent};line-height:1;}}
@media(min-width:768px){{.kpi-value{{font-size:30px;}}}}
.kpi-delta{{font-size:14px;font-weight:600;color:{accent};margin-left:10px;opacity:.8;}}
.insight-list{{display:flex;flex-direction:column;flex:1;justify-content:flex-start;}}
.insight-row{{
  display:flex;align-items:flex-start;gap:10px;
  padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.07);
}}
.insight-row:last-child{{border-bottom:none;}}
.insight-icon{{font-size:16px;flex-shrink:0;margin-top:2px;}}
.insight-label{{
  font-size:12px;font-weight:700;
  color:{accent};margin-right:6px;white-space:nowrap;
}}
.insight-text{{
  font-size:14px;color:rgba(255,255,255,0.85);line-height:1.55;
  overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
}}
.action-list{{display:flex;flex-direction:column;flex:1;justify-content:flex-start;}}
.action-row{{
  display:flex;align-items:flex-start;gap:10px;
  padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.07);
}}
.action-row:last-child{{border-bottom:none;}}
.action-dot{{
  width:8px;height:8px;border-radius:50%;
  flex-shrink:0;margin-top:5px;
}}
.action-text{{
  font-size:14px;color:rgba(255,255,255,0.88);line-height:1.55;
  overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
}}
#save-bar{{
  display:flex;justify-content:center;
  padding:14px 18px 18px 18px;
}}
#save-btn{{
  background:rgba(255,255,255,0.06);
  border:1px solid rgba(255,255,255,0.20);
  color:rgba(255,255,255,0.75);
  font-size:13px;font-weight:600;
  padding:8px 24px;border-radius:8px;
  cursor:pointer;transition:background .15s,color .15s;
}}
#save-btn:hover{{
  background:rgba(255,255,255,0.12);color:#fff;
}}
</style>
</head>
<body>
<div class="root">
  <div class="header">
    <span class="header-kicker">EXECUTIVE INFOGRAPHIC</span>
    <span class="header-title">{title}</span>
  </div>
  <div class="card">
    <div class="card-title">エグゼクティブサマリー</div>
    <div class="summary-text">{summary}</div>
    <div class="kpi-block">
      <div class="kpi-label">{kpi_label}</div>
      <div class="kpi-value">{kpi_value}{delta_html}</div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">主要インサイト</div>
    <div class="insight-list">
    {insight_rows}
    </div>
  </div>
  <div class="card">
    <div class="card-title">推奨アクション</div>
    <div class="action-list">
    {action_rows}
    </div>
  </div>
</div>

<div id="save-bar">
  <button id="save-btn" onclick="saveAsPng()">📷 PNG保存</button>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script>
function saveAsPng() {{
  var btn = document.getElementById('save-btn');
  var bar = document.getElementById('save-bar');
  btn.textContent = '⏳ 生成中...';
  btn.disabled = true;
  bar.style.display = 'none';
  html2canvas(document.querySelector('.root'), {{
    backgroundColor: '#0e1117',
    scale: 2,
    useCORS: true,
    logging: false
  }}).then(function(canvas) {{
    bar.style.display = 'flex';
    btn.textContent = '📷 PNG保存';
    btn.disabled = false;
    var link = document.createElement('a');
    link.download = '{png_filename}';
    link.href = canvas.toDataURL('image/png');
    link.click();
  }}).catch(function() {{
    bar.style.display = 'flex';
    btn.textContent = '❌ エラー';
    setTimeout(function() {{ btn.textContent = '📷 PNG保存'; btn.disabled = false; }}, 2000);
  }});
}}
</script>
</body>
</html>"""


class _MinimalDataCtx:
    """Minimal DataContext stub for internal use."""
    def __init__(self, bq_connected: bool) -> None:
        self.bq_connected = bq_connected
