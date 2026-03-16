"""
orchestration/reasoning_engine_v2.py — Agent Router 統合版 ReasoningEngine

【役割】
Agent Router（LangGraph ワークフロー）を統合した ReasoningEngine。
ユーザーの質問を意図分類し、専門エージェントにルーティングする。

【設計原則】
- 既存の ReasoningEngine との後方互換性を維持
- use_agent_router フラグで動作を切り替え可能
- ストリーミング対応
- 思考プロセス・深掘り質問生成を統合

【使用方法】
```python
engine = ReasoningEngineV2(client, data_agent, memory)

# Agent Router を使用（デフォルト）
result = engine.run(user_prompt, display_label, company, cfg, data_ctx)

# 従来の直接 Gemini 呼び出し
result = engine.run(user_prompt, display_label, company, cfg, data_ctx, use_agent_router=False)
```
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Any, Generator, Optional

from orchestration.graph.state import AgentResult, WorkflowState, create_initial_state
from orchestration.graph.workflow import run_workflow, compile_workflow

# google-genai はオプション依存
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# データクラス
# -----------------------------------------------------------------------------
@dataclass
class StreamEvent:
    """ストリーミング中のイベント"""
    kind: str  # "text", "status", "sql", "agent_selected", "complete"
    text: str = ""
    status: str = ""
    executed_sql: str = ""
    sql_result: dict[str, Any] | None = None
    agent_type: str = ""  # Router が選択したエージェント種別
    confidence: float = 0.0  # 分類信頼度


@dataclass
class ResponseBundle:
    """推論サイクルの完全な結果"""
    user_message: dict[str, Any]
    assistant_message: dict[str, Any]
    thought_process: str = ""
    info_html: str = ""
    info_data: dict[str, Any] | None = None
    deep_dive: list[str] | None = None
    agent_type: str = ""  # どのエージェントが回答したか
    classification_confidence: float = 0.0


# -----------------------------------------------------------------------------
# ReasoningEngineV2 クラス
# -----------------------------------------------------------------------------
class ReasoningEngineV2:
    """
    Agent Router 統合版 ReasoningEngine。
    
    ユーザーの質問を意図分類し、専門エージェント（Analysis/Comparison/Forecast/General）
    にルーティングして回答を生成する。
    """
    
    def __init__(
        self,
        client: Any,  # genai.Client
        data_agent: Any,  # DataAgent
        memory: Any,  # SessionMemory
        use_llm_router: bool = True,
        use_llm_agents: bool = True,
    ) -> None:
        """
        ReasoningEngineV2 を初期化する。
        
        Args:
            client: Gemini API クライアント
            data_agent: DataAgent インスタンス
            memory: SessionMemory インスタンス
            use_llm_router: LLM ベースの Router を使用するか
            use_llm_agents: LLM ベースのエージェントを使用するか
        """
        self._client = client
        self._data_agent = data_agent
        self._memory = memory
        self._use_llm_router = use_llm_router
        self._use_llm_agents = use_llm_agents
        
        # ワークフローをプリコンパイル（パフォーマンス最適化）
        self._compiled_workflow = None
    
    # ----------------------------------------------------------
    # メインエントリポイント
    # ----------------------------------------------------------
    
    def run(
        self,
        user_prompt: str,
        display_label: str,
        company: str,
        cfg: Any,  # CloudConfig
        data_ctx: Any,  # DataContext
        use_agent_router: bool = True,
    ) -> ResponseBundle | None:
        """
        推論サイクルを実行する。
        
        Args:
            user_prompt: Gemini に送信するプロンプト
            display_label: ユーザーに表示するテキスト
            company: 企業名
            cfg: クラウド設定
            data_ctx: データコンテキスト
            use_agent_router: Agent Router を使用するか
        
        Returns:
            ResponseBundle、または空の応答の場合は None
        """
        start_time = time.time()
        
        if use_agent_router:
            result = self._run_with_agent_router(
                user_prompt=user_prompt,
                display_label=display_label,
                company=company,
                cfg=cfg,
                data_ctx=data_ctx,
            )
        else:
            # 従来の直接 Gemini 呼び出し
            result = self._run_direct(
                user_prompt=user_prompt,
                display_label=display_label,
                company=company,
                cfg=cfg,
                data_ctx=data_ctx,
            )
        
        elapsed = time.time() - start_time
        logger.info("[ReasoningEngineV2] run() completed in %.2f sec", elapsed)
        
        return result
    
    def _run_with_agent_router(
        self,
        user_prompt: str,
        display_label: str,
        company: str,
        cfg: Any,
        data_ctx: Any,
    ) -> ResponseBundle | None:
        """Agent Router を使用して推論を実行する"""
        
        # ワークフロー状態を作成
        workflow_result = run_workflow(
            user_prompt=user_prompt,
            display_label=display_label,
            company=company,
            company_folder=cfg.folder_name if cfg else "",
            bq_schema=data_ctx.bq_result.content if data_ctx else "",
            gcs_docs=data_ctx.gcs_result.content if data_ctx else "",
            knowledge=data_ctx.assets.knowledge_text if data_ctx and data_ctx.assets else "",
            prompts=data_ctx.assets.prompt_text if data_ctx and data_ctx.assets else "",
            structured_data=data_ctx.assets.structured_text if data_ctx and data_ctx.assets else "",
            unstructured_data=data_ctx.assets.unstructured_text if data_ctx and data_ctx.assets else "",
            bq_connected=data_ctx.bq_connected if data_ctx else False,
            client=self._client,
            use_llm_router=self._use_llm_router,
            use_llm_agents=self._use_llm_agents,
        )
        
        # 結果を取得
        agent_result = workflow_result.get("agent_result")
        classification = workflow_result.get("classification", {})
        
        if not agent_result:
            logger.warning("[ReasoningEngineV2] No agent_result in workflow output")
            return None
        
        response_text = agent_result.get("response_text", "")
        files = agent_result.get("files", [])
        
        if not response_text:
            logger.warning("[ReasoningEngineV2] Empty response from agent")
            return None
        
        # メッセージを構築
        user_message = {
            "role": "user",
            "content": display_label,
            "llm_prompt": user_prompt,
        }
        
        assistant_message = {
            "role": "assistant",
            "content": response_text,
            "files": files,
            "thought_process": "",
            "sql_result": agent_result.get("sql_result"),
            "sql_query": agent_result.get("sql_query", ""),
            "artifacts": {},
        }
        
        # メモリに追加
        if self._memory:
            self._memory.add_turn(user_prompt, response_text)
        
        return ResponseBundle(
            user_message=user_message,
            assistant_message=assistant_message,
            agent_type=classification.get("intent", "general"),
            classification_confidence=classification.get("confidence", 0.0),
        )
    
    def _run_direct(
        self,
        user_prompt: str,
        display_label: str,
        company: str,
        cfg: Any,
        data_ctx: Any,
    ) -> ResponseBundle | None:
        """従来の直接 Gemini 呼び出し（後方互換性用）"""
        # 簡略化された実装
        # 本番では既存の ReasoningEngine.run() を呼び出すか、
        # そのロジックをここに移植する
        
        logger.info("[ReasoningEngineV2] Using direct Gemini call (legacy mode)")
        
        # 簡易実装: GeneralAgent を直接呼び出す
        from orchestration.agents.general_agent import GeneralAgent
        
        state = create_initial_state(
            user_prompt=user_prompt,
            display_label=display_label,
            company=company,
            company_folder=cfg.folder_name if cfg else "",
            bq_schema=data_ctx.bq_result.content if data_ctx else "",
            gcs_docs=data_ctx.gcs_result.content if data_ctx else "",
            knowledge=data_ctx.assets.knowledge_text if data_ctx and data_ctx.assets else "",
            prompts=data_ctx.assets.prompt_text if data_ctx and data_ctx.assets else "",
            structured_data=data_ctx.assets.structured_text if data_ctx and data_ctx.assets else "",
            unstructured_data=data_ctx.assets.unstructured_text if data_ctx and data_ctx.assets else "",
            bq_connected=data_ctx.bq_connected if data_ctx else False,
        )
        
        agent = GeneralAgent(client=self._client)
        result = agent.run(state)
        
        agent_result = result.get("agent_result")
        if not agent_result:
            return None
        
        user_message = {
            "role": "user",
            "content": display_label,
            "llm_prompt": user_prompt,
        }
        
        assistant_message = {
            "role": "assistant",
            "content": agent_result.get("response_text", ""),
            "files": agent_result.get("files", []),
            "thought_process": "",
            "sql_result": None,
            "sql_query": "",
            "artifacts": {},
        }
        
        return ResponseBundle(
            user_message=user_message,
            assistant_message=assistant_message,
            agent_type="general",
        )
    
    # ----------------------------------------------------------
    # ストリーミング対応
    # ----------------------------------------------------------
    
    def stream_events(
        self,
        user_prompt: str,
        company: str,
        cfg: Any,
        data_ctx: Any,
        use_agent_router: bool = True,
    ) -> Generator[StreamEvent, None, None]:
        """
        ストリーミングでイベントを生成する。
        
        Args:
            user_prompt: ユーザーの質問
            company: 企業名
            cfg: クラウド設定
            data_ctx: データコンテキスト
            use_agent_router: Agent Router を使用するか
        
        Yields:
            StreamEvent オブジェクト
        """
        if not user_prompt or not str(user_prompt).strip():
            raise ValueError(f"user_prompt cannot be empty: {repr(user_prompt)}")
        
        if use_agent_router:
            yield from self._stream_with_agent_router(
                user_prompt=user_prompt,
                company=company,
                cfg=cfg,
                data_ctx=data_ctx,
            )
        else:
            yield from self._stream_direct(
                user_prompt=user_prompt,
                company=company,
                cfg=cfg,
                data_ctx=data_ctx,
            )
    
    def _stream_with_agent_router(
        self,
        user_prompt: str,
        company: str,
        cfg: Any,
        data_ctx: Any,
    ) -> Generator[StreamEvent, None, None]:
        """Agent Router を使用したストリーミング"""
        
        # 意図分類フェーズ
        yield StreamEvent(kind="status", status="🧠 質問を分析しています...")
        
        # ワークフローを実行（現時点では非ストリーミング）
        # 将来的には LangGraph のストリーミング機能を使用
        workflow_result = run_workflow(
            user_prompt=user_prompt,
            display_label=user_prompt,
            company=company,
            company_folder=cfg.folder_name if cfg else "",
            bq_schema=data_ctx.bq_result.content if data_ctx else "",
            gcs_docs=data_ctx.gcs_result.content if data_ctx else "",
            knowledge=data_ctx.assets.knowledge_text if data_ctx and data_ctx.assets else "",
            prompts=data_ctx.assets.prompt_text if data_ctx and data_ctx.assets else "",
            structured_data=data_ctx.assets.structured_text if data_ctx and data_ctx.assets else "",
            unstructured_data=data_ctx.assets.unstructured_text if data_ctx and data_ctx.assets else "",
            bq_connected=data_ctx.bq_connected if data_ctx else False,
            client=self._client,
            use_llm_router=self._use_llm_router,
            use_llm_agents=self._use_llm_agents,
        )
        
        # 分類結果を通知
        classification = workflow_result.get("classification", {})
        agent_type = classification.get("intent", "general")
        confidence = classification.get("confidence", 0.0)
        
        agent_labels = {
            "analysis": "📊 要因分析",
            "comparison": "⚖️ 比較分析",
            "forecast": "🔮 予測分析",
            "general": "💬 汎用回答",
        }
        
        yield StreamEvent(
            kind="agent_selected",
            status=f"{agent_labels.get(agent_type, '💬 回答生成')}エージェントを選択しました",
            agent_type=agent_type,
            confidence=confidence,
        )
        
        yield StreamEvent(kind="status", status="✍️ 回答を生成しています...")
        
        # エージェント結果を取得
        agent_result = workflow_result.get("agent_result")
        
        if agent_result:
            response_text = agent_result.get("response_text", "")
            
            # テキストをチャンク単位で yield（ストリーミング模倣）
            # 将来的には実際の LLM ストリーミングに置き換え
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield StreamEvent(kind="text", text=chunk)
            
            # SQL 結果があれば通知
            if agent_result.get("sql_query"):
                yield StreamEvent(
                    kind="sql",
                    executed_sql=agent_result.get("sql_query", ""),
                    sql_result=agent_result.get("sql_result"),
                )
        
        yield StreamEvent(kind="complete", status="✅ 完了")
    
    def _stream_direct(
        self,
        user_prompt: str,
        company: str,
        cfg: Any,
        data_ctx: Any,
    ) -> Generator[StreamEvent, None, None]:
        """従来の直接ストリーミング（後方互換性用）"""
        yield StreamEvent(kind="status", status="✍️ 回答を生成しています...")
        
        # 簡易実装
        result = self._run_direct(
            user_prompt=user_prompt,
            display_label=user_prompt,
            company=company,
            cfg=cfg,
            data_ctx=data_ctx,
        )
        
        if result:
            response_text = result.assistant_message.get("content", "")
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield StreamEvent(kind="text", text=chunk)
        
        yield StreamEvent(kind="complete", status="✅ 完了")
    
    # ----------------------------------------------------------
    # 補足フェーズ
    # ----------------------------------------------------------
    
    def generate_thought_process(
        self,
        user_question: str,
        assistant_answer: str,
        structured_data: str = "",
        unstructured_data: str = "",
        agent_type: str = "general",
    ) -> str:
        """
        4ステップの思考プロセスを生成する。
        
        エージェントタイプに応じて、より専門的な思考プロセスを生成。
        """
        # エージェントタイプ別のプロンプト調整
        agent_context = {
            "analysis": "要因分析の観点から、5 Whys や寄与度分析を踏まえて",
            "comparison": "比較分析の観点から、各対象の強み・弱みを踏まえて",
            "forecast": "予測分析の観点から、3シナリオ（楽観/基本/悲観）を踏まえて",
            "general": "総合的な観点から",
        }
        
        context = agent_context.get(agent_type, "総合的な観点から")
        
        prompt = f"""あなたは AI の推論プロセスを分析するシステムです。
