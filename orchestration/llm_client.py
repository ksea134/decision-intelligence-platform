"""
orchestration/llm_client.py — LLMクライアント抽象化層

Gemini / Claude を統一インターフェースで呼び出す。
モデルIDのプレフィックスで自動的にクライアントを切り替える。

- gemini-* → Google GenAI クライアント
- claude-* → Anthropic クライアント

呼び出し元はLLMの種類を意識しない。
"""
from __future__ import annotations

import logging
from typing import Generator

logger = logging.getLogger(__name__)

# --- Gemini クライアント（遅延初期化） ---
_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client()
    return _gemini_client


# --- Anthropic クライアント（遅延初期化） ---
_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic()
        except Exception as e:
            logger.error("[LLMClient] Anthropic client init failed: %s", e)
            raise
    return _anthropic_client


def _is_claude(model: str) -> bool:
    return model.startswith("claude-")


# ============================================================
# 統一インターフェース
# ============================================================

def generate_text(
    model: str,
    contents: str | list,
    system_instruction: str = "",
    temperature: float = 0.0,
) -> str:
    """テキストを生成する（非ストリーミング）。"""
    if _is_claude(model):
        return _claude_generate_text(model, contents, system_instruction, temperature)
    else:
        return _gemini_generate_text(model, contents, system_instruction, temperature)


def generate_stream(
    model: str,
    contents: str | list,
    system_instruction: str = "",
    temperature: float = 0.0,
) -> Generator[str, None, None]:
    """テキストをストリーミング生成する。"""
    if _is_claude(model):
        yield from _claude_generate_stream(model, contents, system_instruction, temperature)
    else:
        yield from _gemini_generate_stream(model, contents, system_instruction, temperature)


# ============================================================
# Gemini 実装
# ============================================================

def _gemini_generate_text(
    model: str, contents: str | list, system_instruction: str, temperature: float,
) -> str:
    from google.genai import types
    client = _get_gemini_client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction or None,
        temperature=temperature,
    )
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    return (response.text or "").strip()


def _gemini_generate_stream(
    model: str, contents: str | list, system_instruction: str, temperature: float,
) -> Generator[str, None, None]:
    from google.genai import types
    client = _get_gemini_client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction or None,
        temperature=temperature,
    )
    response_stream = client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    )
    for chunk in response_stream:
        if chunk.text:
            yield chunk.text


# ============================================================
# Claude 実装
# ============================================================

def _claude_generate_text(
    model: str, contents: str | list, system_instruction: str, temperature: float,
) -> str:
    client = _get_anthropic_client()
    # contentsをClaude形式に変換
    messages = _to_claude_messages(contents)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_instruction or "",
        messages=messages,
        temperature=temperature,
    )
    return response.content[0].text.strip()


def _claude_generate_stream(
    model: str, contents: str | list, system_instruction: str, temperature: float,
) -> Generator[str, None, None]:
    client = _get_anthropic_client()
    messages = _to_claude_messages(contents)
    with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=system_instruction or "",
        messages=messages,
        temperature=temperature,
    ) as stream:
        for text in stream.text_stream:
            yield text


def _to_claude_messages(contents) -> list[dict]:
    """Gemini形式のcontentsをClaude形式のmessagesに変換する。"""
    if isinstance(contents, str):
        return [{"role": "user", "content": contents}]

    messages = []
    for item in contents:
        if isinstance(item, str):
            messages.append({"role": "user", "content": item})
        elif isinstance(item, dict):
            role = item.get("role", "user")
            # Geminiの"model"ロールをClaudeの"assistant"に変換
            if role == "model":
                role = "assistant"
            content = item.get("parts", [item.get("content", "")])
            if isinstance(content, list):
                content = " ".join(str(p) for p in content)
            messages.append({"role": role, "content": str(content)})
        else:
            # Gemini Content オブジェクト
            role = getattr(item, "role", "user")
            if role == "model":
                role = "assistant"
            parts = getattr(item, "parts", [])
            text = " ".join(getattr(p, "text", str(p)) for p in parts)
            messages.append({"role": role, "content": text})

    # Claudeはmessagesが空だとエラー
    if not messages:
        messages = [{"role": "user", "content": ""}]

    # Claudeは最初のメッセージがuserである必要がある
    if messages[0]["role"] != "user":
        messages.insert(0, {"role": "user", "content": "質問に回答してください。"})

    # Claudeは同じロールが連続するとエラー — 連続する場合はマージ
    merged = []
    for msg in messages:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(msg)

    return merged
