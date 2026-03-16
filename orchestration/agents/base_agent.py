"""
orchestration/agents/base_agent.py — エージェント基底クラス

【役割】
全エージェントに共通する LLM 呼び出しロジックを提供する。
各専門エージェントはこのクラスを継承し、専用のシステムプロンプトを定義する。

【設計原則】
- DI パターン: Client を外部から注入
- テンプレートメソッドパターン: サブクラスで system_prompt を定義
- 構造化出力: JSON モードで応答を強制（オプション）
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from orchestration.graph.state import AgentResult, WorkflowState

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
# 定数
# -----------------------------------------------------------------------------
# メインモデル（複雑な推論用）
MAIN_MODEL = "gemini-2.5-flash"

# 軽量モデル（単純なタスク用）
LIGHT_MODEL = "gemini-2.5-flash"


# -----------------------------------------------------------------------------
# 応答の構造化データ
# -----------------------------------------------------------------------------
@dataclass
class AgentResponse:
    """エージェントの応答を格納するデータクラス"""
    text: str
    files: list[str]
    structured_data: dict[str, Any] | None = None
    sql_query: str | None = None
    sql_result: dict[str, Any] | None = None


# -----------------------------------------------------------------------------
# BaseAgent クラス
# -----------------------------------------------------------------------------
class BaseAgent(ABC):
    """
    エージェントの基底クラス。
    
    サブクラスは以下を実装する必要がある:
    - build_system_prompt(): 専用のシステムプロンプトを構築
    - agent_name: エージェント名（ログ用）
    
    オプションで以下をオーバーライド可能:
    - post_process(): 応答の後処理
    - use_json_mode: JSON モードを使用するか
    """
    
    def __init__(
        self,
        client: Any,  # genai.Client
        model: str = MAIN_MODEL,
        temperature: float = 0.0,
    ) -> None:
        """
        BaseAgent を初期化する。
        
        Args:
            client: Gemini API クライアント
            model: 使用するモデル名
            temperature: 生成温度
        """
        self._client = client
        self._model = model
        self._temperature = temperature
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """エージェント名（ログ用）"""
        pass
    
    @abstractmethod
    def build_system_prompt(self, state: WorkflowState) -> str:
        """
        システムプロンプトを構築する。
        
        Args:
            state: ワークフロー状態
        
        Returns:
            システムプロンプト文字列
        """
        pass
    
    @property
    def use_json_mode(self) -> bool:
        """JSON モードを使用するか（デフォルト: False）"""
        return False
    
    @property
    def max_output_tokens(self) -> int:
        """最大出力トークン数（デフォルト: 4096）"""
        return 4096
    
    def run(self, state: WorkflowState) -> dict[str, Any]:
        """
        エージェントを実行する。
        
        Args:
            state: ワークフロー状態
        
        Returns:
            更新する状態フィールドの辞書
        """
        user_prompt = state.get("user_prompt", "")
        
        logger.info("[%s] Processing: %s", self.agent_name, user_prompt[:50])
        
        try:
            response = self._call_llm(state)
            agent_result = self._build_result(response)
            
            logger.info(
                "[%s] Completed: %d chars, %d files",
                self.agent_name,
                len(response.text),
                len(response.files),
            )
            
            return {"agent_result": agent_result}
            
        except Exception as e:
            logger.error("[%s] Error: %s", self.agent_name, e)
            return {
                "agent_result": AgentResult(
                    response_text=f"エラーが発生しました: {str(e)}",
                    files=[],
                ),
                "error": str(e),
            }
    
    def _call_llm(self, state: WorkflowState) -> AgentResponse:
        """
        LLM を呼び出して応答を取得する。
        
        Args:
            state: ワークフロー状態
        
        Returns:
            AgentResponse
        """
        system_prompt = self.build_system_prompt(state)
        user_prompt = state.get("user_prompt", "")
        
        # config を構築
        config_dict = {
            "system_instruction": system_prompt,
            "temperature": self._temperature,
            "max_output_tokens": self.max_output_tokens,
        }
        
        if self.use_json_mode:
            config_dict["response_mime_type"] = "application/json"
        
        if types is not None:
            config = types.GenerateContentConfig(**config_dict)
        else:
            config = config_dict
        
        response = self._client.models.generate_content(
            model=self._model,
            contents=[user_prompt],
            config=config,
        )
        
        response_text = response.text.strip()
        
        # 応答をパース
        return self._parse_response(response_text)
    
    def _parse_response(self, text: str) -> AgentResponse:
        """
        LLM 応答をパースする。
        
        Args:
            text: 応答テキスト
        
        Returns:
            AgentResponse
        """
        # [FILES: ...] タグを抽出
        files = self._extract_files(text)
        
        # 構造化データを抽出（JSON モードの場合）
        structured_data = None
        if self.use_json_mode:
            structured_data = self._parse_json(text)
        
        return AgentResponse(
            text=text,
            files=files,
            structured_data=structured_data,
        )
    
    def _extract_files(self, text: str) -> list[str]:
        """
        [FILES: ...] タグからファイル名を抽出する。
        
        Args:
            text: 応答テキスト
        
        Returns:
            ファイル名のリスト
        """
        pattern = r"\[FILES?:\s*([^\]]+)\]"
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        files = []
        for match in matches:
            # カンマ区切りで分割
            for f in match.split(","):
                f = f.strip()
                if f:
                    files.append(f)
        
        return files
    
    def _parse_json(self, text: str) -> dict[str, Any] | None:
        """
        テキストから JSON をパースする。
        
        Args:
            text: 応答テキスト
        
        Returns:
            パースされた辞書、または None
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Markdown コードブロックから抽出
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # { } で囲まれた部分を抽出
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _build_result(self, response: AgentResponse) -> AgentResult:
        """
        AgentResponse から AgentResult を構築する。
        
        Args:
            response: AgentResponse
        
        Returns:
            AgentResult
        """
        return AgentResult(
            response_text=response.text,
            files=response.files,
            structured_data=response.structured_data,
            sql_query=response.sql_query,
            sql_result=response.sql_result,
        )


# -----------------------------------------------------------------------------
# ヘルパー関数
# -----------------------------------------------------------------------------
def build_data_context_section(state: WorkflowState) -> str:
    """
    データコンテキストセクションを構築する。
    
    Args:
        state: ワークフロー状態
    
    Returns:
        データコンテキストのテキスト
    """
    sections = []
    
    # BigQuery スキーマ
    bq_schema = state.get("bq_schema", "")
    if bq_schema:
        sections.append(f"## BigQuery スキーマ\n{bq_schema}")
    
    # GCS ドキュメント
    gcs_docs = state.get("gcs_docs", "")
    if gcs_docs:
        sections.append(f"## クラウドドキュメント\n{gcs_docs}")
    
    # 企業別前提知識
    knowledge = state.get("knowledge", "")
    if knowledge:
        sections.append(f"## 企業別前提知識\n{knowledge}")
    
    # 構造化データ
    structured = state.get("structured_data", "")
    if structured:
        sections.append(f"## 構造化データ\n{structured}")
    
    # 非構造化データ
    unstructured = state.get("unstructured_data", "")
    if unstructured:
        sections.append(f"## 非構造化データ\n{unstructured}")
    
    return "\n\n".join(sections)