以下の質問と回答を分析し、{context}4ステップの思考プロセスを再構築してください。

質問: {user_question}

回答: {assistant_answer[:2000]}

構造化データ（抜粋）: {structured_data[:500] if structured_data else "なし"}

非構造化データ（抜粋）: {unstructured_data[:500] if unstructured_data else "なし"}

以下の形式で日本語で出力してください。他のテキストは含めないでください。

**Step 1: データの定量的把握**
- （箇条書き）

**Step 2: リスク・文脈の把握**
- （箇条書き）

**Step 3: 論点・仮説の統合**
- （箇条書き）

**Step 4: 回答方針**
- （箇条書き）
"""
        
        try:
            return self._generate_text(prompt)
        except Exception as e:
            logger.error("[ReasoningEngineV2] thought process generation failed: %s", e)
            return ""
    
    def generate_deep_dive(
        self,
        user_question: str,
        assistant_answer: str,
        agent_type: str = "general",
        count: int = 3,
    ) -> list[str]:
        """
        深掘り質問を生成する。
        
        エージェントタイプに応じて、より専門的な深掘り質問を生成。
        """
        agent_hints = {
            "analysis": "根本原因の深掘り、他の要因の検討、対策の具体化",
            "comparison": "追加の比較軸、時系列での変化、特定条件下での比較",
            "forecast": "シナリオの詳細化、リスク要因の深掘り、対応策の検討",
            "general": "追加情報の要求、具体例の要求、関連トピックへの展開",
        }
        
        hint = agent_hints.get(agent_type, "")
        
        prompt = f"""あなたは経営コンサルタントです。
