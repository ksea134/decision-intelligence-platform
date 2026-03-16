from __future__ import annotations
import time
import logging
from typing import Any
from domain.models import ChatMessage
from config.app_config import APP

logger = logging.getLogger(__name__)


class SessionMemory:
    """
    Short-term memory for conversation history.

    Manages per-company chat messages and question history.
    No Streamlit dependency. Storage backend is injected via constructor,
    making it replaceable with Redis Memorystore in Phase 3.

    Current backend: plain Python dict (in-process memory).
    Future backend:  Redis Memorystore (drop-in replacement).
    """

    def __init__(self) -> None:
        self._current_company: str | None = None
        self._messages: list[ChatMessage] = []
        self._company_messages: dict[str, list[ChatMessage]] = {}
        self._question_history: dict[str, list[dict[str, str]]] = {}

    # ----------------------------------------------------------
    # Company switching
    # ----------------------------------------------------------

    def current_company(self) -> str | None:
        return self._current_company

    def switch_company(self, new_company: str | None) -> bool:
        """
        Switch active company. Saves current messages before switching.
        Returns True if company actually changed.
        """
        if self._current_company == new_company:
            return False
        if self._current_company is not None:
            self._company_messages[self._current_company] = list(self._messages)
        self._messages = list(self._company_messages.get(new_company, [])) if new_company else []
        self._current_company = new_company
        return True

    # ----------------------------------------------------------
    # Message management
    # ----------------------------------------------------------

    def get_messages(self) -> list[ChatMessage]:
        return self._messages

    def add_message(self, message: ChatMessage) -> None:
        # role または content が None/空のメッセージは追加しない
        if not message.get("role") or message.get("content") is None:
            return
        self._messages.append(message)

    def reset_chat(self) -> None:
        self._messages = []
        if self._current_company:
            self._company_messages[self._current_company] = []

    def sync(self) -> None:
        if self._current_company:
            self._company_messages[self._current_company] = list(self._messages)

    def get_artifacts(self, index: int) -> dict[str, Any]:
        if 0 <= index < len(self._messages):
            msg = self._messages[index]
            if "artifacts" not in msg:
                msg["artifacts"] = {}
            return msg["artifacts"]
        return {}

    # ----------------------------------------------------------
    # Question history
    # ----------------------------------------------------------

    def add_question_history(self, company: str, text: str) -> None:
        if not company or not text:
            return
        entries = self._question_history.get(company, [])
        if entries and entries[0]["text"] == text:
            return
        entries.insert(0, {
            "id": str(int(time.time() * 1000)),
            "text": text,
            "ts": time.strftime("%m/%d %H:%M"),
        })
        self._question_history[company] = entries[:APP.question_history_max]

    def delete_question_history(self, company: str, entry_id: str) -> None:
        entries = self._question_history.get(company, [])
        self._question_history[company] = [e for e in entries if e["id"] != entry_id]

    def get_question_history(self, company: str) -> list[dict[str, str]]:
        return self._question_history.get(company, [])

    # ----------------------------------------------------------
    # History builder for Gemini API
    # ----------------------------------------------------------

    def build_gemini_history(self, current_prompt: str):
        """
        Convert stored messages to Gemini API types.Content format.
        
        google-genai 1.47.0 では types.Content / types.Part を使用する必要がある。
        dict 形式はライブラリ内部で .role アクセスを試みてエラーになる。
        
        Raises:
            ValueError: If current_prompt is empty or None.
        """
        from google.genai import types
        
        # 【修正1】空プロンプトの早期検出 - Gemini APIエラー防止
        if not current_prompt or not str(current_prompt).strip():
            raise ValueError(
                "current_prompt cannot be empty. "
                "This usually indicates a smart card with missing prompt_template "
                "or an empty user input."
            )
        
        history = []
        for msg in self._messages:
            # 壊れたメッセージはスキップ
            if not msg.get("role") or msg.get("content") is None:
                continue
            role = "user" if msg.get("role") == "user" else "model"
            text = msg.get("llm_prompt") or msg.get("content", "") if msg.get("role") == "user" else msg.get("content", "")
            # 空テキストはスキップ（これが元のエラーの原因）
            if not text or not str(text).strip():
                continue
            
            # types.Content と types.Part を正しく構築
            content = types.Content(
                role=role,
                parts=[types.Part(text=str(text))]
            )
            history.append(content)
        
        # 必ずuserロールで終わるようにする
        current_content = types.Content(
            role="user",
            parts=[types.Part(text=str(current_prompt))]
        )
        history.append(current_content)
        
        # 【デバッグ用】履歴の内容をログ出力
        logger.debug("build_gemini_history: %d messages, current_prompt=%s", len(history), current_prompt[:50])
        
        return history
