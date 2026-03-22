"""
tests/test_step_to_mermaid.py — Mermaidフローチャート自動変換のテスト
"""
from domain.step_to_mermaid import (
    detect_steps,
    should_generate_flowchart,
    steps_to_mermaid,
    maybe_generate_mermaid_segment,
    detect_all_step_groups,
)


def test_detect_numbered_list():
    """番号付きリストの検出"""
    text = "1. 準備\n2. 実行\n3. 確認\n4. 報告"
    steps = detect_steps(text)
    assert len(steps) == 4


def test_detect_alphabet_list():
    """アルファベットリストの検出"""
    text = "A: 準備\nB: 実行\nC: 確認"
    steps = detect_steps(text)
    assert len(steps) == 3


def test_detect_bullet_alphabet():
    """箇条書き+アルファベットの検出（Gemini出力形式）"""
    text = "*   **A: 準備**: 詳細\n*   **B: 実行**: 詳細\n*   **C: 確認**: 詳細"
    steps = detect_steps(text)
    assert len(steps) == 3


def test_should_generate_with_keyword():
    """手順系キーワードがある場合のみ生成"""
    answer = "1. 準備\n2. 実行\n3. 確認"
    assert should_generate_flowchart("手順を教えて", answer) is True
    assert should_generate_flowchart("売上教えて", answer) is False


def test_should_not_generate_under_3():
    """3項目未満では生成しない"""
    answer = "1. 準備\n2. 実行"
    assert should_generate_flowchart("手順を教えて", answer) is False


def test_steps_to_mermaid():
    """Mermaidコード生成"""
    steps = ["準備", "実行", "確認"]
    code = steps_to_mermaid(steps)
    assert "graph TD" in code
    assert "-->" in code
    assert '"準備"' in code


def test_detect_longest_group():
    """複数リストがある場合、最長を選択"""
    text = "手順:\n1. A\n2. B\n3. C\n4. D\n5. E\n\n推奨:\nA: X\nB: Y\nC: Z"
    steps = detect_steps(text)
    assert len(steps) == 5  # 最長の数字リスト


def test_detect_all_groups():
    """全リストグループの検出"""
    text = "1. A\n2. B\n3. C\n\nX: P\nY: Q\nZ: R"
    groups = detect_all_step_groups(text)
    assert len(groups) == 2


def test_maybe_generate_none():
    """生成不要の場合はNone"""
    result = maybe_generate_mermaid_segment("売上教えて", "売上は100万円です。")
    assert result is None


def test_maybe_generate_valid():
    """有効な入力でセグメントが生成される"""
    answer = "手順:\n1. 準備\n2. 実行\n3. 確認\n4. 報告"
    result = maybe_generate_mermaid_segment("手順を教えて", answer)
    assert result is not None
    assert result["chart_type"] == "mermaid"
    assert "graph TD" in result["code"]