以下の Q&A を踏まえ、{count}件の深掘り質問を提案してください。

質問: {user_question}

回答: {assistant_answer[:2000]}

{f"方向性のヒント: {hint}" if hint else ""}

以下のルールに従ってください:
- JSON 配列のみを出力（マークダウンやバッククォートは不要）
- 各質問は日本語で 20〜40 文字
- 分析を深める質問にすること

["質問1", "質問2", "質問3"]
"""
        
        try:
            result = self._extract_json(self._generate_text(prompt))
            if isinstance(result, list):
                return [str(x) for x in result[:count]]
        except Exception as e:
            logger.error("[ReasoningEngineV2] deep dive generation failed: %s", e)
        
        return []
    
    def generate_infographic(
        self,
        content: str,
        timestamp: str = "",
        company: str = "",
    ) -> tuple[str, dict[str, Any]]:
        """
        インフォグラフィック HTML を生成する。
        
        Returns:
            (html_string, data_dict)
        """
        prompt = f"""あなたはデータ抽出の専門家です。
以下の回答文を分析し、エグゼクティブ向けインフォグラフィック用のデータを JSON 形式で返してください。

【出力ルール（厳守）】
- JSON のみを出力すること。説明文・前置きは一切含めないこと
- 文字列内のダブルクォートはエスケープ（\\"）すること
- 必ず以下のキーをすべて含めること
- insights は必ず5件、actions は必ず5件出力すること

{{"title":"回答の核心を表す短いタイトル（20字以内）",
"summary":"意思決定者向けのエグゼクティブサマリー（80字以内）",
"kpi":{{"label":"最も重要な指標名（10字以内）","value":"その数値または状態（10字以内）","delta":"前期比・変化率など（任意・不明なら空文字）"}},
"insights":[{{"icon":"絵文字1つ","label":"カテゴリ（10字以内）","text":"内容（40字以内）"}}],
"actions":[{{"text":"アクション内容（30字以内）","priority":"high/medium/low"}}]}}

回答文:
{content[:3000]}
"""
        
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
        except Exception as e:
            logger.warning("[ReasoningEngineV2] infographic JSON failed, using default: %s", e)
            data = default
        
        html = self._build_infographic_html(data, timestamp, company)
        return html, data
    
    # ----------------------------------------------------------
    # 内部ヘルパー
    # ----------------------------------------------------------
    
    def _generate_text(self, prompt: str) -> str:
        """Gemini でテキストを生成する"""
        response = self._client.models.generate_content(
            model="gemini-2.5-flash",  # 補足生成は Flash で十分
            contents=prompt,
        )
        return response.text.strip()
    
    def _extract_json(self, text: str) -> Any:
        """テキストから JSON を抽出する"""
        cleaned = text.strip().replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # { } または [ ] で囲まれた部分を抽出
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
        
        raise ValueError(f"No valid JSON found in: {text[:100]}...")
    
    def _build_infographic_html(
        self,
        data: dict[str, Any],
        timestamp: str,
        company: str,
    ) -> str:
        """インフォグラフィック HTML を構築する（完全版）"""
        import html
        import re as re_mod
        
        title = html.escape(str(data.get("title", "Summary")))
        summary = html.escape(str(data.get("summary", "")))
        kpi = data.get("kpi", {})
        kpi_label = html.escape(str(kpi.get("label", "")))
        kpi_value = html.escape(str(kpi.get("value", "-")))
        kpi_delta = html.escape(str(kpi.get("delta", "")))
        insights = data.get("insights", [])
        actions = data.get("actions", [])
        
        # ファイル名用
        safe_company = re_mod.sub(r"[^\w\-]", "_", company) if company else "Report"
        png_filename = f"{timestamp}_Infographic_{safe_company}.png" if timestamp else "infographic.png"

        # アクセントカラー
        accent = "#D2FF00"

        insight_rows = ""
        for item in insights[:5]:
            icon = html.escape(str(item.get("icon", "●")))
            label = html.escape(str(item.get("label", "")))
            text = html.escape(str(item.get("text", "")))
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
            text = html.escape(str(item.get("text", "")))
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
  grid-template-columns:1.2fr 1fr 1fr;
  grid-template-rows:auto auto;
  gap:12px;
  padding:18px;
  min-height:100%;
  background:#0e1117;
}}
.header{{
  grid-column:1/-1;
  display:flex;align-items:baseline;gap:16px;
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
.kpi-value{{font-size:30px;font-weight:800;color:{accent};line-height:1;}}
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


# -----------------------------------------------------------------------------
# ファクトリ関数
# -----------------------------------------------------------------------------
def create_reasoning_engine_v2(
    client: Any,
    data_agent: Any,
    memory: Any,
    use_llm_router: bool = True,
    use_llm_agents: bool = True,
) -> ReasoningEngineV2:
    """
    ReasoningEngineV2 のインスタンスを生成する。
    
    Args:
        client: Gemini API クライアント
        data_agent: DataAgent インスタンス
        memory: SessionMemory インスタンス
        use_llm_router: LLM ベースの Router を使用するか
        use_llm_agents: LLM ベースのエージェントを使用するか
    
    Returns:
        ReasoningEngineV2 インスタンス
    """
    return ReasoningEngineV2(
        client=client,
        data_agent=data_agent,
        memory=memory,
        use_llm_router=use_llm_router,
        use_llm_agents=use_llm_agents,
    )
